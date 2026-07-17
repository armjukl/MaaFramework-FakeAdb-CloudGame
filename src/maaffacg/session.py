"""虚拟设备生命周期与 MaaFramework 连接配置。"""

from __future__ import annotations

import subprocess
import threading
import logging
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Any

from .backend import DeviceBackend
from .server import FakeAdbServer

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaaAdbConnection:
    """提供给任意 MaaFramework 项目 ADB 控制器的连接参数。"""

    adb_path: str
    address: str
    config: dict[str, Any] | None = None
    # MaaFFACG 仅实现可移植的 Shell ADB 方案。MaaFramework 原生默认值还会
    # 探测 Android 文件同步与 maatouch/minitouch，浏览器虚拟设备并不具备这些能力。
    screencap_methods: int = 2  # MaaAdbScreencapMethodEnum.Encode
    input_methods: int = 1  # MaaAdbInputMethodEnum.AdbShell

    def controller_kwargs(self) -> dict[str, Any]:
        """返回 ``maa.controller.AdbController`` 接受的关键字参数。"""
        values: dict[str, Any] = {
            "adb_path": self.adb_path,
            "address": self.address,
            "screencap_methods": self.screencap_methods,
            "input_methods": self.input_methods,
        }
        if self.config is not None:
            values["config"] = self.config
        return values

    def create_controller(self) -> Any:
        """创建 MaaFramework 原生 ADB 控制器，不导入旧 MaaCore API。"""
        try:
            from maa.controller import AdbController
        except ImportError as exc:
            raise RuntimeError("MaaFramework Python bindings are required: pip install maafw") from exc
        return AdbController(**self.controller_kwargs())


class AdbDeviceSession:
    """启动虚拟设备，并通过标准 adb 服务注册它。"""

    def __init__(
        self,
        backend: DeviceBackend,
        adb_path: str | Path = "adb",
        host: str = "127.0.0.1",
        port: int = 5555,
        width: int = 1920,
        height: int = 1080,
        startup_timeout: float = 5.0,
        reconnect_interval: float = 0.25,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("MaaFFACG only listens on loopback; use a local host bridge for remote use")
        self.adb_path = _resolve_executable(adb_path)
        self.startup_timeout = startup_timeout
        if reconnect_interval <= 0:
            raise ValueError("reconnect_interval must be positive")
        self.reconnect_interval = reconnect_interval
        self.server = FakeAdbServer(backend, host, port, width, height)
        self._thread: threading.Thread | None = None
        self._watcher: threading.Thread | None = None
        self._watch_stop = threading.Event()
        self._connected = False

    @property
    def address(self) -> str:
        return f"127.0.0.1:{self.server.port}"

    @property
    def maa_connection(self) -> MaaAdbConnection:
        return MaaAdbConnection(self.adb_path, self.address)

    def start(self, register_with_adb: bool = True) -> MaaAdbConnection:
        self._thread = self.server.start_in_thread()
        try:
            self.server.wait_until_ready(self.startup_timeout)
            if register_with_adb:
                self._run_adb("start-server")
                self._run_adb("connect", self.address)
                self._connected = True
                self._start_connection_watcher()
            return self.maa_connection
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self._stop_connection_watcher()
        if self._connected:
            self._run_adb("disconnect", self.address, check=False)
            self._connected = False
        self.server.close()
        if self._thread is not None:
            self._thread.join(self.startup_timeout)
            self._thread = None

    def __enter__(self) -> "AdbDeviceSession":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _run_adb(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([self.adb_path, *args], capture_output=True, text=True, check=False)
        if check and result.returncode:
            details = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise RuntimeError(f"adb {' '.join(args)} failed: {details}")
        return result

    def _start_connection_watcher(self) -> None:
        self._watch_stop.clear()
        self._watcher = threading.Thread(
            target=self._maintain_connection,
            name="maaffacg-adb-keepalive",
            daemon=True,
        )
        self._watcher.start()

    def _stop_connection_watcher(self) -> None:
        self._watch_stop.set()
        if self._watcher is not None:
            self._watcher.join(self.reconnect_interval + 1)
            self._watcher = None

    def _maintain_connection(self) -> None:
        """其他程序断开设备后，恢复 ADB 注册状态。"""
        while not self._watch_stop.wait(self.reconnect_interval):
            if self._device_is_registered():
                continue
            result = self._run_adb("connect", self.address, check=False)
            if result.returncode:
                _LOG.warning("failed to restore ADB device registration: %s", result.stderr.strip())

    def _device_is_registered(self) -> bool:
        result = self._run_adb("devices", check=False)
        if result.returncode:
            return False
        expected = f"{self.address}\tdevice"
        return any(line.startswith(expected) for line in result.stdout.splitlines())


def _resolve_executable(executable: str | Path) -> str:
    """可能时为 MaaFramework 提供可执行文件的绝对路径。"""
    candidate = Path(executable).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    resolved = which(str(executable))
    if resolved:
        return str(Path(resolved).resolve())
    return str(executable)
