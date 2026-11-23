use std::path::{Path, PathBuf};
use std::process::Command;
use std::ptr;

use windows_sys::Win32::UI::Shell::ShellExecuteW;
use windows_sys::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;

use crate::lnk_cache;

fn wide(text: &str) -> Vec<u16> {
    text.encode_utf16().chain(std::iter::once(0)).collect()
}

fn shell_execute(operation: &str, file: &str, directory: Option<&Path>) -> Result<(), String> {
    let operation = wide(operation);
    let file = wide(file);
    let directory = directory.map(|dir| wide(&dir.to_string_lossy()));
    let directory_ptr = directory
        .as_ref()
        .map(|value| value.as_ptr())
        .unwrap_or(ptr::null());

    let result = unsafe {
        ShellExecuteW(
            ptr::null_mut(),
            operation.as_ptr(),
            file.as_ptr(),
            ptr::null(),
            directory_ptr,
            SW_SHOWNORMAL,
        )
    };
    let code = result as isize;
    if code <= 32 {
        Err(format!("ShellExecuteW failed (code {code})"))
    } else {
        Ok(())
    }
}

pub fn launch(path: &Path, admin: bool) -> Result<(), String> {
    let operation = if admin { "runas" } else { "open" };
    let directory = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty());
    shell_execute(operation, &path.to_string_lossy(), directory)
}

pub fn open_url(url: &str) -> Result<(), String> {
    shell_execute("open", url, None)
}

pub fn open_folder(path: &Path) -> Result<(), String> {
    let resolved = resolve_for_open(path);
    let folder: PathBuf = if resolved.is_dir() {
        resolved
    } else {
        resolved
            .parent()
            .map(Path::to_path_buf)
            .ok_or_else(|| format!("无法定位文件夹: {}", path.display()))?
    };

    if !folder.is_dir() {
        return Err(format!("找不到文件夹：\n{}", folder.display()));
    }

    Command::new("explorer.exe")
        .arg(&folder)
        .spawn()
        .map(|_| ())
        .map_err(|err| format!("打开路径失败: {err}"))
}

fn resolve_for_open(path: &Path) -> PathBuf {
    let is_lnk = path
        .extension()
        .map(|ext| ext.eq_ignore_ascii_case("lnk"))
        .unwrap_or(false);
    if is_lnk && let Some(target) = lnk_cache::resolve(path) {
        return target;
    }
    path.to_path_buf()
}
