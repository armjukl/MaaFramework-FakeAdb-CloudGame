"""MaaFFACG 的 MaaFramework AdbController 端到端冒烟测试。"""

from __future__ import annotations

import argparse
import struct
import time
import zlib
from pathlib import Path

from maaffacg import AdbDeviceSession, CallbackBackend

def _png_1x1() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\0\0\0\0")) + chunk(b"IEND", b"")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb", type=Path, required=True)
    args = parser.parse_args()
    actions = []
    with AdbDeviceSession(CallbackBackend(_png_1x1, actions.append), args.adb, port=0, width=1, height=1) as device:
        controller = device.maa_connection.create_controller()
        connection = controller.post_connection()
        connection.wait()
        if not connection.status.succeeded:
            raise SystemExit(f"MaaFramework connection failed: {connection.status}")
        screencap = controller.post_screencap()
        screencap.wait()
        if not screencap.status.succeeded:
            raise SystemExit(f"MaaFramework screenshot failed: {screencap.status}")
        if controller.cached_image.size == 0:
            raise SystemExit("MaaFramework received an empty screenshot")
        controller.post_click(0, 0).wait()
        time.sleep(0.1)
        if not actions or actions[-1].kind != "tap":
            raise SystemExit("MaaFramework click did not reach the virtual device")
        print("PASS: MaaFramework AdbController connected, captured, and clicked through MaaFFACG")


if __name__ == "__main__":
    main()
