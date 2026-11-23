use std::env;
use std::path::PathBuf;

pub fn config_dir() -> PathBuf {
    base_dir("APPDATA")
        .unwrap_or_else(home_dir)
        .join("wangqiao258")
        .join("RunLauncher")
}

pub fn local_dir() -> PathBuf {
    base_dir("LOCALAPPDATA")
        .or_else(|| base_dir("APPDATA"))
        .unwrap_or_else(home_dir)
        .join("wangqiao258")
        .join("RunLauncher")
}

pub fn config_file() -> PathBuf {
    config_dir().join("config.json")
}

pub fn icon_cache_file() -> PathBuf {
    local_dir().join("icon-cache.json")
}

pub fn log_file() -> PathBuf {
    local_dir().join("startup.log")
}

fn base_dir(name: &str) -> Option<PathBuf> {
    env::var_os(name)
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
}

fn home_dir() -> PathBuf {
    env::var_os("USERPROFILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}
