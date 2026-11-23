use chrono::Local;
use std::fs::{self, OpenOptions};
use std::io::Write;

use crate::paths;

pub fn log(message: &str) {
    let path = paths::log_file();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let line = format!("[{}] {message}\n", Local::now().format("%Y-%m-%d %H:%M:%S"));
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = file.write_all(line.as_bytes());
    }
}

pub fn install_panic_hook() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        log(&format!("panic: {info}"));
        previous(info);
    }));
}
