# Run Launcher

一个 Windows 桌面快速启动器：**Alt+Space** 全局呼出，拖拽添加、分类管理、模糊搜索、自定义图标、鼠标拖窗改大小。基于 PyQt5，Nuitka 编译为单文件 EXE（约 18 MB，无需 Python 环境）。

## 下载

到 [Releases](https://github.com/wangqiao258/run_launcher/releases/latest) 下载 `Launcher.exe` 双击运行即可。

## 主要功能

| 类别 | 说明 |
|------|------|
| **全局热键** | 默认 `Alt+Space` 显示/隐藏，退出前自动记忆窗口位置与大小 |
| **拖拽添加** | 桌面文件/文件夹/`.lnk` 快捷方式直接拖进窗口 |
| **分类管理** | 右键标签栏 → 添加/重命名/删除；拖图标到目标分类 tab 直接跨类移动 |
| **多选操作** | `Ctrl` 点选 / 画框多选，批量删除（Delete 键或右键「删除选中项」）、批量拖拽到其他分类 |
| **模糊搜索** | 顶部搜索框跨所有分类实时过滤，支持中文名、拼音首字母（如 `wx` 搜「微信」）、路径、`.lnk` 目标路径 |
| **右键编辑** | 修改名称、路径、**自定义图标**（`.ico/.png/.exe/.dll`） |
| **鼠标拖窗** | 拖标题移动；拖边缘（15px）/ 四角（6px）调整大小 |
| **托盘集成** | 右键托盘：显示/隐藏 · 设置 · 关于 · 退出；双击托盘呼出 |
| **开机自启动** | 设置对话框一键开关，写入注册表 `HKCU\...\Run` |
| **检查更新** | 关于对话框内一键查询 GitHub Releases 最新版 |

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

依赖：`PyQt5`（含 `QtWinExtras`）、`pywin32`。

## 从源码编译

推荐 Nuitka onefile（约 18 MB，启动快）：

```powershell
python -m nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --include-windows-runtime-dlls=no --noinclude-qt-plugins=mediaservice --noinclude-qt-plugins=printsupport --noinclude-qt-plugins=platformthemes --noinclude-qt-plugins=imageformats --noinclude-qt-plugins=styles --noinclude-qt-plugins=iconengines "--noinclude-dlls=*qt5quick.dll" "--noinclude-dlls=*qt5qml.dll" "--noinclude-dlls=*qt5qmlmodels.dll" "--noinclude-dlls=*libcrypto-1_1.dll" "--noinclude-dlls=*libssl-1_1.dll" "--noinclude-dlls=*libeay32.dll" "--noinclude-dlls=*ssleay32.dll" "--noinclude-dlls=*qt5network.dll" "--noinclude-dlls=*qt5multimedia.dll" "--noinclude-dlls=*qt5dbus.dll" "--noinclude-dlls=*qt5websockets.dll" "--noinclude-dlls=*qt5printsupport.dll" "--noinclude-dlls=*qt5svg.dll" "--noinclude-dlls=*qminimal.dll" "--noinclude-dlls=*qoffscreen.dll" "--noinclude-dlls=*qwebgl.dll" "--noinclude-dlls=*qwebp.dll" "--noinclude-dlls=*qtiff.dll" "--noinclude-dlls=*qsvg.dll" "--noinclude-dlls=*qicns.dll" "--noinclude-dlls=*qtga.dll" "--noinclude-dlls=*qwbmp.dll" "--noinclude-dlls=*qsvgicon.dll" --remove-output main.py
```

产物 `main.exe` 重命名 `Launcher.exe`。

## 配置文件

`%APPDATA%\RunLauncher\config.json`（首次运行自动创建）

```json
{
  "hotkey": { "ctrl": false, "alt": true, "shift": false, "vk": 32 },
  "window_width": 420,
  "window_height": 480,
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

`hotkey.vk` 参考 [Virtual-Key Codes](https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes)（32 = 空格）。

## 更新日志

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
