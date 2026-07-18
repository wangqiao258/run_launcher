# Run Launcher

一个基于 Python + PyQt5 的 Windows 快速启动器：Alt+Space 全局呼出，拖拽添加、分类管理、搜索过滤、鼠标缩放窗口、跨分类拖动、自定义图标。可通过 Nuitka 编译为单文件 EXE（约 18 MB）。

## 功能

- **全局热键 Alt+Space** 显示/隐藏（RegisterHotKey + QAbstractNativeEventFilter，零漏发、无双重触发）
- **拖拽添加**：把桌面文件/文件夹/快捷方式拖到窗口即添加
- **搜索过滤**：顶部搜索框实时跨所有分类过滤
- **分类管理**：右键标签栏 添加/重命名/删除分类
- **右键编辑**：修改名称、路径、**自定义图标**
- **鼠标拖窗**
  - 拖标题区域移动窗口
  - **拖动边缘/四角调节大小**（最小 320×320）
- **跨分类拖动**：把图标从一个分类拖到另一个分类的标签上
- **图标提取**：通过 Windows Shell 的 `SHGetFileInfoW` 提取系统原生 32×32 图标（与资源管理器"大图标"视图一致），缓存 + 后台线程懒加载，切分类零阻塞
- **自定义图标**：`.vbs`/`.bat` 等图标偏小时，右键编辑 → 图标 → 浏览指定 `.ico/.png/.exe/.dll`
- **托盘集成**：右键托盘 显示/隐藏/设置/退出，双击托盘唤出
- **开机自启动**：写入注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **启动失败提示**：启动的目标已卸载/移动时弹提示，不再静默隐藏
- 支持 `.lnk` 快捷方式深度解析目标路径

## 项目结构

```
run_launch/
├── main.py             # 入口 + RegisterHotKey + nativeEventFilter
├── config.py           # 配置读写（%APPDATA%\RunLauncher\config.json）+ 开机自启注册表 + 异步原子保存
├── dialogs.py          # 设置/输入/编辑对话框（EditItemDialog 支持自定义图标）
├── window.py           # LauncherWindow + SHGetFileInfoW 图标提取 + 缓存/异步加载 + resize/drag-drop
├── requirements.txt
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖：`PyQt5`（含 `QtWinExtras`）、`pywin32`。

## 快速开始

```bash
python main.py
```

- 按 **Alt+Space** 显示/隐藏
- 拖桌面图标进窗口 → 自动添加
- 输入搜索关键字过滤
- 右键标签栏 → 添加分类
- 右键图标 → 编辑（可指定自定义图标）
- 拖窗口边缘 → 改变大小
- 拖图标到分类标签 → 移动到该分类

## 配置文件

运行时配置：`%APPDATA%\RunLauncher\config.json`

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
        { "name": "Burp", "path": "C:/tools/Burp.vbs", "icon_path": "C:/tools/burp.ico" }
      ]
    }
  ]
}
```

- `hotkey.vk`：热键键码（32=空格；32=空格；参考 [Virtual-Key Codes](https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes)）
- `icon_path`（可选）：为该条目指定图标文件，优先于自动提取

## 从源码编译

### Nuitka（推荐）

```powershell
$env:Path = "C:\mingw64\mingw64\bin;" + $env:Path
python -m nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --experimental=force-accept-windows-gcc main.py
```

编译完成后重命名 `main.exe` → `Launcher.exe`。

## 变更日志

### v2.0.5 (2026-07-18)

