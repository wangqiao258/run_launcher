use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::mpsc::Sender;

use base64::Engine as _;
use base64::engine::general_purpose::STANDARD as BASE64;
use serde::Deserialize;
use sha2::{Digest, Sha256};

use crate::config::{self, Category, Item};
use crate::events::{AppEvent, IconReady};
use crate::icons::worker::{IconRequest, IconWorker};
use crate::logging;
use crate::paths;

pub mod shell;
pub mod worker;

const TEXTURE_LIMIT: usize = 512;

pub struct IconStore {
    textures: HashMap<String, egui::TextureHandle>,
    order: VecDeque<String>,
    disk: HashMap<String, String>,
    pending: HashSet<String>,
    failed: HashSet<String>,
    worker: Option<IconWorker>,
}

#[derive(Deserialize)]
struct CacheFile {
    version: u32,
    icons: HashMap<String, String>,
}

impl IconStore {
    pub fn new(ctx: &egui::Context, events: Sender<AppEvent>) -> Self {
        let mut disk = load_disk_cache();
        if disk.len() > 512 {
            disk = disk.into_iter().take(512).collect();
        }
        Self {
            textures: HashMap::new(),
            order: VecDeque::new(),
            disk,
            pending: HashSet::new(),
            failed: HashSet::new(),
            worker: Some(IconWorker::spawn(ctx.clone(), events)),
        }
    }

    pub fn texture_for(
        &mut self,
        ctx: &egui::Context,
        item: &Item,
        foreground: bool,
    ) -> Option<egui::TextureHandle> {
        let key = key_for_item(item);
        if key.is_empty() {
            return None;
        }
        if let Some(texture) = self.textures.get(&key) {
            return Some(texture.clone());
        }
        if let Some(texture) = self.decode_cached(ctx, &key) {
            return Some(texture);
        }
        self.request(item, foreground, false);
        None
    }

    pub fn on_ready(&mut self, ctx: &egui::Context, ready: IconReady) {
        self.pending.remove(&ready.key);
        self.failed.remove(&ready.key);

        let image = egui::ColorImage::from_rgba_unmultiplied(
            [ready.width as usize, ready.height as usize],
            &ready.rgba,
        );
        let texture = ctx.load_texture(&ready.key, image, egui::TextureOptions::LINEAR);
        if !self.textures.contains_key(&ready.key) {
            self.order.push_back(ready.key.clone());
        }
        self.textures.insert(ready.key, texture);
        while self.textures.len() > TEXTURE_LIMIT {
            if let Some(old) = self.order.pop_front() {
                self.textures.remove(&old);
            } else {
                break;
            }
        }
    }

    pub fn on_failed(&mut self, key: String) {
        self.pending.remove(&key);
        self.failed.insert(key);
    }

    pub fn clear_failures(&mut self) {
        self.failed.clear();
    }

    pub fn preload(&mut self, categories: &[Category]) {
        for category in categories {
            for item in &category.items {
                let key = key_for_item(item);
                if key.is_empty() || self.textures.contains_key(&key) {
                    continue;
                }
                let is_lnk = item.path.to_lowercase().ends_with(".lnk");
                self.request(item, false, is_lnk);
            }
        }
    }

    pub fn shutdown(&mut self) {
        if let Some(worker) = &mut self.worker {
            worker.stop();
        }
        self.worker = None;
    }

    fn request(&mut self, item: &Item, foreground: bool, force: bool) {
        let logical_key = key_for_item(item);
        if logical_key.is_empty()
            || self.pending.contains(&logical_key)
            || self.failed.contains(&logical_key)
            || self.textures.contains_key(&logical_key)
        {
            return;
        }
        let disk_key = disk_key(&logical_key);
        if !force && self.disk.contains_key(&disk_key) {
            return;
        }
        if let Some(worker) = &self.worker {
            worker.request(
                IconRequest {
                    logical_key: logical_key.clone(),
                    disk_key,
                    path: PathBuf::from(&item.path),
                    icon: item.icon.as_ref().map(PathBuf::from),
                },
                foreground,
            );
            self.pending.insert(logical_key);
        }
    }

    fn decode_cached(&mut self, ctx: &egui::Context, key: &str) -> Option<egui::TextureHandle> {
        let disk_key = disk_key(key);
        let encoded = self.disk.get(&disk_key)?.clone();
        let bytes = match BASE64.decode(encoded) {
            Ok(bytes) => bytes,
            Err(_) => {
                self.disk.remove(&disk_key);
                return None;
            }
        };
        let image = match image::load_from_memory(&bytes) {
            Ok(image) => image.to_rgba8(),
            Err(_) => {
                self.disk.remove(&disk_key);
                return None;
            }
        };
        let color_image = egui::ColorImage::from_rgba_unmultiplied(
            [image.width() as usize, image.height() as usize],
            image.as_raw(),
        );
        let texture = ctx.load_texture(key, color_image, egui::TextureOptions::LINEAR);
        if !self.textures.contains_key(key) {
            self.order.push_back(key.to_string());
        }
        self.textures.insert(key.to_string(), texture.clone());
        Some(texture)
    }
}

pub fn key_for_item(item: &Item) -> String {
    if item.path.trim().is_empty() {
        return String::new();
    }
    let path_fingerprint = config::fingerprint(Path::new(&item.path));
    if let Some(icon) = &item.icon {
        let icon_path = Path::new(icon);
        if icon_path.is_file() {
            return format!(
                "icon|{}|{}",
                config::fingerprint(icon_path),
                path_fingerprint
            );
        }
    }
    format!("path|{path_fingerprint}")
}

pub fn disk_key(logical_key: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(logical_key.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn load_disk_cache() -> HashMap<String, String> {
    let path = paths::icon_cache_file();
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(_) => return HashMap::new(),
    };
    match serde_json::from_str::<CacheFile>(&text) {
        Ok(file) if file.version == 1 => file.icons,
        Ok(_) => HashMap::new(),
        Err(err) => {
            logging::log(&format!("icon cache load failed: {err}"));
            HashMap::new()
        }
    }
}
