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

编辑 `config.json`：

```json
{
  "hotkey": { "ctrl": false, "alt": true, "shift": false, "vk": 32 },
  "window_width": 420,
  "window_height": 480,
  "title": "Launcher",
  "pos_x": null,
  "pos_y": null,
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

编译完成后重命名 `main.exe` → `Launcher.exe`。

### 方法二：PyInstaller（备选，无需 C 编译器）

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name "Launcher" --add-data "config.json;." main.py
```

## 变更日志

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
