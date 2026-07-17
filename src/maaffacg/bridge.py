"""供 Playwright、Qt 等 UI 框架安全交接画面和输入的桥接层。"""

from __future__ import annotations

from collections import deque
from threading import Condition, RLock
from typing import Callable

from .backend import AppLaunchRequest, DeviceBackend, InputAction


class FrameInputBridge(DeviceBackend):
    """在 ADB 线程与宿主 UI 线程之间缓存画面并排队输入。

    ADB 服务线程不会调用浏览器或 UI 对象。宿主线程定期通过
    :meth:`publish_frame` 发布 PNG，并通过 :meth:`drain_inputs` 消费输入，
    以避免 Playwright、Qt 的线程归属问题。
    """

    def __init__(self, initial_frame: bytes | None = None, max_pending_inputs: int = 256) -> None:
        self._lock = RLock()
        self._frame_ready = Condition(self._lock)
        self._frame = initial_frame
        self._actions: deque[InputAction] = deque(maxlen=max_pending_inputs)
        self._launches: deque[AppLaunchRequest] = deque()

    def publish_frame(self, png: bytes) -> None:
        if not isinstance(png, bytes) or not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("published frame must be a PNG byte string")
        with self._frame_ready:
            self._frame = png
            self._frame_ready.notify_all()

    def screencap(self) -> bytes:
        with self._lock:
            if self._frame is None:
                raise RuntimeError("no cloud-game frame has been published yet")
            return self._frame

    def dispatch_input(self, action: InputAction) -> None:
        with self._lock:
            self._actions.append(action)

    def dispatch_app_launch(self, request: AppLaunchRequest) -> None:
        with self._lock:
            self._launches.append(request)

    def drain_inputs(self, handler: Callable[[InputAction], None]) -> int:
        """在所属宿主/UI 线程中对队列内输入执行 *handler*。"""
        with self._lock:
            actions = list(self._actions)
            self._actions.clear()
        for action in actions:
            handler(action)
        return len(actions)

    def drain_app_launches(self, handler: Callable[[AppLaunchRequest], None]) -> int:
        """在所属宿主/UI 线程中处理包启动请求。"""
        with self._lock:
            launches = list(self._launches)
            self._launches.clear()
        for launch in launches:
            handler(launch)
        return len(launches)
