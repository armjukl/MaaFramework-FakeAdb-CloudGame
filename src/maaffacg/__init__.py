"""MaaFFACG：将非 Android 画面暴露为 MaaFramework 可用的 ADB 设备。"""

from .backend import AppLaunchRequest, CallbackBackend, DeviceBackend, InputAction
from .bridge import FrameInputBridge
from .server import FakeAdbServer
from .session import AdbDeviceSession, MaaAdbConnection

__all__ = [
    "AdbDeviceSession",
    "AppLaunchRequest",
    "CallbackBackend",
    "DeviceBackend",
    "FakeAdbServer",
    "FrameInputBridge",
    "InputAction",
    "MaaAdbConnection",
]
