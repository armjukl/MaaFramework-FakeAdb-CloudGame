import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from maaffacg import AppLaunchRequest, CallbackBackend, FakeAdbServer, FrameInputBridge, InputAction
from maaffacg.config import load_env
from maaffacg.cli import _integer, _number, _parse_routes, _split_routes
from maaffacg.netease import NetEaseCloudGameBridge


PNG = b"\x89PNG\r\n\x1a\nminimal"


class ServerTests(unittest.TestCase):
    def test_server_reports_device_and_queues_all_common_input(self) -> None:
        actions = []
        server = FakeAdbServer(CallbackBackend(lambda: PNG, actions.append), width=1280, height=720)

        self.assertEqual(server.execute_command("wm size"), b"Physical size: 1280x720\n")
        self.assertEqual(server.execute_command("screencap -p"), PNG)
        self.assertEqual(server.execute_command("input tap 4 5"), b"")
        server.execute_command("input swipe 1 2 3 4 500")
        server.execute_command("input keyevent 4")
        server.execute_command("input text hello%sworld")

        self.assertEqual([(action.kind, action.value) for action in actions], [
            ("tap", None),
            ("swipe", None),
            ("keyevent", "4"),
            ("text", "hello world"),
        ])

    def test_bridge_isolated_from_adb_thread(self) -> None:
        bridge = FrameInputBridge(PNG)
        bridge.dispatch_input(InputAction("tap", 1, 2))
        seen = []
        self.assertEqual(bridge.screencap(), PNG)
        self.assertEqual(bridge.drain_inputs(seen.append), 1)
        self.assertEqual(seen[0].start_x, 1)

    def test_start_app_is_queued_for_the_host_thread(self) -> None:
        bridge = FrameInputBridge(PNG)
        server = FakeAdbServer(bridge)
        server.execute_command("am start -n com.example.game/.MainActivity")
        received = []
        self.assertEqual(bridge.drain_app_launches(received.append), 1)
        self.assertEqual(received[0].package_name, "com.example.game")

    def test_env_loader_and_route_parser(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "maaffacg.env"
            path.write_text("MAAFFACG_PORT=6000\nMAAFFACG_ROUTES=a.b=c,d.e=f\n", encoding="utf-8")
            values = load_env(path)
        self.assertEqual(_integer(values, "MAAFFACG_PORT", 5555), 6000)
        self.assertEqual(_number({"MAAFFACG_RECONNECT_INTERVAL": "0.5"}, "MAAFFACG_RECONNECT_INTERVAL", 1), 0.5)
        self.assertEqual(_parse_routes(_split_routes(values["MAAFFACG_ROUTES"])), {"a.b": "c", "d.e": "f"})

    def test_failed_cloud_navigation_does_not_raise(self) -> None:
        class FailingPage:
            def goto(self, *args, **kwargs):
                raise RuntimeError("temporary navigation failure")

        bridge = NetEaseCloudGameBridge(FailingPage(), package_routes={"com.example.game": "mrfz"})
        bridge._launch_game(AppLaunchRequest("com.example.game", "am start -n com.example.game/.Main"))
        self.assertEqual(bridge.active_game_code, "mrfz")

    def test_closed_page_requests_browser_recovery(self) -> None:
        class ClosedPage:
            def is_closed(self) -> bool:
                return True

        bridge = NetEaseCloudGameBridge(ClosedPage())
        self.assertTrue(bridge.needs_recovery)
