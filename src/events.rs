use std::sync::mpsc::Sender;

use global_hotkey::GlobalHotKeyEvent;
use tray_icon::menu::MenuEvent;
use tray_icon::TrayIconEvent;

#[derive(Debug, Clone)]
pub struct IconReady {
    pub key: String,
    pub rgba: Vec<u8>,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone)]
pub enum AppEvent {
    Hotkey(u32),
    TrayDoubleClick,
    Menu(String),
    IconReady(IconReady),
    IconFailed(String),
    Error(String),
}

pub fn spawn_wakers(tx: Sender<AppEvent>, ctx: egui::Context) {
    {
        let tx = tx.clone();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let receiver = GlobalHotKeyEvent::receiver();
            while let Ok(event) = receiver.recv() {
                if event.state == global_hotkey::HotKeyState::Pressed {
                    let _ = tx.send(AppEvent::Hotkey(event.id));
                    ctx.request_repaint();
                }
            }
        });
    }

    {
        let tx = tx.clone();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let receiver = MenuEvent::receiver();
            while let Ok(event) = receiver.recv() {
                let _ = tx.send(AppEvent::Menu(event.id.0));
                ctx.request_repaint();
            }
        });
    }

    {
        let tx = tx;
        let ctx = ctx;
        std::thread::spawn(move || {
            let receiver = TrayIconEvent::receiver();
            while let Ok(event) = receiver.recv() {
                if matches!(event, TrayIconEvent::DoubleClick { .. }) {
                    let _ = tx.send(AppEvent::TrayDoubleClick);
                    ctx.request_repaint();
                }
            }
        });
    }
}
