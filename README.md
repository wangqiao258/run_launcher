# Run Launcher

一个 Windows 桌面快速启动器：**Alt+Space** 全局呼出，拖拽添加、分类管理、模糊搜索、自定义图标、鼠标拖窗改大小。基于 PyQt5，PyInstaller 打成单文件 EXE（精简版约 19 MB、完整版约 40 MB，无需 Python 环境）。

## 下载

到 [Releases](https://github.com/wangqiao258/run_launcher/releases/latest) 下载 `Launcher.exe` 双击运行即可。

## 主要功能

| 类别 | 说明 |
|------|------|
| **全局热键** | 默认 `Alt+Space` 显示/隐藏，退出前自动记忆窗口位置与大小 |
| **鼠标速度热键** | 默认 `Ctrl+Alt+M` 循环切换档位 5/10/15/20（慢/标准/快/极快），屏幕下方 OSD 浮层即时提示当前档位 |
| **图标缓存** | 提取结果按「路径 + 修改时间 + 大小」落盘（上限 500 条），启动时预热全部分类，重启后首屏直接出图标 |
| **拖拽添加** | 桌面文件/文件夹/`.lnk` 快捷方式直接拖进窗口 |
| **分类管理** | 右键标签栏 → 添加/重命名/删除；拖图标到目标分类 tab 直接跨类移动 |
| **多选操作** | `Ctrl` 点选 / 画框多选，批量删除（Delete 键或右键「删除选中项」）、批量拖拽到其他分类 |
| **模糊搜索** | 顶部搜索框跨所有分类实时过滤，支持中文名、拼音首字母（如 `wx` 搜「微信」）、路径、`.lnk` 目标路径 |
| **右键编辑** | 修改名称、路径、**自定义图标**（`.ico/.png/.exe/.dll`） |
| **鼠标拖窗** | 拖标题移动；拖边缘（15px）/ 四角（6px）调整大小 |
| **托盘集成** | 右键托盘：显示/隐藏 · 设置 · 关于 · 退出；双击托盘呼出 |
| **开机自启动** | 设置对话框一键开关，写入注册表 `HKCU\...\Run` |
| **管理员启动** | 右键图标 → 以管理员身份运行（触发 UAC 提权） |

## 快速上手

- **添加应用**：把桌面图标拖进窗口即可
- **搜索**：输入几个字即时过滤，中文名可输拼音首字母（如 `wx` 找「微信」）
- **编辑**：右键图标 → 编辑，可指定自定义图标覆盖系统默认
- **多选**：`Ctrl` 点选或按住左键画框选中多个，Delete 批量删除、拖到其他分类批量移动
- **调整大小**：把鼠标移到窗口边缘变成箭头后拖动
- **移动到别的分类**：按住图标拖到目标 tab 上

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

项目结构：`main.py`（入口）、`window.py`（主窗口）、`utils.py`（工具函数）、`config.py`（配置管理）、`dialogs.py`（对话框）、`Launcher.spec`（打包配置）。

依赖：`PyQt5`（含 `QtWinExtras`）、`pywin32`、`pypinyin`。

## 从源码编译

用 PyInstaller + `Launcher.spec`，同一个 spec 有两档：

```powershell
pip install -r requirements.txt pyinstaller

# 完整版 → dist\Launcher.exe（约 40 MB）
python -m PyInstaller --clean --noconfirm Launcher.spec
```

```powershell
# 精简版 → dist-slim\Launcher-slim.exe（约 19 MB）
$env:RUNLAUNCHER_SLIM=1
python -m PyInstaller --clean --noconfirm --workpath build-slim --distpath dist-slim Launcher.spec
```

精简版只保留 `qt5core/gui/widgets/winextras` 与 5 个必需插件（`qwindows`、`qoffscreen`、`qjpeg`、`qico`、`qwindowsvistastyle`），裁掉 translations 与 OpenSSL。因为排除了 `_hashlib`，spec 里显式补了 `_sha2`，让 `hashlib` 走 CPython 内置实现——图标缓存 key 依赖它算 SHA-256。

发布时把产物重命名为 `Launcher.exe`。

## 配置文件

`%APPDATA%\RunLauncher\config.json`（首次运行自动创建）

```json
{
  "hotkey": "Alt+Space",
  "mouse_speed_hotkey": "Ctrl+Alt+M",
  "mouse_speed_presets": [5, 10, 15, 20],
  "window_width": 420,
  "window_height": 480,
  "pos_x": 800,
  "pos_y": 300,
  "title": "Run Launcher",
  "categories": [
    {
      "name": "默认",
      "items": [
        { "name": "记事本", "path": "C:/Windows/notepad.exe" }
      ]
    }
  ]
}
```

- 快捷键用 QKeySequence 字符串（`"Alt+Space"`、`"Ctrl+Alt+M"`），旧版 `{"ctrl": false, "alt": true, "vk": 32}` 的 dict 形式会自动转换
- 条目可选 `icon_path` 字段覆盖系统图标
- 同目录下的 `icon-cache-v1.json` 是图标缓存（PNG base64，上限 500 条），删掉只影响首屏速度，会自动重建
- 同目录下的 `startup.log` 是运行日志，热键注册、图标提取失败都记在这里

## 更新日志

### v2.1.0 (2026-11-10)

**图标秒开：磁盘缓存 + 启动预热**

- 图标提取结果以 64×64 PNG（base64）落到 `%APPDATA%\RunLauncher\icon-cache-v1.json`，最多 500 条 LRU 淘汰；重启后首屏直接从缓存解码，不再逐个等 Shell 提取
- 缓存 key 为 `SHA-256(规范化路径 + mtime_ns + 文件大小)`，程序换了图标就会失效重取；自定义图标失效时退回程序自身图标（二级 key）
- 缓存文件带 `version` 字段，损坏或版本不符自动丢弃重建；写入走 `.tmp` + `os.replace` 原子替换，且只由图标线程执行（250ms 防抖 + 退出前最终落盘），GUI 线程不碰磁盘
- 启动时窗口还没显示就把所有分类的图标排队预热，第一次 `Alt+Space` 就是热的；`.lnk` 即使命中缓存也会后台复查——快捷方式自身 mtime 不变但目标程序可能换了图标

**图标管线重写**

- `IconLoader` 改为常驻线程 + Condition 双队列（前台/后台）：当前列表优先，后台只做缓存预热；同一 key 的重复请求合并，`prioritize()` 支持插队
- 图标回填从「按列表下标映射」改成「按缓存 key 路由到对应行」，切分类或搜索时后台结果不会再贴到错的行
- 加载失败也回填完成态，下次刷新可以重试（旧实现失败后会一直挂在 pending 里）
- 退出改为优雅停线程：`aboutToQuit` 里 wait 工作线程，HICON 回到 GUI 线程销毁，不再用 `terminate()`
- `shell_hicon` 修 HICON 句柄泄漏：一次提取出的大/小图标只保留一个，其余立即 `DestroyIcon`
- `resolve_lnk_target` 不再复用全局 `WScript.Shell`（COM 对象属于创建它的线程，跨线程用会报错），改为每次在当前线程 Dispatch

**打包方式迁移到 PyInstaller**

- 新增 `Launcher.spec`，同一个 spec 出两档：默认完整版，`RUNLAUNCHER_SLIM=1` 走精简版（约 19 MB）
- 精简版白名单裁剪 Qt DLL/插件并剔除 translations，同时排除 OpenSSL（`_ssl`/`_hashlib`）

### v2.0.13 (2026-09-07)

- **移除「检查更新」功能**：打包版缺 ssl 模块（OpenSSL DLL 被瘦身排除）导致功能不可用，直连 GitHub 在本机网络环境也不可达；关于对话框保留版本号与 GitHub 链接

### v2.0.12 (2026-09-07)

- **鼠标速度热键**：全局热键循环切换鼠标速度档位（默认 `Ctrl+Alt+M`），档位 5/10/15/20（慢/标准/快/极快），切换时屏幕下方弹出 OSD 浮层即时反馈（实测 ~6ms，不走系统通知管线）
- **设置面板**：新增「鼠标速度热键」自定义（与呼出热键同款录入控件），与呼出热键重复时拒绝保存
- **兼容实现**：`SPI_SETMOUSESPEED` 持久化设置（等同系统滑杆）；`SPI_GETMOUSESPEED` 失效时回退读注册表 `MouseSensitivity`
- 多热键架构：`HotkeyFilter` 改为按 ID 派发表，单进程支持多个全局热键

### v2.0.11 (2026-08-28)

- **自定义热键**：呼出热键可在设置面板修改，配置以字符串形式存储（旧 dict 形式自动兼容）
- **图标加载改 QThread**：`IconLoader` 单条常驻线程 + 队列，取代 `ThreadPoolExecutor`
- **pywin32 统一**：COM 初始化统一走 `pythoncom.CoInitialize()`
- 主窗口基类改 `QMainWindow`；拼音搜索依赖 `pypinyin`

### v2.0.10 (2026-08-27)

- **代码重构**：提取工具函数到 `utils.py`（LNK 解析、拼音首字母、Shell 图标），减少 `window.py` 耦合
- **窗口缩放修复**：背景组件填满整个窗口，修正坐标映射；边缘缩放区域从 12px 增大到 15px，四角 6px
- **窗口状态保存统一**：新增 `_save_window_state()` 方法，消除 4 处重复保存逻辑
- **图标缓存 LRU**：`_icon_cache` 限制最多 500 项，防止长时间运行内存泄漏
- **线程池退出清理**：`quit_app()` 中关闭 `ThreadPoolExecutor`，防止 Nuitka 打包场景线程泄漏
- **自定义关闭按钮**：QPainter 精确绘制 X，不依赖字体渲染，确保居中
- **管理员启动**：右键菜单新增「以管理员身份运行」，通过 `ShellExecuteW` + `runas` 触发 UAC
- **关闭按钮 hover 修复**：eventFilter 不再在子组件上频繁调用 `setCursor`，避免 hover 闪烁
- **设置对话框修复**：补上遗漏的深色主题样式表，复选框现在可见
- **Nuitka 瘦身**：排除 imageformats/styles/iconengines 插件

### v2.0.9 (2026-08-14)

- **多选操作**：`Ctrl` 点选 / 画框多选，Delete 键或右键「删除选中项 (N)」批量删除，批量拖拽到其他分类
- **搜索增强**：支持拼音首字母（`wx` 搜「微信」）、文件路径、`.lnk` 目标路径匹配，中文名无需输入完整汉字
- **修复 VBS 直接拖入报错**：`launch_item` 改用 `ShellExecuteW` 并显式传入工作目录，`CN_Burp(无CMD窗口).VBS` 这类依赖相对路径的脚本直接运行不再报"找不到文件"
- **打包瘦身**：排除 QML/OpenSSL/Network 等 20+ 个不需要的 Qt DLL（`--noinclude-dlls`）及插件（`--noinclude-qt-plugins`），最终约 18 MB

### v2.0.8 (2026-08-03)

- **右键「打开路径」**：图标上右键新增"打开路径"，`.lnk` 打开指向的 exe 所在文件夹、普通文件打开自身所在文件夹
- **hosts 等无扩展名文件图标兜底**：`_extract_icon_payload` 在 Shell 取不到图标时回退 `QFileIconProvider` 通用文件图标，不再空白
- **修复 Tab 拖拽排序与分类不同步**：拖 tab 重排后同步 `categories` 并持久化
- **清理旧图标管线死代码**：移除 v2.0.5 异步化后未使用的 `extract_icon` / `_load_custom_icon` / `_extract_icon_from_path` 及其辅助函数

### v2.0.7 (2026-07-19)

- **启动应用零延迟**：`launch_item` 先 `hide()` 隐藏窗口，再用后台线程调 `os.startfile()`。启动重量级软件（如浏览器/IDE）时主线程不再被 ShellExecute 短暂阻塞，视觉零延迟
- **打包瘦身**：编译产物去掉用不到的 Qt 插件（mediaservice / printsupport / platformthemes），约 -1 MB

### v2.0.6 (2026-07-18)

- **关于对话框**：托盘菜单「关于」→ 版本号、GitHub 链接、检查更新按钮
- **检查更新**：走 GitHub Releases API，后台线程查询，有新版可一键打开下载页
- **图标启动首屏为空修复**：Shell IconCache 冷启动时 `SHGetFileInfoW` 会漏返 0，加 3 次 20ms 间隔的重试彻底解决

### v2.0.5 (2026-07-18)

- **全局热键**：从 `GetAsyncKeyState` 150ms 轮询改为 `RegisterHotKey` + `WM_HOTKEY` 事件驱动，零漏发、无双触发
- **配置保存异步化**：debounce 250ms + daemon 线程 + `os.replace` 原子写，切分类不再抖动
- **图标管线简化**：砍掉 v2.0.4 的 `SHIL_JUMBO` / IImageList / 手动裁剪等 ~300 行复杂逻辑，改用 `SHGetFileInfoW` 直接取系统 32×32 图标（与资源管理器一致）
- **图标缓存 + 后台线程懒加载**：`ThreadPoolExecutor(max_workers=4)` 后台提取 HICON 句柄，signal 回主线程渲染；`_icon_cache` 按 `(path, mtime)` 缓存，切分类零阻塞
- **性能**：默认分类 18 项刷新从 1250ms → **164ms**（首次），后续切换命中缓存基本 0ms

### v2.0.4

- 鼠标拖边缘/四角调整窗口大小
- 自定义图标（EditItemDialog 增加图标字段）
- 跨分类拖动（拖图标到目标 tab）
- 高 DPI 支持

### v2.0.2

- 配置持久化改到 `%APPDATA%\RunLauncher\`
- 修复开机自启动、编辑对话框不显示等 bug
- 启动日志 `startup.log`

### v2.0.1 / v2.0

- 全局搜索、编辑项目、记住窗口位置、模块化重构、开机自启动

## License

MIT
