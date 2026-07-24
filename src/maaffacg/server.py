"""满足 MaaFramework ADB 控制器所需的最小 adbd 传输服务。"""

from __future__ import annotations

import logging
import socket
import struct
import threading
from typing import Final

from .backend import AppLaunchRequest, DeviceBackend, InputAction

_LOG = logging.getLogger(__name__)

A_CNXN: Final = 0x4E584E43
A_OPEN: Final = 0x4E45504F
A_OKAY: Final = 0x59414B4F
A_WRTE: Final = 0x45545257
A_CLSE: Final = 0x45534C43
A_VERSION: Final = 0x01000001
A_MAXDATA: Final = 1024 * 1024
HEADER_SIZE: Final = 24
CHUNK_SIZE: Final = 512 * 1024

_DEVICE_PROPERTIES: Final = {
    "ro.build.version.release": "11",
    "ro.build.version.sdk": "30",
    "ro.product.brand": "MaaFFACG",
    "ro.product.name": "maaffacg",
    "ro.product.device": "maaffacg",
    "ro.product.cpu.abi": "x86_64",
    "ro.product.model": "MaaFFACG",
    "ro.product.manufacturer": "MaaFFACG",
}


def _packet(command: int, arg0: int, arg1: int, payload: bytes = b"") -> bytes:
    return struct.pack(
        "<6I", command, arg0, arg1, len(payload), sum(payload) & 0xFFFFFFFF, command ^ 0xFFFFFFFF
    ) + payload


