# MaaFramework-FakeAdb-CloudGame（MaaFFACG）

MaaFFACG 将网易云游戏浏览器画面伪装成一台本地 Android ADB 设备，供 **MaaFramework** 项目使用。

它不依赖 MaaCore、`Asst` 或旧版任务格式。对 MaaFW 项目而言，MaaFFACG 就是 `127.0.0.1:5555` 上的一台 Android 设备：项目通过 ADB 截图、点击、滑动和启动应用，MaaFFACG 则把这些操作转发到网易云游戏网页。

## 适用范围

可用于使用 MaaFramework Android ADB 控制器的项目，包括 MaaEnd。项目应使用常规 ADB 截图和 `input` 输入方式。

不适用于 Win32、iOS 或依赖真实 Android 文件系统、MaaTouch/minitouch、专有设备协议的项目。MaaFFACG 不包含游戏任务、模板、账号或 Maa 资源，这些仍由使用它的 MaaFW 项目负责。

```text
MaaFW 项目 -> adb.exe -> 本地 ADB 服务 -> MaaFFACG -> 浏览器 -> 网易云游戏
```

## 首次安装

在 PowerShell 中执行：

```powershell
cd MaaFramework-FakeAdb-CloudGame
pip install -e .[netease]
playwright install chromium
```

项目自带 `platform-tools\adb.exe` 及所需 DLL，无需另行安装 Android platform-tools。

## 基本使用

1. 复制 `maaffacg.env.example` 为 `maaffacg.env`。
2. 填写游戏包名和网易云游戏 `code`。
3. 运行 `启动MaaFFACG.bat`，在首次打开的浏览器中正常登录网易云游戏。
4. 保持 MaaFFACG 运行，再通过对应脚本启动 MaaFW 项目。
5. 在项目内选择 ADB 控制器并连接 `127.0.0.1:5555`。

最小配置示例：

```ini
# MaaFW 项目通过 adb shell am start 启动的 Android 包名
MAAFFACG_PACKAGE=com.example.game

# 网易云游戏 run.html 使用的 code，由用户自行填写
MAAFFACG_GAME_CODE=your_cloud_game_code

# MaaEnd 画面模板要求的固定分辨率示例
MAAFFACG_WIDTH=1280
MAAFFACG_HEIGHT=720
```

MaaFFACG 收到 `am start -n <包名>/<活动>` 或 `monkey -p <包名>` 后，会查找对应 `code` 并打开网易云游戏。浏览器配置目录 `.maaffacg-profile` 会保存登录状态，之后通常无需重复登录。

关闭浏览器会停止 MaaFFACG 并断开虚拟 ADB；程序不会自动重新打开浏览器。需要继续使用时，请手动运行 `启动MaaFFACG.bat`。

## MaaEnd

使用 `示例启动MaaEnd.bat` 启动 MaaEnd，不要直接双击 MaaEnd。脚本会把 MaaFFACG 自带的 `platform-tools` 放到 MaaEnd 进程的 `PATH` 首位，使其设备扫描器能发现虚拟设备。

默认 MaaEnd 路径可在 `maaffacg.env` 中配置：

```ini
MAAFFACG_MAAEND_EXE=C:\Users\Administrator\Downloads\MaaEnd-win-x86_64-v2.19.0\MaaEnd.exe
```

在 MaaEnd 中连接时使用：

```text
设备地址：127.0.0.1:5555
ADB 路径：MaaFFACG\platform-tools\adb.exe
```

## 其他 MaaFW 项目

使用 `启动MaaFFACG项目.bat` 启动其他 MaaFramework 程序，有两种方式：

```text
将目标项目的 .exe 拖到 启动MaaFFACG项目.bat 上。
```

或在 `maaffacg.env` 中填写：

```ini
MAAFFACG_TARGET_EXE=D:\MaaProjects\SomeProject\SomeProject.exe
```

然后双击 `启动MaaFFACG项目.bat`。如果目标项目不扫描 `PATH` 中的 ADB，需要在其设置内手动填写上述设备地址和 ADB 路径。

## 同时使用多个项目

为每个 Android 包名添加一个网易云游戏 `code`：

```ini
MAAFFACG_ROUTES=com.example.game1=code1,com.example.game2=code2
```

`MAAFFACG_PACKAGE` 与 `MAAFFACG_GAME_CODE` 适合默认的一组映射；`MAAFFACG_ROUTES` 用于追加更多映射。包名必须与项目实际发送的启动命令一致。

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `MAAFFACG_ADB` | MaaFFACG 使用的 ADB 路径；启动脚本未配置时回退到自带 ADB | `./platform-tools/adb.exe` |
| `MAAFFACG_PORT` | 虚拟设备端口 | `5555` |
| `MAAFFACG_WIDTH` / `MAAFFACG_HEIGHT` | 提供给 ADB 的画面尺寸 | `1920x1080` |
| `MAAFFACG_PROFILE` | Chromium 持久化登录目录 | `.maaffacg-profile` |
| `MAAFFACG_CLOUD_URL` | 网易云游戏网站地址 | `https://cg.163.com` |
| `MAAFFACG_RECONNECT_INTERVAL` | 检查 ADB 注册状态的间隔（秒） | `0.25` |

## 颜色识别与模板

浏览器截图是网易云视频解码后的像素。若 MaaEnd 提示颜色识别失败，先检查 `MaaEnd\debug\screencap` 中同一时间生成的截图，确认实际画面、分辨率和颜色。

本机 HDR、动态亮丽等桌面显示后处理不会进入浏览器截图链路。若截图画面正常但模板因极窄色值范围失败，应谨慎放宽对应资源中的 `ColorMatch` 范围，并先备份原资源。MaaEnd 的通用识别规则在 `resource\pipeline\nodes.json`，ADB 专用图片模板在 `resource_adb`。

## 常见问题

**找不到设备**：先确认 MaaFFACG 正在运行，再执行：

```powershell
.\platform-tools\adb.exe devices -l
```

应出现 `127.0.0.1:5555 device`。如果 MaaEnd 未扫描到设备，请通过 `启动MaaEnd.bat` 重启 MaaEnd。

**任务提示分辨率不符**：将 `MAAFFACG_WIDTH` 和 `MAAFFACG_HEIGHT` 改为项目要求的固定尺寸，例如 MaaEnd 常用 `1280x720`，然后重启 MaaFFACG。

**启动游戏失败**：检查 `MAAFFACG_PACKAGE` 是否等于项目实际启动的包名，以及该包名对应的网易云 `code` 是否正确。运行日志位于 `logs\maaffacg.log`。

## 验证

```powershell
cd MaaFramework-FakeAdb-CloudGame
$env:PYTHONPATH = (Resolve-Path .\src)
python -m unittest discover -s tests -v
```

协议级检查：

```powershell
adb -s 127.0.0.1:5555 exec-out screencap -p
adb -s 127.0.0.1:5555 shell input tap 960 540
```
