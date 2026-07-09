# Run Launcher

一个基于 Python + PyQt5 的快速启动器，支持拖拽添加快捷方式、分类管理、搜索过滤、开机自启动，可通过 Nuitka 编译为单文件 EXE。

## 功能

- **Alt+Space** 在鼠标位置显示/隐藏启动器（记住窗口位置）
- 拖拽文件/文件夹到启动器添加快捷方式
- **搜索框**：实时过滤当前分类的快捷方式
- 右键标签栏管理分类（添加/重命名/删除）
- 右键快捷方式 → 编辑（修改名称/路径）/ 删除
- 右键托盘图标 → 设置（自定义标题、宽度、高度、**开机自启动**）
- 窗口右上角 **×** 关闭按钮（隐藏到托盘）
- 支持热键配置（`config.json` 中修改）

## 项目结构

```
run_launch/
├── main.py          # 入口 + 热键轮询
├── config.py        # 配置读写 + 开机自启（注册表）
├── dialogs.py       # 设置/输入/编辑 对话框
├── window.py        # LauncherWindow 主窗口
├── requirements.txt
├── config.json
└── README.md
```

## 使用

1. 运行 `Launcher.exe`（已编译）或 `python main.py`
2. 按 **Alt+Space** 显示/隐藏
3. 拖拽文件到网格添加快捷方式
4. 使用搜索框快速过滤
5. 右键标签栏管理分类

## 自定义配置

配置文件路径：`%APPDATA%\RunLauncher\config.json`

```json
{
  "hotkey": { "ctrl": false, "alt": true, "shift": false, "vk": 32 },
  "window_width": 420,
  "window_height": 480,
  "title": "Launcher",
  "categories": [...]
}
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 从源码编译

### 方法一：Nuitka（推荐，性能更好）

```bash
pip install -r requirements.txt nuitka zstandard
nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable main.py
```

如果你本地有 MinGW-w64 但 Nuitka 拒绝使用，可添加 `--experimental=force-accept-windows-gcc`：

```bash
# 先安装 MinGW-w64 并加入 PATH
nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --experimental=force-accept-windows-gcc main.py
```

#### Nuitka 自动下载 MinGW 失败的处理

Nuitka 默认会从 GitHub 下载一份 MinGW-w64 到 `%LOCALAPPDATA%\Nuitka\Nuitka\Cache\downloads\gcc\`。如果下载的 zip 损坏、网络不稳定，会报：

```
FATAL: Problem with the downloaded zip file, deleting it.
FATAL: Failed unexpectedly in Scons C backend compilation.
```

手动处理步骤：

1. 从 [winlibs-mingw](https://github.com/brechtsanders/winlibs_mingw/releases) 下载 `winlibs-x86_64-posix-seh-gcc-*-mingw-w64msvcrt-*-r3.zip`
2. 解压到 `C:\mingw64\`，确保 `gcc.exe` 位于 `C:\mingw64\mingw64\bin\gcc.exe`
3. 删除 Nuitka 缓存目录下损坏的版本：
   ```
   rmdir /S /Q "%LOCALAPPDATA%\Nuitka\Nuitka\Cache\downloads\gcc"
   ```
4. 把 `C:\mingw64\mingw64\bin` 加入 PATH 后再编译：
   ```bash
   nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable --experimental=force-accept-windows-gcc main.py
   ```

> 也可把 `--include-data-files=config.json=config.json` 一并加上，使默认配置随 EXE 打包。

编译完成后重命名 `main.exe` → `Launcher.exe`。

### 方法二：PyInstaller（备选，无需 C 编译器）

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name "Launcher" --add-data "config.json;." main.py
```

## 变更日志

### v2.0.3 (2026-07-09)

