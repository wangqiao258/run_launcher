use std::collections::{HashMap, VecDeque};
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Receiver, Sender, TryRecvError};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use base64::Engine as _;
use base64::engine::general_purpose::STANDARD as BASE64;
use serde::{Deserialize, Serialize};

use crate::events::{AppEvent, IconReady};
use crate::icons::shell;
use crate::lnk_cache;
use crate::logging;
use crate::paths;

const CACHE_LIMIT: usize = 512;

#[derive(Debug)]
struct Request {
    logical_key: String,
    disk_key: String,
    path: PathBuf,
    icon: Option<PathBuf>,
}

enum WorkerMsg {
    Foreground(Request),
    Background(Request),
    Shutdown,
}

#[derive(Serialize, Deserialize)]
struct CacheFile {
    version: u32,
    icons: HashMap<String, String>,
}

pub struct IconWorker {
    foreground: Sender<WorkerMsg>,
    background: Sender<WorkerMsg>,
    join: Option<JoinHandle<()>>,
}

impl IconWorker {
    pub fn spawn(ctx: egui::Context, events: Sender<AppEvent>) -> Self {
        let (fg_tx, fg_rx) = mpsc::channel();
        let (bg_tx, bg_rx) = mpsc::channel();
        let join = thread::spawn(move || worker_loop(ctx, events, fg_rx, bg_rx));

        Self {
            foreground: fg_tx,
            background: bg_tx,
            join: Some(join),
        }
    }

    pub fn request(&self, request: IconRequest, foreground: bool) {
        let request = Request {
            logical_key: request.logical_key,
            disk_key: request.disk_key,
            path: request.path,
            icon: request.icon,
        };
        let result = if foreground {
            self.foreground.send(WorkerMsg::Foreground(request))
        } else {
            self.background.send(WorkerMsg::Background(request))
        };
        if let Err(err) = result {
            logging::log(&format!("icon queue failed: {err}"));
        }
    }

    pub fn stop(&mut self) {
        let _ = self.foreground.send(WorkerMsg::Shutdown);
        if let Some(join) = self.join.take() {
            let _ = join.join();
        }
    }
}

pub struct IconRequest {
    pub logical_key: String,
    pub disk_key: String,
    pub path: PathBuf,
    pub icon: Option<PathBuf>,
}

fn worker_loop(
    ctx: egui::Context,
    events: Sender<AppEvent>,
    foreground: Receiver<WorkerMsg>,
    background: Receiver<WorkerMsg>,
) {
    let mut cache = load_cache();
    let mut order: VecDeque<String> = cache.keys().cloned().collect();
    let mut dirty = false;
    let mut last_save = Instant::now();

    loop {
        let mut worked = false;

        while let Ok(message) = foreground.try_recv() {
            match message {
                WorkerMsg::Shutdown => {
                    if dirty {
                        save_cache(&cache);
                    }
                    return;
                }
                WorkerMsg::Foreground(request) => {
                    process(request, &mut cache, &mut order, &ctx, &events);
                    dirty = true;
                    worked = true;
                }
                WorkerMsg::Background(_) => {}
            }
        }

        if !worked {
            match background.try_recv() {
                Ok(WorkerMsg::Background(request)) => {
                    process(request, &mut cache, &mut order, &ctx, &events);
                    dirty = true;
                    worked = true;
                }
                Ok(WorkerMsg::Foreground(request)) => {
                    process(request, &mut cache, &mut order, &ctx, &events);
                    dirty = true;
                    worked = true;
                }
                Ok(WorkerMsg::Shutdown) => {
                    if dirty {
                        save_cache(&cache);
                    }
                    return;
                }
                Err(TryRecvError::Disconnected) => return,
                Err(TryRecvError::Empty) => {}
            }
        }

        if !worked {
            match foreground.recv_timeout(Duration::from_millis(50)) {
                Ok(WorkerMsg::Shutdown) => {
                    if dirty {
                        save_cache(&cache);
                    }
                    return;
                }
                Ok(WorkerMsg::Foreground(request)) => {
                    process(request, &mut cache, &mut order, &ctx, &events);
                    dirty = true;
                }
                Ok(WorkerMsg::Background(_)) => {}
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => return,
            }
        }

        if dirty && last_save.elapsed() >= Duration::from_millis(250) {
            save_cache(&cache);
            dirty = false;
            last_save = Instant::now();
        }
    }
}

