use std::fs;
use std::sync::Arc;

use egui::{Color32, CornerRadius, FontData, FontDefinitions, FontFamily, Stroke, vec2};

pub const ACCENT: Color32 = Color32::from_rgb(74, 158, 255);
pub const TEXT: Color32 = Color32::from_rgb(255, 255, 255);
pub const TEXT_DIM: Color32 = Color32::from_rgb(160, 160, 176);
pub const SURFACE: Color32 = Color32::from_rgb(42, 42, 54);
pub const DANGER: Color32 = Color32::from_rgb(255, 92, 92);

pub fn background() -> Color32 {
    Color32::from_rgba_unmultiplied(30, 30, 40, 248)
}

pub fn hover() -> Color32 {
    Color32::from_rgba_unmultiplied(255, 255, 255, 20)
}

pub fn selected() -> Color32 {
    Color32::from_rgba_unmultiplied(255, 255, 255, 31)
}

pub fn install(ctx: &egui::Context) {
    install_fonts(ctx);

    ctx.set_theme(egui::ThemePreference::Dark);
    let theme = egui::Theme::Dark;
    let mut style = (*ctx.style_of(theme)).clone();
    style.visuals = egui::Visuals::dark();
    style.visuals.panel_fill = background();
    style.visuals.window_fill = SURFACE;
    style.visuals.extreme_bg_color = Color32::from_rgb(24, 24, 32);
    style.visuals.override_text_color = Some(TEXT);
    style.visuals.selection.bg_fill = ACCENT;
    style.visuals.selection.stroke = Stroke::new(1.0, TEXT);
    style.visuals.widgets.inactive.bg_fill = SURFACE;
    style.visuals.widgets.inactive.weak_bg_fill = SURFACE;
    style.visuals.widgets.inactive.fg_stroke = Stroke::new(1.0, TEXT);
    style.visuals.widgets.inactive.corner_radius = CornerRadius::same(8);
    style.visuals.widgets.hovered.bg_fill = Color32::from_rgb(52, 52, 66);
    style.visuals.widgets.hovered.fg_stroke = Stroke::new(1.0, TEXT);
    style.visuals.widgets.hovered.corner_radius = CornerRadius::same(8);
    style.visuals.widgets.active.bg_fill = Color32::from_rgb(62, 62, 78);
    style.visuals.widgets.active.fg_stroke = Stroke::new(1.0, TEXT);
    style.visuals.widgets.active.corner_radius = CornerRadius::same(8);
    style.visuals.window_corner_radius = CornerRadius::same(12);
    style.spacing.item_spacing = vec2(8.0, 8.0);
    style.spacing.button_padding = vec2(12.0, 6.0);
    ctx.set_style_of(theme, style);
}

fn install_fonts(ctx: &egui::Context) {
    let candidates = [
        (r"C:\Windows\Fonts\msyh.ttc", "msyh"),
        (r"C:\Windows\Fonts\msyh.ttf", "msyh"),
        (r"C:\Windows\Fonts\simhei.ttf", "simhei"),
        (r"C:\Windows\Fonts\simsun.ttc", "simsun"),
    ];

    let mut found = None;
    for (path, name) in candidates {
        if let Ok(bytes) = fs::read(path) {
            found = Some((name.to_string(), bytes));
            break;
        }
    }
    let Some((name, bytes)) = found else {
        return;
    };

    let mut fonts = FontDefinitions::default();
    fonts
        .font_data
        .insert(name.clone(), Arc::new(FontData::from_owned(bytes)));
    for family in [FontFamily::Proportional, FontFamily::Monospace] {
        fonts.families.entry(family).or_default().push(name.clone());
    }
    ctx.set_fonts(fonts);
}