#### Bug 修复
- **快捷方式图标丢失**：目标软件卸载/重装后 `.lnk` 重建，Qt 图标缓存未刷新导致 `QFileIconProvider` 返回空但非 null 的图标。
  修复：新增 `_icon_has_content()` 实际渲染 pixmap 验证；`.lnk` 通过 `WScript.Shell` 解析 `TargetPath` 后从真实目标提取图标；EXE/DLL/ICO 直接 `QIcon(path)` 兜底
- **启动失败静默隐藏窗口**：原 `launch_item` 用裸 `except` 吞异常，目标失效时窗口仍隐藏、用户无反馈。
  修复：启动前校验路径（`.lnk` 先解析真实目标），失败弹 `QMessageBox` 提示 + 写日志，仅启动成功才隐藏窗口

#### 新增
- **Nuitka 自动下载 MinGW 失败的处理**：README 补充手动放置 MinGW、清缓存、加入 PATH 的步骤

### v2.0.2 (2026-06-29)

#### Bug 修复
- **右键编辑不显示对话框**：`edit_item` 创建 `EditItemDialog` 后未调用 `exec_()`，导致对话框不显示（v2.0.0 重构引入）
- **配置文件不持久**：配置文件和 EXE 放在同一目录，Nuitka onefile 模式在某些场景下路径解析不一致。
  已改为标准的 `%APPDATA%\RunLauncher\config.json`，并自动迁移旧配置
- **开机自启动无效**：注册表写入缺少 `KEY_QUERY_VALUE` 权限导致写入失败；`sys.frozen` 检测不够健壮。
  修复：添加 `_is_frozen()` + `_detect_exe_path()` 准确获取 exe 路径；写入后 `FlushKey`+读回校验
- **右键编辑不显示**：`edit_item` 创建 `EditItemDialog` 后未调用 `exec_()`（v2.0.0 重构引入）

#### 新增
- **启动日志**：每次启动写入 `%APPDATA%\RunLauncher\startup.log`，便于排查自启/启动问题

#### 其他
- `config.json` 重置为默认配置

### v2.0.1 (2026-06-26)

#### Bug 修复
- **分类对话框不显示**：`add_category` 和 `rename_category` 缺少 `exec_()` 调用，点击后无反应（v2.0.0 重构引入）

#### 优化
- **全局搜索**：搜索框现在跨所有分类搜索匹配项，不再局限于当前标签
- **跨分类编辑/删除**：搜索结果显示的跨分类项目也能正常编辑和删除
- **切换标签不清空搜索**：切换分类标签时保留搜索框内容和搜索结果

#### 其他
- `config.json` 重置为默认配置

### v2.0 (2026-06-26)

#### 重构
- 单文件 `run_launcher.py` → 模块化结构：`main.py` / `config.py` / `dialogs.py` / `window.py`

#### Bug 修复
- **热键双重触发**：原代码同时使用 `RegisterHotKey` + `WinEventFilter` 和 `GetAsyncKeyState` 轮询两套机制，
  按一次热键 `toggle()` 被调用两次导致窗口闪烁。现已移除不可靠的 `RegisterHotKey` 方式，只保留轮询检测
- **配置文件路径**：原代码使用相对路径 `config.json`，编译为 EXE 后可能找不到配置文件。
  已改用 `sys.executable` 或 `__file__` 所在目录的绝对路径
- **文件夹启动报错**：拖入文件夹后点击运行，`subprocess.Popen` + `shell=True` 将文件夹路径当作命令执行。
  已改为 `os.startfile()` 调用系统默认处理程序

#### 新增功能
- **搜索过滤**：窗口顶部添加搜索框，按名称实时过滤当前分类的快捷方式
- **编辑项目**：右键快捷方式新增"编辑"选项，可修改名称和路径
- **记住窗口位置**：隐藏/关闭窗口时保存位置坐标，下次打开自动恢复
- **开机自启动**：设置对话框增加"开机自启动"复选框，写入注册表
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **窗口关闭按钮**：右上角 × 按钮，点击隐藏到系统托盘（非退出）
- **requirements.txt**：添加依赖清单文件
