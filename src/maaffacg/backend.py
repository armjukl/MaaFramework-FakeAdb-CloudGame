"""虚拟设备面向宿主程序的接口约定。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol


@dataclass(frozen=True)
class InputAction:
    """由兼容 ADB 的自动化控制器发出的输入请求。"""

    kind: Literal["tap", "swipe", "keyevent", "text"]
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    duration_ms: int = 0
    value: str | None = None


@dataclass(frozen=True)
class AppLaunchRequest:
    """通过 ``adb shell am`` 或 ``monkey`` 请求启动的 Android 包。"""

    package_name: str
    command: str


class DeviceBackend(Protocol):
    """宿主程序必须为虚拟设备提供的两项能力。"""

    def screencap(self) -> bytes:
        """返回当前的非空 PNG 图像。"""

    def dispatch_input(self, action: InputAction) -> None:
        """接收一项输入操作，且不得阻塞 ADB 连接。"""


class AppLaunchBackend(Protocol):
    """可响应 Android 应用启动请求的可选宿主接口。"""

    def dispatch_app_launch(self, request: AppLaunchRequest) -> None:
        """接收包启动请求，不直接访问宿主 UI 对象。"""


class CallbackBackend:
    """将普通截图和输入回调适配为 :class:`DeviceBackend`。"""

    def __init__(
        self,
        screenshot_provider: Callable[[], bytes],
        input_handler: Callable[[InputAction], None],
    ) -> None:
        self._screenshot_provider = screenshot_provider
        self._input_handler = input_handler

    def screencap(self) -> bytes:
        image = self._screenshot_provider()
        if not isinstance(image, bytes) or not image:
            raise ValueError("screenshot_provider must return non-empty PNG bytes")
        return image

    def dispatch_input(self, action: InputAction) -> None:
        self._input_handler(action)
