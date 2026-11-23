use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use crate::logging;
use crate::paths;

pub const MIN_WINDOW: f32 = 400.0;
pub const MIN_HEIGHT: f32 = 400.0;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Item {
    pub name: String,
    pub path: String,
    #[serde(default)]
    pub icon: Option<String>,
    #[serde(skip)]
    pub id: u64,
}

impl Item {
    pub fn new(id: u64, name: String, path: String, icon: Option<String>) -> Self {
        Self {
            name,
            path,
            icon,
            id,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Category {
    pub name: String,
    pub items: Vec<Item>,
}

impl Default for Category {
    fn default() -> Self {
        Self {
            name: "默认".to_string(),
            items: Vec::new(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct General {
    pub title: String,
    pub hotkey: String,
    pub mouse_speed_hotkey: String,
    pub mouse_speed_presets: Vec<u32>,
}

impl Default for General {
    fn default() -> Self {
        Self {
            title: "Run Launcher".to_string(),
            hotkey: "Alt+Space".to_string(),
            mouse_speed_hotkey: "Ctrl+Alt+M".to_string(),
            mouse_speed_presets: vec![5, 10, 15, 20],
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct WindowState {
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub width: f32,
    pub height: f32,
}

impl Default for WindowState {
    fn default() -> Self {
        Self {
            x: None,
            y: None,
            width: 560.0,
            height: 600.0,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {
    pub version: u32,
    pub general: General,
    pub window: WindowState,
    pub categories: Vec<Category>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            version: 1,
            general: General::default(),
            window: WindowState::default(),
            categories: vec![Category::default()],
        }
    }
}

impl Config {
    pub fn normalize(mut self) -> Self {
        if self.version == 0 {
            self.version = 1;
        }
        if self.general.title.trim().is_empty() {
            self.general.title = General::default().title;
        }
        if self.general.hotkey.trim().is_empty() {
            self.general.hotkey = General::default().hotkey;
        }
        if self.general.mouse_speed_hotkey.trim().is_empty() {
            self.general.mouse_speed_hotkey = General::default().mouse_speed_hotkey;
        }
        let mut presets: Vec<u32> = self
            .general
            .mouse_speed_presets
            .iter()
            .map(|v| (*v).clamp(1, 20))
            .collect();
        presets.sort_unstable();
        presets.dedup();
        if presets.is_empty() {
            presets = General::default().mouse_speed_presets;
        }
        self.general.mouse_speed_presets = presets;

        if !self.window.width.is_finite() || self.window.width < MIN_WINDOW {
            self.window.width = MIN_WINDOW;
        }
        if !self.window.height.is_finite() || self.window.height < MIN_HEIGHT {
            self.window.height = MIN_HEIGHT;
        }

        if self.categories.is_empty() {
            self.categories.push(Category::default());
        }
        for category in &mut self.categories {
            if category.name.trim().is_empty() {
                category.name = "未命名".to_string();
            }
            category.items.retain(|item| !item.name.trim().is_empty());
        }
        self.assign_ids();
        self
    }

    pub fn assign_ids(&mut self) {
        let mut next = 1;
        for category in &mut self.categories {
            for item in &mut category.items {
                item.id = next;
                next += 1;
            }
        }
    }

    pub fn next_id(&self) -> u64 {
        self.categories
            .iter()
            .flat_map(|c| c.items.iter())
            .map(|i| i.id)
            .max()
            .unwrap_or(0)
            + 1
    }
}

pub fn load() -> Config {
    let path = paths::config_file();
    match fs::read_to_string(&path) {
        Ok(text) => match serde_json::from_str::<Config>(&text) {
            Ok(config) => config.normalize(),
            Err(err) => {
                logging::log(&format!("config parse failed: {err}"));
                Config::default()
            }
        },
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Config::default(),
        Err(err) => {
            logging::log(&format!("config read failed: {err}"));
            Config::default()
        }
    }
}

pub fn save(config: &Config) -> Result<(), String> {
    let path = paths::config_file();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create config dir: {e}"))?;
    }
    let text =
        serde_json::to_string_pretty(config).map_err(|e| format!("serialize config: {e}"))?;
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
    fs::write(&tmp, text).map_err(|e| format!("write config tmp: {e}"))?;
    if let Err(err) = fs::rename(&tmp, &path) {
        let _ = fs::remove_file(&path);
        fs::rename(&tmp, &path).map_err(|e| format!("replace config ({err}): {e}"))?;
    }
    Ok(())
}

pub fn fingerprint(path: &Path) -> String {
    let absolute = std::path::absolute(path).unwrap_or_else(|_| path.to_path_buf());
    let normalized = absolute.to_string_lossy().replace('/', "\\").to_lowercase();
    match fs::metadata(&absolute) {
        Ok(meta) => {
            let modified = meta
                .modified()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            format!("{normalized}|{modified}|{}", meta.len())
        }
        Err(_) => format!("{normalized}|0|0"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_are_normalized() {
        let config = Config::default().normalize();
        assert_eq!(config.categories.len(), 1);
        assert!(config.window.width >= MIN_WINDOW);
        assert_eq!(config.general.mouse_speed_presets, vec![5, 10, 15, 20]);
    }

    #[test]
    fn presets_are_clamped_and_deduped() {
        let mut config = Config::default();
        config.general.mouse_speed_presets = vec![99, 5, 5, 0, 12];
        let config = config.normalize();
        assert_eq!(config.general.mouse_speed_presets, vec![1, 5, 12, 20]);
    }
}