#### 重构
- **热键系统**：移除 `GetAsyncKeyState` 150ms 轮询，改用 `RegisterHotKey` + `QAbstractNativeEventFilter` 捕获 `WM_HOTKEY`。加 `MOD_NOREPEAT` 避免长按重复。按 5 次 50ms 间隔冒烟测试全部通过。退出时 `UnregisterHotKey` 清理
- **配置保存异步化**：`save_config` 取消直接写文件，改为模块级 `_save_pending` + 250ms debounce `threading.Timer`。到期后 daemon 线程 `_do_save()` 先写 `.tmp` 再 `os.replace` 原子落盘。`quit_app()` 前调 `flush_save_now()` 确保退出前持久化
- **图标管线简化**：移除 `SHIL_JUMBO`/`SHGetImageList`/`IImageList`/`ExtractIconExW`/像素裁剪等 ~300 行复杂逻辑。改为 `SHGetFileInfoW(SHGFI_ICON|SHGFI_LARGEICON)` 直接取系统缓存 32×32 图标，与资源管理器"大图标"一致
- **图标缓存 + 异步加载**：`_icon_cache` dict 按 `(path/icon_path, mtime)` 缓存 QIcon；`ThreadPoolExecutor(max_workers=4)` 后台提取，`_icon_ready` signal 回主线程回填。切分类时列表立刻显示（无图标），图标逐个弹出，再次切回零阻塞
- **显示尺寸调整**：`iconSize` 64→32，`gridSize` 96×104→72×72（匹配 SHGFI_LARGEICON 原生 32×32）

#### 性能
- 默认分类 18 项图标刷新：1250ms → **164ms**（7.6×），后续切换零阻塞
- 单张图标提取：70ms → **8-15ms**
- 排除自定义图标文件后编译产物不再捆绑 `config.json`

### v2.0.4 (2026-07-18)

#### 新增
- 鼠标拖动改窗口大小：拖边缘（12px）或四角（18px）调节大小，光标自动切换 8 方向；释放鼠标保存新宽高
- 自定义图标：右键编辑 → 图标 → 浏览，可指定任意 `.ico/.png/.jpg/.bmp/.exe/.dll` 作为图标源，优先于自动提取
- 跨分类拖动：把图标从一个分类拖到目标分类标签，即可移动条目（放宽命中：找最近 tab，拖过时目标 tab 高亮）
- 高 DPI 支持：`AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps`，在 125%/150% 缩放屏幕上图标不糊

#### Bug 修复
- 快捷方式图标丢失：目标软件卸载/重装后 `.lnk` 重建，Qt 图标缓存未刷新导致返回空但非 null 的图标。新增 `_icon_has_content()` 渲染 pixmap 验证；`.lnk` 通过 `WScript.Shell` 解析 `TargetPath` 后从真实目标提取
- 启动失败静默隐藏：`launch_item` 用裸 `except` 吞异常导致目标失效时窗口仍隐藏、用户无反馈。现在校验路径、弹 `QMessageBox` 提示、写日志，仅启动成功才隐藏窗口
- 拖动窗口子控件吞事件：改用应用级 `installEventFilter` + 递归 `setMouseTracking`，边缘 resize 命中稳定

### v2.0.2 (2026-06-29)

- 配置文件不持久：从 EXE 同目录改为 `%APPDATA%\RunLauncher\config.json`，并自动迁移旧配置
- 开机自启动无效：注册表写入缺少 `KEY_QUERY_VALUE` 权限；`sys.frozen` 检测不够健壮
- 右键编辑不显示对话框：`edit_item` 创建 `EditItemDialog` 后未调用 `exec_()`
- 新增启动日志：`%APPDATA%\RunLauncher\startup.log`

### v2.0.1 (2026-06-26)

- 全局搜索：搜索框跨所有分类搜索匹配项
- 跨分类编辑/删除：搜索结果显示的跨分类项目也能编辑/删除
- 切换标签不清空搜索：切换分类时保留搜索框内容和搜索结果
- Bug：`add_category` 和 `rename_category` 缺少 `exec_()` 调用

### v2.0 (2026-06-26)

- 单文件 → 模块化：`main.py` / `config.py` / `dialogs.py` / `window.py`
- 热键双重触发修复：移除 `RegisterHotKey`，只保留轮询（v2.0.5 已重新正确实现）
- 配置文件路径修复
- 文件夹启动报错修复：`subprocess.Popen(shell=True)` 把文件夹当命令；改用 `os.startfile()`
- 新增搜索过滤、编辑项目、记住窗口位置、开机自启动
