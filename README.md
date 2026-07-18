# Run Launcher

一个 Windows 桌面快速启动器：**Alt+Space** 全局呼出，拖拽添加、分类管理、模糊搜索、自定义图标、鼠标拖窗改大小。基于 PyQt5，Nuitka 编译为单文件 EXE（约 20 MB，无需 Python 环境）。

## 下载

到 [Releases](https://github.com/wangqiao258/run_launcher/releases/latest) 下载 `Launcher.exe` 双击运行即可。

## 主要功能

| 类别 | 说明 |
|------|------|
| **全局热键** | 默认 `Alt+Space` 显示/隐藏，退出前自动记忆窗口位置与大小 |
| **拖拽添加** | 桌面文件/文件夹/`.lnk` 快捷方式直接拖进窗口 |
| **分类管理** | 右键标签栏 → 添加/重命名/删除；拖图标到目标分类 tab 直接跨类移动 |
| **模糊搜索** | 顶部搜索框跨所有分类实时过滤 |
| **右键编辑** | 修改名称、路径、**自定义图标**（`.ico/.png/.exe/.dll`） |
| **鼠标拖窗** | 拖标题移动；拖边缘（12px）/ 四角（18px）调整大小 |
| **托盘集成** | 右键托盘：显示/隐藏 · 设置 · 关于 · 退出；双击托盘呼出 |
| **开机自启动** | 设置对话框一键开关，写入注册表 `HKCU\...\Run` |
| **检查更新** | 关于对话框内一键查询 GitHub Releases 最新版 |

## 快速上手

- **添加应用**：把桌面图标拖进窗口即可
- **搜索**：输入几个字即时过滤
- **编辑**：右键图标 → 编辑，可指定自定义图标覆盖系统默认
- **调整大小**：把鼠标移到窗口边缘变成箭头后拖动
- **移动到别的分类**：按住图标拖到目标 tab 上

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

依赖：`PyQt5`（含 `QtWinExtras`）、`pywin32`。

## 从源码编译

推荐 Nuitka onefile（约 20 MB，启动快）：

```powershell
$env:Path = "C:\mingw64\mingw64\bin;" + $env:Path
python -m nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --experimental=force-accept-windows-gcc main.py
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
        { "name": "记事本", "path": "C:/Windows/notepad.exe" },
        { "name": "Burp",   "path": "C:/tools/Burp.vbs", "icon_path": "C:/tools/burp.ico" }
      ]
    }
  ]
}
```

`hotkey.vk` 参考 [Virtual-Key Codes](https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes)（32 = 空格）。

## 更新日志

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
