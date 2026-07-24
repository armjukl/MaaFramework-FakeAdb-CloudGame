"""网易云游戏（cg.163.com）的 Playwright 宿主适配器。"""

from __future__ import annotations

import logging
import time
from io import BytesIO
from typing import Any

from .backend import AppLaunchRequest, InputAction
from .bridge import FrameInputBridge

_LOG = logging.getLogger(__name__)

try:
    from PIL import Image, ImageEnhance

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


class NetEaseCloudGameBridge(FrameInputBridge):
    """将同步 Playwright 页面桥接到 MaaFFACG。

    必须在创建 Playwright 页面的同一线程调用 :meth:`sync`。该方法会截图游戏
    canvas/video，并将排队的 ADB 操作应用到相应元素。
    """

    selectors = ("#app canvas", "#app video", "canvas", "video")

    def __init__(
        self,
        page: Any,
        width: int = 1920,
        height: int = 1080,
        package_routes: dict[str, str] | None = None,
        cloud_url: str = "https://cg.163.com",
        enhancement_saturation: float = 1.0,
        enhancement_contrast: float = 1.0,
        enhancement_brightness: float = 1.0,
    ) -> None:
        super().__init__()
        self.page = page
        self.width = width
        self.height = height
        self.package_routes = package_routes or {}
        self.cloud_url = cloud_url.rstrip("/")
        self.enhancement_saturation = enhancement_saturation
        self.enhancement_contrast = enhancement_contrast
        self.enhancement_brightness = enhancement_brightness
        self.active_package: str | None = None
        self.active_game_code: str | None = None
        self._needs_recovery = False

    @property
    def needs_recovery(self) -> bool:
        """判断 Playwright 页面或浏览器连接是否已丢失。"""
        if self._needs_recovery:
            return True
        try:
            return bool(self.page.is_closed())
        except Exception:
            return True

    def set_page(self, page: Any) -> None:
        """绑定启动器在恢复后创建的替换页面。"""
        self.page = page
        self._needs_recovery = False

    def restore_active_game(self) -> None:
        """重新打开最近一次 Android StartApp 动作指定的游戏。"""
        if self.active_package is not None:
            self._launch_game(AppLaunchRequest(self.active_package, "browser recovery"))

    def sync(self) -> int:
        """发布最新串流帧，然后执行所有排队的 Maa 输入。"""
        launches = self.drain_app_launches(self._launch_game)
        try:
            target = self._target()
            # body 截图会排除滚动条，例如 1280x720 视口会变成 1264x704。
            # MaaEnd 要求 ADB 截图分辨率必须精确匹配。
            frame = target.screenshot(type="png") if target is not None else self.page.screenshot(type="png")
            frame = self._enhance_screenshot(
                frame,
                self.enhancement_saturation,
                self.enhancement_contrast,
                self.enhancement_brightness,
            )
            self.publish_frame(frame)
        except Exception as exc:
            # 页面跳转和云串流初始化会暂时使页面对象失效。保持 ADB 设备存活，
            # 并在下一轮重试。
            self._mark_recovery_if_closed(exc)
            if not self._needs_recovery:
                _LOG.warning("unable to capture a cloud-game frame; retrying: %s", exc)
            return launches

        try:
            return launches + self.drain_inputs(lambda action: self._apply(target, action))
        except Exception as exc:
            self._mark_recovery_if_closed(exc)
            if not self._needs_recovery:
                _LOG.warning("unable to apply queued cloud-game input; retrying: %s", exc)
            return launches

    @staticmethod
    def _enhance_screenshot(
        png: bytes,
        saturation: float = 1.0,
        contrast: float = 1.0,
        brightness: float = 1.0,
    ) -> bytes:
        """按配置增强截图颜色；三个参数均为 1.0 时保持原始 PNG。"""
        if not _HAS_PIL or (saturation == 1.0 and contrast == 1.0 and brightness == 1.0):
            return png
        try:
            image = Image.open(BytesIO(png))
            if saturation != 1.0:
                image = ImageEnhance.Color(image).enhance(saturation)
            if contrast != 1.0:
                image = ImageEnhance.Contrast(image).enhance(contrast)
            if brightness != 1.0:
                image = ImageEnhance.Brightness(image).enhance(brightness)
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        except Exception as exc:
            _LOG.warning("screenshot color enhancement failed: %s", exc)
            return png

    def _launch_game(self, request: AppLaunchRequest) -> None:
        game_code = self.package_routes.get(request.package_name)
        if game_code is None:
            _LOG.error(
                f"no NetEase game code configured for Android package {request.package_name!r}; "
                "start MaaFFACG with --route package=game_code"
            )
            return
        self.active_package = request.package_name
        self.active_game_code = game_code
        url = f"{self.cloud_url}/run.html?code={game_code}&id={int(time.time() * 1000)}&inline=1"
        _LOG.info("launching NetEase cloud game %s for package %s", game_code, request.package_name)
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            _LOG.info("cloud-game navigation finished: %s", self.page.url)
        except Exception as exc:
            # 云游戏导航可能在串流初始化期间超时，持久化页面仍可能在之后加载完成。
            self._mark_recovery_if_closed(exc)
            if not self._needs_recovery:
                _LOG.warning("cloud-game navigation is still loading for %s: %s", game_code, exc)

    def _mark_recovery_if_closed(self, error: Exception) -> None:
        message = str(error).lower()
        closed = (
            "target page, context or browser has been closed" in message
            or "connection closed" in message
            or "target closed" in message
        )
        if closed and not self._needs_recovery:
            self._needs_recovery = True
            _LOG.warning("cloud-game browser was closed; recreating it with the saved profile")

    def _target(self) -> Any | None:
        for selector in self.selectors:
            locator = self.page.locator(selector).first
            try:
                if locator.count() and locator.is_visible(timeout=100):
                    return locator
            except Exception:
                continue
        return None

    def _apply(self, target: Any | None, action: InputAction) -> None:
        box = target.bounding_box() if target is not None else {
            "x": 0,
            "y": 0,
            "width": self.width,
            "height": self.height,
        }
        if box is None:
            return
        scale_x = box["width"] / self.width
        scale_y = box["height"] / self.height

        def point(x: int | None, y: int | None) -> tuple[float, float]:
            return box["x"] + (x or 0) * scale_x, box["y"] + (y or 0) * scale_y

        if target is not None:
            # 云串流页面会在画布失焦时忽略鼠标事件；焦点请求失败不应阻断 ADB 输入。
            try:
                target.focus(timeout=500)
            except Exception:
                pass

        if action.kind == "tap":
            x, y = point(action.start_x, action.start_y)
            # Playwright 的 mouse.click 会连续发送 down/up。给云串流一个短按时间，
            # 避免其输入通道只收到一次无法识别的瞬时点击。
            self.page.mouse.move(x, y)
            self.page.mouse.down()
            time.sleep(0.04)
            self.page.mouse.up()
        elif action.kind == "swipe":
            x1, y1 = point(action.start_x, action.start_y)
            x2, y2 = point(action.end_x, action.end_y)
            self.page.mouse.move(x1, y1)
            self.page.mouse.down()
            self.page.mouse.move(x2, y2, steps=max(2, action.duration_ms // 16))
            time.sleep(action.duration_ms / 1000)
            self.page.mouse.up()
        elif action.kind == "keyevent" and action.value:
            self.page.keyboard.press(_adb_key_to_playwright(action.value))
        elif action.kind == "text" and action.value:
            self.page.keyboard.insert_text(action.value)


def _adb_key_to_playwright(key: str) -> str:
    mapping = {"3": "Home", "4": "Escape", "19": "ArrowUp", "20": "ArrowDown", "21": "ArrowLeft", "22": "ArrowRight", "23": "Enter", "66": "Enter"}
    return mapping.get(key, key)