fn process(
    request: Request,
    cache: &mut HashMap<String, String>,
    order: &mut VecDeque<String>,
    ctx: &egui::Context,
    events: &Sender<AppEvent>,
) {
    match extract_icon(&request.path, request.icon.as_deref()) {
        Some(rgba) => {
            if let Some(png) = encode_png(&rgba) {
                if !cache.contains_key(&request.disk_key) {
                    order.push_back(request.disk_key.clone());
                }
                cache.insert(request.disk_key.clone(), BASE64.encode(&png));
                while cache.len() > CACHE_LIMIT {
                    if let Some(old) = order.pop_front() {
                        cache.remove(&old);
                    } else {
                        break;
                    }
                }
                let _ = events.send(AppEvent::IconReady(IconReady {
                    key: request.logical_key,
                    rgba: rgba.pixels,
                    width: rgba.width,
                    height: rgba.height,
                }));
            } else {
                let _ = events.send(AppEvent::IconFailed(request.logical_key));
            }
        }
        None => {
            let _ = events.send(AppEvent::IconFailed(request.logical_key));
        }
    }
    ctx.request_repaint();
}

fn extract_icon(path: &Path, icon: Option<&Path>) -> Option<shell::RgbaIcon> {
    if let Some(icon_path) = icon.filter(|p| p.is_file()) {
        if let Ok(image) = image::open(icon_path) {
            let rgba = image.to_rgba8();
            return Some(shell::RgbaIcon {
                width: rgba.width(),
                height: rgba.height(),
                pixels: rgba.into_raw(),
            });
        }
        if let Some(rgba) = shell::extract_from_path(icon_path) {
            return Some(rgba);
        }
    }

    if path.is_file()
        && let Some(rgba) = shell::extract_from_path(path)
    {
        return Some(rgba);
    }

    let is_lnk = path
        .extension()
        .map(|ext| ext.eq_ignore_ascii_case("lnk"))
        .unwrap_or(false);
    if is_lnk
        && let Some(target) = lnk_cache::resolve(path)
        && let Some(rgba) = shell::extract_from_path(&target)
    {
        return Some(rgba);
    }

    shell::extract_shell_icon(path)
}

fn encode_png(rgba: &shell::RgbaIcon) -> Option<Vec<u8>> {
    let image = image::RgbaImage::from_raw(rgba.width, rgba.height, rgba.pixels.clone())?;
    let image = if rgba.width > 64 || rgba.height > 64 {
        image::imageops::resize(&image, 64, 64, image::imageops::FilterType::Lanczos3)
    } else {
        image
    };
    let mut png = Vec::new();
    image::DynamicImage::ImageRgba8(image)
        .write_to(&mut Cursor::new(&mut png), image::ImageFormat::Png)
        .ok()?;
    Some(png)
}

fn load_cache() -> HashMap<String, String> {
    let path = paths::icon_cache_file();
    let text = match fs::read_to_string(path) {
        Ok(text) => text,
        Err(_) => return HashMap::new(),
    };
    let file: CacheFile = match serde_json::from_str::<CacheFile>(&text) {
        Ok(file) if file.version == 1 => file,
        Ok(_) => return HashMap::new(),
        Err(err) => {
            logging::log(&format!("load icon cache failed: {err}"));
            return HashMap::new();
        }
    };
    file.icons
}

fn save_cache(cache: &HashMap<String, String>) {
    let path = paths::icon_cache_file();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let file = CacheFile {
        version: 1,
        icons: cache.clone(),
    };
    let text = match serde_json::to_string(&file) {
        Ok(text) => text,
        Err(err) => {
            logging::log(&format!("serialize icon cache failed: {err}"));
            return;
        }
    };
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
    if fs::write(&tmp, text).is_err() {
        return;
    }
    if fs::rename(&tmp, &path).is_err() {
        let _ = fs::remove_file(&path);
        let _ = fs::rename(&tmp, &path);
    }
}