class FakeAdbServer:
    """将 :class:`DeviceBackend` 暴露为精简的本地 adbd 服务。"""

    def __init__(
        self,
        backend: DeviceBackend,
        host: str = "127.0.0.1",
        port: int = 5555,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        self.backend = backend
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self._socket: socket.socket | None = None
        self._ready = threading.Event()
        self._stopping = threading.Event()
        self._startup_error: OSError | None = None

    def start_in_thread(self) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, name="maaffacg-adbd", daemon=True)
        thread.start()
        return thread

    def wait_until_ready(self, timeout: float = 5.0) -> None:
        if not self._ready.wait(timeout):
            raise TimeoutError(f"virtual device did not bind within {timeout:g}s")
        if self._startup_error:
            raise RuntimeError("unable to start virtual device") from self._startup_error

    def serve_forever(self) -> None:
        self._ready.clear()
        self._stopping.clear()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                self._socket = server
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.host, self.port))
                self.port = server.getsockname()[1]
                server.listen(8)
                server.settimeout(0.25)
                self._ready.set()
                while not self._stopping.is_set():
                    try:
                        connection, address = server.accept()
                    except TimeoutError:
                        continue
                    except OSError:
                        break
                    threading.Thread(target=self._serve_connection, args=(connection, address), daemon=True).start()
        except OSError as exc:
            self._startup_error = exc
            self._ready.set()
        finally:
            self._socket = None

    def close(self) -> None:
        self._stopping.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass

    def execute_command(self, command: str) -> bytes:
        """执行 shell/exec 命令，保留公开接口以便诊断测试。"""
        tokens = command.strip().split()
        if not tokens:
            return b"\n"
        executable = tokens[0]
        if executable.endswith("screencap"):
            return self.backend.screencap()
        if executable == "input":
            self._dispatch_input(tokens)
            # Android 的 `input` 命令成功时不输出内容。MaaFramework 的 AdbShell
            # 输入单元会将意外的标准输出视为命令错误。
            return b""
        launch = self._parse_launch(command, tokens)
        if launch is not None:
            dispatch = getattr(self.backend, "dispatch_app_launch", None)
            if dispatch is not None:
                dispatch(launch)
            return b"Starting: Intent { cmp=" + launch.package_name.encode() + b"/.MainActivity }\n"
        if executable == "wm" and len(tokens) > 1 and tokens[1] in {"size", "density"}:
            return f"Physical size: {self.width}x{self.height}\n".encode() if tokens[1] == "size" else b"Physical density: 320\n"
        if executable == "getprop":
            if len(tokens) >= 4 and tokens[1:3] == ["|", "grep"]:
                pattern = " ".join(tokens[3:])
                return "".join(
                    f"[{key}]: [{value}]\n"
                    for key, value in _DEVICE_PROPERTIES.items()
                    if pattern in key or pattern in value
                ).encode()
            key = tokens[1] if len(tokens) > 1 else ""
            value = _DEVICE_PROPERTIES.get(key)
            # An absent Android property produces no content. Returning a
            # newline here makes MaaFramework's emulator probes see it as set.
            return b"" if value is None else f"{value}\n".encode()
        if executable == "settings":
            return b"0123456789abcdef\n" if "android_id" in tokens else b"\n"
        if executable == "pm" and len(tokens) > 1 and tokens[1] == "path":
            package = tokens[2] if len(tokens) > 2 else "cloud.game"
            return f"package:/data/app/{package}/base.apk\n".encode()
        if executable == "echo":
            return (" ".join(tokens[1:]) + "\n").encode()
        return b"\n"

    @staticmethod
    def _parse_launch(command: str, tokens: list[str]) -> AppLaunchRequest | None:
        """识别 MaaFramework StartApp 动作发出的包名格式。"""
        if len(tokens) < 2:
            return None
        package = ""
        if tokens[0] == "am" and tokens[1] in {"start", "start-activity", "startservice"}:
            for flag in ("-n", "--component"):
                if flag in tokens:
                    index = tokens.index(flag) + 1
                    if index < len(tokens):
                        package = tokens[index].split("/", 1)[0]
                        break
            if not package:
                candidates = [token for token in tokens[2:] if "." in token and not token.startswith("-")]
                if candidates:
                    package = candidates[-1].split("/", 1)[0]
        elif tokens[0] == "monkey" and "-p" in tokens:
            index = tokens.index("-p") + 1
            if index < len(tokens):
                package = tokens[index]
        if package and all(part and part.replace("_", "").replace("-", "").isalnum() for part in package.split(".")):
            return AppLaunchRequest(package, command)
        return None

    def _serve_connection(self, connection: socket.socket, address: object) -> None:
        buffer = b""
        streams: dict[tuple[int, int], str] = {}
        try:
            with connection:
                while not self._stopping.is_set():
                    received = connection.recv(65536)
                    if not received:
                        return
                    buffer += received
                    while len(buffer) >= HEADER_SIZE:
                        command, arg0, arg1, length, _checksum, _magic = struct.unpack("<6I", buffer[:HEADER_SIZE])
                        if len(buffer) < HEADER_SIZE + length:
                            break
                        payload = buffer[HEADER_SIZE : HEADER_SIZE + length]
                        buffer = buffer[HEADER_SIZE + length :]
                        self._handle_packet(connection, command, arg0, arg1, payload, streams)
        except (ConnectionError, OSError) as exc:
            _LOG.debug("ADB connection %s closed: %s", address, exc)

    def _handle_packet(
        self,
        connection: socket.socket,
        command: int,
        arg0: int,
        arg1: int,
        payload: bytes,
        streams: dict[tuple[int, int], str],
    ) -> None:
        if command == A_CNXN:
            banner = b"device::ro.product.name=maaffacg;ro.adb.secure=0;ro.product.model=MaaFFACG;"
            connection.sendall(_packet(A_CNXN, A_VERSION, A_MAXDATA, banner))
            return
        if command == A_WRTE:
            self._handle_stream_write(connection, arg0, arg1, payload, streams)
            return
        if command == A_CLSE:
            streams.pop((arg0, arg1), None)
            streams.pop((arg1, arg0), None)
            return
        if command != A_OPEN:
            return
        remote_id = arg0
        local_id = remote_id + 1
        destination = payload.decode("utf-8", errors="replace").rstrip("\0")
        if destination == "sync:":
            # MaaFramework 会用 `adb push` 探测 maatouch/minitouch。此处不模拟
            # Android 文件系统，但实现足够的 Sync 协议，让 adb 正常失败并回退到
            # AdbShell，而不是崩溃。
            streams[(local_id, remote_id)] = "sync"
            connection.sendall(_packet(A_OKAY, local_id, remote_id))
            return
        if not destination.startswith(("shell:", "exec:", "exec-out:")):
            connection.sendall(_packet(A_OKAY, local_id, remote_id))
            connection.sendall(_packet(A_CLSE, local_id, remote_id))
            return
        command_text = destination.split(":", 1)[1]
        if command_text.strip() == "cat":
            # MaaFramework 保持 `adb shell cat` 连接作为状态监视器。立即关闭会让
            # MaaControllerConnected 永远为 false，并导致客户端循环重建控制器。
            streams[(local_id, remote_id)] = "monitor"
            connection.sendall(_packet(A_OKAY, local_id, remote_id))
            return
        result = self.execute_command(command_text)
        connection.sendall(_packet(A_OKAY, local_id, remote_id))
        for offset in range(0, len(result), CHUNK_SIZE):
            connection.sendall(_packet(A_WRTE, local_id, remote_id, result[offset : offset + CHUNK_SIZE]))
        connection.sendall(_packet(A_CLSE, local_id, remote_id))

    @staticmethod
    def _handle_stream_write(
        connection: socket.socket,
        remote_id: int,
        local_id: int,
        payload: bytes,
        streams: dict[tuple[int, int], str],
    ) -> None:
        if streams.get((local_id, remote_id)) != "sync":
            return
        connection.sendall(_packet(A_OKAY, local_id, remote_id))
        offset = 0
        while offset + 8 <= len(payload):
            sync_command = payload[offset : offset + 4]
            size = struct.unpack("<I", payload[offset + 4 : offset + 8])[0]
            offset += 8
            if sync_command == b"QUIT":
                connection.sendall(_packet(A_CLSE, local_id, remote_id))
                streams.pop((local_id, remote_id), None)
                return
            if sync_command == b"DONE":
                message = b"MaaFFACG has no Android filesystem"
                sync_failure = b"FAIL" + struct.pack("<I", len(message)) + message
                connection.sendall(_packet(A_WRTE, local_id, remote_id, sync_failure))
                connection.sendall(_packet(A_CLSE, local_id, remote_id))
                streams.pop((local_id, remote_id), None)
                return
            if sync_command == b"STAT":
                # adb 在 push 前检查目标是否存在。模式值为零是 Sync 协议中“未找到”
                # 的正常表示。
                connection.sendall(_packet(A_WRTE, local_id, remote_id, b"STAT" + struct.pack("<3I", 0, 0, 0)))
            if sync_command == b"RECV":
                message = b"MaaFFACG has no Android filesystem"
                sync_failure = b"FAIL" + struct.pack("<I", len(message)) + message
                connection.sendall(_packet(A_WRTE, local_id, remote_id, sync_failure))
                connection.sendall(_packet(A_CLSE, local_id, remote_id))
                streams.pop((local_id, remote_id), None)
                return
            if sync_command not in {b"SEND", b"DATA", b"RECV", b"STAT"} or offset + size > len(payload):
                return
            offset += size

    def _dispatch_input(self, tokens: list[str]) -> None:
        try:
            command = tokens[1]
            if command == "tap" and len(tokens) >= 4:
                self.backend.dispatch_input(InputAction("tap", int(tokens[2]), int(tokens[3])))
            elif command == "swipe" and len(tokens) >= 6:
                duration = int(tokens[6]) if len(tokens) >= 7 else 200
                self.backend.dispatch_input(InputAction("swipe", int(tokens[2]), int(tokens[3]), int(tokens[4]), int(tokens[5]), duration))
            elif command == "keyevent" and len(tokens) >= 3:
                self.backend.dispatch_input(InputAction("keyevent", value=tokens[2]))
            elif command == "text" and len(tokens) >= 3:
                self.backend.dispatch_input(InputAction("text", value=" ".join(tokens[2:]).replace("%s", " ")))
        except (TypeError, ValueError):
            _LOG.warning("ignoring malformed ADB input: %s", " ".join(tokens))
