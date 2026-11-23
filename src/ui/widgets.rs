use egui::{Color32, CornerRadius, Response, RichText, Sense, Stroke, Ui, vec2};

use super::theme::{ACCENT, TEXT, TEXT_DIM};

pub fn close_button(ui: &mut Ui) -> bool {
    let (rect, response) = ui.allocate_exact_size(vec2(24.0, 24.0), Sense::click());
    let hovered = response.hovered();
    let painter = ui.painter();
    if hovered {
        painter.rect_filled(
            rect,
            CornerRadius::same(4),
            Color32::from_rgba_unmultiplied(255, 60, 60, 150),
        );
    }
    let color = if hovered { TEXT } else { TEXT_DIM };
    let stroke = Stroke::new(2.0, color);
    let margin = 7.0;
    painter.line_segment(
        [
            rect.left_top() + vec2(margin, margin),
            rect.right_bottom() - vec2(margin, margin),
        ],
        stroke,
    );
    painter.line_segment(
        [
            rect.right_top() + vec2(-margin, margin),
            rect.left_bottom() + vec2(margin, -margin),
        ],
        stroke,
    );
    response.clicked()
}

pub fn pill(ui: &mut Ui, text: &str, selected: bool) -> Response {
    let fill = if selected {
        ACCENT
    } else {
        Color32::from_rgba_unmultiplied(255, 255, 255, 14)
    };
    let color = if selected { Color32::WHITE } else { TEXT_DIM };
    ui.add(
        egui::Button::new(RichText::new(text).color(color).size(13.0))
            .fill(fill)
            .min_size(vec2(0.0, 32.0)),
    )
}

pub fn split_label(name: &str, first: usize, second: usize) -> (String, Option<String>) {
    let chars: Vec<char> = name.chars().collect();
    if chars.len() <= first {
        return (name.to_string(), None);
    }
    let line1: String = chars[..first].iter().collect();
    let remaining = &chars[first..];
    if remaining.len() <= second {
        (line1, Some(remaining.iter().collect()))
    } else {
        let line2: String = remaining[..second].iter().collect();
        (line1, Some(format!("{line2}…")))
    }
}

pub fn muted(ui: &mut Ui, text: &str) {
    ui.label(RichText::new(text).color(TEXT_DIM).size(12.0));
}
