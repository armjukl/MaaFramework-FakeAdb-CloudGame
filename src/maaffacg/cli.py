"""网易云游戏 Playwright 适配器的本地启动器。"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from .config import load_env
from .netease import NetEaseCloudGameBridge
from .session import AdbDeviceSession

_LOG = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expose NetEase Cloud Game as a local MaaFramework ADB device")
    parser.add_argument("--env", default="maaffacg.env", help="local KEY=VALUE config file")
    parser.add_argument("--adb", help="path to adb executable")
    parser.add_argument("--port", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--profile", help="persistent Chromium profile directory")
    parser.add_argument("--package", help="Android package used by the downloaded MaaFW release")
    parser.add_argument("--game-code", help="NetEase Cloud Game code for --package")
    parser.add_argument("--route", action="append", default=[], metavar="PACKAGE=GAME_CODE", help="additional package-to-cloud-game mapping; may be repeated")
    parser.add_argument("--cloud-url", help="NetEase Cloud Game base URL")
    args = parser.parse_args()
    try:
        environment = load_env(args.env)
        adb_path = args.adb or environment.get("MAAFFACG_ADB", "adb")
        port = args.port if args.port is not None else _integer(environment, "MAAFFACG_PORT", 5555)
        reconnect_interval = _number(environment, "MAAFFACG_RECONNECT_INTERVAL", 0.25)
        width = args.width if args.width is not None else _integer(environment, "MAAFFACG_WIDTH", 1920)
        height = args.height if args.height is not None else _integer(environment, "MAAFFACG_HEIGHT", 1080)
        enhancement_saturation = _number(environment, "MAAFFACG_ENHANCE_SATURATION", 1.0)
        enhancement_contrast = _number(environment, "MAAFFACG_ENHANCE_CONTRAST", 1.0)
        enhancement_brightness = _number(environment, "MAAFFACG_ENHANCE_BRIGHTNESS", 1.0)
    except ValueError as exc:
        parser.error(str(exc))
    profile = args.profile or environment.get("MAAFFACG_PROFILE", ".maaffacg-profile")
    cloud_url = args.cloud_url or environment.get("MAAFFACG_CLOUD_URL", "https://cg.163.com")
    package = args.package or environment.get("MAAFFACG_PACKAGE")
    game_code = args.game_code or environment.get("MAAFFACG_GAME_CODE")
    if bool(package) != bool(game_code):
        parser.error("--package and --game-code must be supplied together")
    routes = _parse_routes(_split_routes(environment.get("MAAFFACG_ROUTES", "")) + args.route)
    if package and game_code:
        routes[package] = game_code
    if not routes:
        parser.error("configure at least one --package/--game-code or --route")
    _configure_logging()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("MaaFFACG dependencies are missing — run install_dependencies.bat first") from exc

    with sync_playwright() as playwright:
        context, page = _open_browser(playwright, profile, width, height)
        bridge = NetEaseCloudGameBridge(
            page,
            width,
            height,
            routes,
            cloud_url,
            enhancement_saturation=enhancement_saturation,
            enhancement_contrast=enhancement_contrast,
            enhancement_brightness=enhancement_brightness,
        )
        bridge.sync()  # MaaFW 可能会在收到 StartApp 动作前就发起连接。
        with AdbDeviceSession(
            bridge,
            adb_path,
            port=port,
            width=width,
            height=height,
            reconnect_interval=reconnect_interval,
        ) as device:
            print(f"MaaFramework ADB: {device.address}")
            print(f"adb path: {device.adb_path}")
            print("Start the MaaFramework release and let its StartApp action launch the configured package.")
            print("Keep this process open while the MaaFramework project runs. Press Ctrl+C to stop.")
            try:
                while True:
                    if bridge.needs_recovery:
                        _LOG.info("cloud-game browser was closed; stopping MaaFFACG")
                        break
                    try:
                        bridge.sync()
                    except Exception:
                        _LOG.exception("unexpected bridge loop error; continuing")
                    time.sleep(0.05)
            except KeyboardInterrupt:
                pass
        context.close()


def _open_browser(playwright: object, profile: str, width: int, height: int) -> tuple[object, object]:
    """按 ADB 所需分辨率创建可见且持久化的浏览器页面。"""
    _LOG.info("opening Chromium profile %s at %dx%d", Path(profile).resolve(), width, height)
    context = playwright.chromium.launch_persistent_context(
        str(Path(profile).resolve()), headless=False, viewport={"width": width, "height": height}
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.on("close", lambda: _LOG.warning("cloud-game browser tab was closed"))
    page.goto("about:blank")
    return context, page


def _parse_routes(values: list[str]) -> dict[str, str]:
    routes: dict[str, str] = {}
    for value in values:
        package, separator, game_code = value.partition("=")
        if not separator or not package or not game_code:
            raise SystemExit(f"invalid --route {value!r}; expected PACKAGE=GAME_CODE")
        routes[package] = game_code
    return routes


def _split_routes(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _integer(environment: dict[str, str], key: str, default: int) -> int:
    value = environment.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer, got {value!r}") from exc


def _number(environment: dict[str, str], key: str, default: float) -> float:
    value = environment.get(key)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a number, got {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{key} must be positive")
    return parsed


def _configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "maaffacg.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


if __name__ == "__main__":
    main()
