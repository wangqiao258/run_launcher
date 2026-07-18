# Run Launcher

一个基于 Python + PyQt5 的 Windows 快速启动器：Alt+Space 呼出，拖拽添加、分类管理、搜索过滤、鼠标缩放窗口、高清图标、自定义图标。可通过 Nuitka 编译为单文件 EXE。

## 功能

- **全局热键 Alt+Space** 显示/隐藏启动器，隐藏时记住窗口位置和大小
- **拖拽添加**：把桌面文件/文件夹/快捷方式拖到窗口即添加
- **搜索过滤**：顶部搜索框实时跨所有分类过滤
- **分类管理**：右键标签栏 添加/重命名/删除分类
- **右键编辑**：修改名称、路径、**自定义图标**（v2.0.4 新增）
- **鼠标拖窗**
  - 拖标题区域移动窗口
  - **拖动边缘/四角调节大小**（v2.0.4 新增），最小 320×320
- **跨分类拖动**：把图标从一个分类拖到另一个分类的标签上（v2.0.3 新增）
- **高清图标**：通过 Windows Shell 的 `SHIL_JUMBO` 拉最大 256×256 图标，缩放到 64px 显示（v2.0.4 增强）
- **自定义图标**：Windows 对 `.vbs` / `.bat` 生成的系统图标偏小时，右键编辑 → 图标 → 浏览指定任意 `.ico/.png/.exe/.dll`（v2.0.4 新增）
- **托盘集成**：右键托盘 显示/隐藏/设置/退出，双击托盘唤出
- **开机自启动**：设置对话框可勾选，写入注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **启动失败提示**：启动的目标已卸载/移动时弹提示，不再静默隐藏
- 支持 `.lnk` 快捷方式深度解析目标路径

## 项目结构

```
run_launch/
├── main.py             # 入口 + 热键轮询（GetAsyncKeyState）
├── config.py           # 配置读写（%APPDATA%\RunLauncher\config.json）+ 开机自启注册表
├── dialogs.py          # 设置/输入/编辑对话框（EditItemDialog 支持自定义图标）
├── window.py           # LauncherWindow + 高清图标提取（SHGetImageList/ExtractIconEx）
├── requirements.txt
├── config.json         # 默认配置模板
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

- `hotkey.vk`：热键键码（32=空格；参考 [Virtual-Key Codes](https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes)）
- `icon_path`（可选）：为该条目指定图标文件，优先于自动提取

## 从源码编译

### 方法一：Nuitka（推荐，性能更好）

```bash
pip install nuitka zstandard
nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --include-data-files=config.json=config.json main.py
```

编译完成后重命名 `main.exe` → `Launcher.exe`。

#### Nuitka 自动下载 MinGW 失败

1. 从 [winlibs-mingw](https://github.com/brechtsanders/winlibs_mingw/releases) 下载 `winlibs-x86_64-posix-seh-gcc-*-mingw-w64msvcrt-*.zip`
2. 解压确保 `gcc.exe` 在 `C:\mingw64\mingw64\bin\gcc.exe`
3. 清理 Nuitka 缓存中损坏的版本：
   ```powershell
   Remove-Item "$env:LOCALAPPDATA\Nuitka\Nuitka\Cache\downloads\gcc" -Recurse -Force
   ```
4. PATH 加入 `C:\mingw64\mingw64\bin`，再加 `--experimental=force-accept-windows-gcc` 编译：
   ```bash
   nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --include-data-files=config.json=config.json --experimental=force-accept-windows-gcc main.py
   ```

### 方法二：PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "Launcher" --add-data "config.json;." main.py
```

## 变更日志

### v2.0.4 (2026-07-18)

#### 新增
- **鼠标拖动改窗口大小**：拖边缘（12px）或四角（18px）调节大小，光标自动切换 8 方向；释放鼠标保存新宽高
- **自定义图标**：右键编辑 → 图标 → 浏览，可指定任意 `.ico/.png/.jpg/.bmp/.exe/.dll` 作为图标源，优先于自动提取
- **跨分类拖动**：把图标从一个分类拖到目标分类标签，即可移动条目（放宽命中：找最近 tab，拖过时目标 tab 高亮）
- **高 DPI 支持**：`AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps`，在 125%/150% 缩放屏幕上图标不糊
- **图标源升级**：优先走 `SHIL_JUMBO` (256×256)，回退 `SHIL_EXTRALARGE` (48) / `SHIL_LARGE` (32)；`.exe/.dll` 额外走 `ExtractIconExW` 挖 PE 资源；`.lnk` 递归解析 TargetPath 后重取
- **图标显示尺寸**：`iconSize` 44 → 64，`gridSize` 72×80 → 96×104，视觉更接近桌面
- **图标裁剪**：自动裁掉 shell 大画布上的透明留白（避免"256 画布左上角一个 32 图标"）

#### Bug 修复
- **快捷方式图标丢失**：目标软件卸载/重装后 `.lnk` 重建，Qt 图标缓存未刷新导致返回空但非 null 的图标。新增 `_icon_has_content()` 渲染 pixmap 验证；`.lnk` 通过 `WScript.Shell` 解析 `TargetPath` 后从真实目标提取
- **启动失败静默隐藏**：`launch_item` 用裸 `except` 吞异常导致目标失效时窗口仍隐藏、用户无反馈。现在校验路径、弹 `QMessageBox` 提示、写日志，仅启动成功才隐藏窗口
- **拖动窗口子控件吞事件**：改用应用级 `installEventFilter` + 递归 `setMouseTracking`，边缘 resize 命中稳定

### v2.0.2 (2026-06-29)

#### Bug 修复
- **配置文件不持久**：从 EXE 同目录改为 `%APPDATA%\RunLauncher\config.json`，并自动迁移旧配置
- **开机自启动无效**：注册表写入缺少 `KEY_QUERY_VALUE` 权限；`sys.frozen` 检测不够健壮。修复：`_is_frozen()` + `_detect_exe_path()` 准确获取 exe 路径；写入后 `FlushKey`+读回校验
- **右键编辑不显示对话框**：`edit_item` 创建 `EditItemDialog` 后未调用 `exec_()`

#### 新增
- **启动日志**：`%APPDATA%\RunLauncher\startup.log`

### v2.0.1 (2026-06-26)

- **全局搜索**：搜索框跨所有分类搜索匹配项
- **跨分类编辑/删除**：搜索结果显示的跨分类项目也能编辑/删除
- **切换标签不清空搜索**：切换分类时保留搜索框内容和搜索结果
- Bug：`add_category` 和 `rename_category` 缺少 `exec_()` 调用

### v2.0 (2026-06-26)

#### 重构
- 单文件 → 模块化：`main.py` / `config.py` / `dialogs.py` / `window.py`

#### Bug 修复
- **热键双重触发**：`RegisterHotKey` + `WinEventFilter` 与 `GetAsyncKeyState` 轮询两套并存，按一次触发两次窗口闪烁；移除 `RegisterHotKey`，只保留轮询
- **配置文件路径**：EXE 打包后相对路径找不到；改用 `sys.executable` 绝对路径
- **文件夹启动报错**：`subprocess.Popen(shell=True)` 把文件夹当命令；改用 `os.startfile()`

#### 新增
- 搜索过滤、编辑项目、记住窗口位置、开机自启动、窗口关闭按钮、`requirements.txt`
