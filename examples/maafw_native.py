"""最小 MaaFramework 原生连接示例，不包含 MaaCore/Asst 兼容层。"""

from pathlib import Path

from maaffacg import AdbDeviceSession, FrameInputBridge


bridge = FrameInputBridge()
# 云游戏宿主必须在自己的 UI 线程中定期调用以下方法：
# bridge.publish_frame(current_game_png)
# bridge.drain_inputs(send_to_game)

with AdbDeviceSession(
    bridge,
    adb_path=Path("path/to/adb.exe"),
    width=1920,
    height=1080,
) as device:
    controller = device.maa_connection.create_controller()
    controller.post_connection().wait()
    controller.post_screencap().wait()
    # 按项目原有方式将 `controller` 绑定到 MaaFramework Resource/Tasker。
