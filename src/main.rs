#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod config;
mod events;
mod hotkey;
mod icons;
mod launch;
mod lnk_cache;
mod logging;
mod mouse_speed;
mod paths;
mod search;
mod startup;
mod ui;

use eframe::egui;

fn main() -> eframe::Result {
    logging::install_panic_hook();
    logging::log(&format!(
        "Launcher starting, exe={}",
        std::env::current_exe()
            .map(|path| path.display().to_string())
            .unwrap_or_default()
    ));

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Run Launcher")
            .with_decorations(false)
            .with_transparent(true)
            .with_always_on_top()
            .with_taskbar(false)
            .with_resizable(true)
            .with_inner_size([560.0, 600.0])
            .with_min_inner_size([400.0, 400.0])
            .with_visible(false),
        ..Default::default()
    };

    let result = eframe::run_native(
        "Run Launcher",
        options,
        Box::new(|cc| Ok(Box::new(app::LauncherApp::new(cc)) as Box<dyn eframe::App>)),
    );
    if let Err(err) = &result {
        logging::log(&format!("eframe exited with error: {err}"));
    }
    result
}
