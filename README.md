# Quick Launcher

一个基于 Python + PyQt5 的快速启动器，支持拖拽添加快捷方式、分类管理，可通过 Nuitka 编译为单文件 EXE。

## 功能

- **Alt+Space** 在鼠标位置显示/隐藏启动器
- 拖拽文件到启动器添加快捷方式
- 右键标签栏管理分类（添加/重命名/删除）
- 右键托盘图标 → 设置（自定义窗口标题、宽度、高度）
- 支持热键配置（`config.json` 中修改）

## 使用

1. 运行 `Launcher.exe`（已编译）或 `python run_launcher.py`
2. 按 **Alt+Space** 显示/隐藏
3. 拖拽文件到网格添加快捷方式
4. 右键标签栏管理分类

## 自定义配置

编辑 `config.json`：

```json
{
  "hotkey": { "ctrl": false, "alt": true, "shift": false, "vk": 32 },
  "window_width": 420,
  "window_height": 480,
  "title": "Launcher",
  "categories": [...]
}
```

## 从源码编译

```bash
pip install pyqt5 pywin32 nuitka
nuitka --onefile --enable-plugin=pyqt5 --windows-console-mode=disable run_launcher.py
```
