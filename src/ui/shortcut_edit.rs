use egui::{RichText, Ui};

use crate::hotkey;

pub fn show(ui: &mut Ui, value: &mut String, recording: &mut bool) {
    let text = if *recording {
        "请按快捷键… (Esc 清除)".to_string()
    } else if value.is_empty() {
        "未设置".to_string()
    } else {
        value.clone()
    };

    let response = ui.add_sized(
        [ui.available_width(), 28.0],
        egui::Button::new(RichText::new(text).size(13.0)),
    );
    if response.clicked() {
        *recording = true;
    }

    if *recording {
        let events = ui.input(|input| input.events.clone());
        for event in events {
            let egui::Event::Key {
                key,
                pressed: true,
                modifiers,
                ..
            } = event
            else {
                continue;
            };
            if key == egui::Key::Escape {
                value.clear();
                *recording = false;
                break;
            }
            if let Some(formatted) = hotkey::format_from_egui(&modifiers, key) {
                *value = formatted;
                *recording = false;
                break;
            }
        }
        ui.ctx().request_repaint();
    }
}
