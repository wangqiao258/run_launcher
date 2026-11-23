use egui::{Color32, CornerRadius, Rect, Ui, pos2, vec2};

use crate::app::{ItemDrag, LauncherApp, TabDrag};
use crate::ui::theme::ACCENT;
use crate::ui::widgets;

pub enum TabAction {
    Select(usize),
    Add,
    Rename(usize),
    Delete(usize),
    MoveItems { ids: Vec<u64>, destination: usize },
    Reorder { from: usize, to: usize },
}

pub fn show(app: &mut LauncherApp, ui: &mut Ui) -> Option<TabAction> {
    let categories: Vec<String> = app
        .config
        .categories
        .iter()
        .map(|category| category.name.clone())
        .collect();
    let count = categories.len();
    let current = app.current_cat;
    let mut action = None;

    egui::ScrollArea::horizontal()
        .max_height(40.0)
        .auto_shrink([false, true])
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                for (index, name) in categories.iter().enumerate() {
                    let response = widgets::pill(ui, name, index == current);
                    if response.clicked() {
                        action = Some(TabAction::Select(index));
                    }

                    if response.drag_started() {
                        response.dnd_set_drag_payload(TabDrag { from: index });
                    }
                    if response.dnd_hover_payload::<ItemDrag>().is_some() {
                        let rect = Rect::from_min_size(
                            pos2(response.rect.left() + 4.0, response.rect.bottom() - 4.0),
                            vec2((response.rect.width() - 8.0).max(0.0), 2.0),
                        );
                        ui.painter()
                            .rect_filled(rect, CornerRadius::same(1), ACCENT);
                    }
                    if let Some(payload) = response.dnd_release_payload::<ItemDrag>() {
                        action = Some(TabAction::MoveItems {
                            ids: payload.ids.clone(),
                            destination: index,
                        });
                    }
                    if let Some(payload) = response.dnd_release_payload::<TabDrag>()
                        && payload.from != index
                    {
                        action = Some(TabAction::Reorder {
                            from: payload.from,
                            to: index,
                        });
                    }

                    response.context_menu(|ui| {
                        if ui.button("添加分类").clicked() {
                            action = Some(TabAction::Add);
                            ui.close();
                        }
                        if ui.button("重命名").clicked() {
                            action = Some(TabAction::Rename(index));
                            ui.close();
                        }
                        if count > 1 && ui.button("删除").clicked() {
                            action = Some(TabAction::Delete(index));
                            ui.close();
                        }
                    });
                }

                if ui
                    .add(
                        egui::Button::new(egui::RichText::new("+").size(16.0))
                            .fill(Color32::from_rgba_unmultiplied(255, 255, 255, 14))
                            .min_size(vec2(32.0, 32.0)),
                    )
                    .clicked()
                {
                    action = Some(TabAction::Add);
                }
            });
        });

    action
}
