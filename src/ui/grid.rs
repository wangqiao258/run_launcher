use egui::{Align2, Color32, CornerRadius, FontId, Rect, Sense, Ui, pos2, vec2};

use crate::app::{ItemDrag, LauncherApp};
use crate::config::Item;
use crate::ui::theme::{ACCENT, SURFACE, TEXT, TEXT_DIM, hover, selected};
use crate::ui::widgets;

enum GridAction {
    Select(u64, bool, bool),
    Launch(u64),
    LaunchAdmin(u64),
    OpenPath(u64),
    Edit(u64),
    Delete(u64),
    DeleteSelected,
}

pub fn show(app: &mut LauncherApp, ui: &mut Ui, max_height: f32) {
    let visible = app.visible_items();
    let mut entries = Vec::new();
    for (category_index, item_index) in visible {
        if let Some(item) = app
            .config
            .categories
            .get(category_index)
            .and_then(|category| category.items.get(item_index))
        {
            entries.push(item.clone());
        }
    }

    let ctx = ui.ctx().clone();
    let mut actions = Vec::new();
    let has_filter = !app.filter.trim().is_empty();

    egui::ScrollArea::vertical()
        .max_height(max_height)
        .auto_shrink([false, false])
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            let background = ui.interact(
                ui.max_rect(),
                ui.scope_id().with("grid-bg"),
                Sense::click_and_drag(),
            );
            let drag_started = background.drag_started();
            let dragging = background.dragged();
            let drag_stopped = background.drag_stopped();
            if background.clicked() {
                app.selected.clear();
                if let Some(search_id) = app.search_id {
                    ui.ctx().memory_mut(|memory| memory.surrender_focus(search_id));
                }
            }
            if drag_started && let Some(position) = ui.input(|input| input.pointer.interact_pos()) {
                app.marquee_start = Some(position);
                app.marquee_current = Some(position);
            }
            if dragging && let Some(position) = ui.input(|input| input.pointer.interact_pos()) {
                app.marquee_current = Some(position);
            }

            if entries.is_empty() {
                ui.add_space(48.0);
                ui.vertical_centered(|ui| {
                    let text = if has_filter {
                        "没有匹配项"
                    } else {
                        "拖入文件或文件夹开始"
                    };
                    ui.label(egui::RichText::new(text).color(TEXT_DIM).size(14.0));
                });
                return;
            }

            let cell = 88.0;
            let gap = 8.0;
            let columns = (((ui.available_width() + gap) / (cell + gap)).floor() as usize).max(1);
            ui.spacing_mut().item_spacing = vec2(gap, gap);
            let mut cell_rects = Vec::new();

            for row in entries.chunks(columns) {
                ui.horizontal(|ui| {
                    for item in row {
                        draw_cell(ui, app, item, &mut actions, &mut cell_rects);
                    }
                });
            }

            if let (Some(start), Some(current)) = (app.marquee_start, app.marquee_current) {
                let marquee = Rect::from_two_pos(start, current);
                ui.painter().rect_filled(
                    marquee,
                    CornerRadius::same(2),
                    Color32::from_rgba_unmultiplied(74, 158, 255, 40),
                );
            }

            if drag_stopped {
                let marquee = match (app.marquee_start, app.marquee_current) {
                    (Some(start), Some(current)) => Some(Rect::from_two_pos(start, current)),
                    _ => None,
                };
                if let Some(marquee) = marquee
                    && marquee.width() * marquee.height() > 16.0
                {
                    app.selected.clear();
                    for (id, cell_rect) in &cell_rects {
                        if marquee.intersects(*cell_rect) {
                            app.selected.insert(*id);
                        }
                    }
                }
                app.marquee_start = None;
                app.marquee_current = None;
            }
        });

    for action in actions {
        match action {
            GridAction::Select(id, ctrl, shift) => app.select_clicked(id, ctrl, shift),
            GridAction::Launch(id) => app.launch_item(&ctx, id, false),
            GridAction::LaunchAdmin(id) => app.launch_item(&ctx, id, true),
            GridAction::OpenPath(id) => app.open_item_path(id),
            GridAction::Edit(id) => app.edit_item(id),
            GridAction::Delete(id) => app.remove_item(id),
            GridAction::DeleteSelected => app.delete_selected(),
        }
    }

    if matches!(app.dialog, crate::app::Dialog::None)
        && ctx.memory(|memory| memory.focused()) != app.search_id
        && ui.input(|input| input.key_pressed(egui::Key::Delete))
    {
        app.delete_selected();
    }
}

fn draw_cell(
    ui: &mut Ui,
    app: &mut LauncherApp,
    item: &Item,
    actions: &mut Vec<GridAction>,
    cell_rects: &mut Vec<(u64, Rect)>,
) {
    let (rect, response) = ui.allocate_exact_size(vec2(88.0, 88.0), Sense::click_and_drag());
    cell_rects.push((item.id, rect));
    let is_selected = app.selected.contains(&item.id);
    let painter = ui.painter();

    if is_selected {
        painter.rect_filled(rect, CornerRadius::same(8), selected());
    } else if response.hovered() {
        painter.rect_filled(rect, CornerRadius::same(8), hover());
    }

    let icon_rect =
        Rect::from_center_size(pos2(rect.center().x, rect.top() + 30.0), vec2(40.0, 40.0));
    if let Some(texture) = app.icons.texture_for(ui.ctx(), item, true) {
        painter.image(
            texture.id(),
            icon_rect,
            Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0)),
            Color32::WHITE,
        );
    } else {
        painter.rect_filled(icon_rect.shrink(4.0), CornerRadius::same(6), SURFACE);
    }

    let (line1, line2) = widgets::split_label(&item.name, 9, 7);
    let center = rect.center().x;
    painter.text(
        pos2(center, rect.top() + 54.0),
        Align2::CENTER_TOP,
        line1,
        FontId::proportional(12.0),
        if is_selected { ACCENT } else { TEXT },
    );
    if let Some(line2) = line2 {
        painter.text(
            pos2(center, rect.top() + 69.0),
            Align2::CENTER_TOP,
            line2,
            FontId::proportional(12.0),
            if is_selected { ACCENT } else { TEXT },
        );
    }

    if response.clicked() {
        if let Some(search_id) = app.search_id {
            ui.ctx().memory_mut(|memory| memory.surrender_focus(search_id));
        }
        let modifiers = ui.input(|input| input.modifiers);
        actions.push(GridAction::Select(item.id, modifiers.ctrl, modifiers.shift));
    }
    if response.double_clicked() {
        actions.push(GridAction::Launch(item.id));
    }
    if response.drag_started() {
        let ids = if app.selected.contains(&item.id) {
            app.selected_ids()
        } else {
            actions.push(GridAction::Select(item.id, false, false));
            vec![item.id]
        };
        response.dnd_set_drag_payload(ItemDrag { ids });
    }

    let is_multi = app.selected.len() > 1 && app.selected.contains(&item.id);
    let selected_count = app.selected.len();
    response.context_menu(|ui| {
        if is_multi {
            if ui
                .button(format!("删除选中项 ({selected_count})"))
                .clicked()
            {
                actions.push(GridAction::DeleteSelected);
                ui.close();
            }
            return;
        }
        if ui.button("打开路径").clicked() {
            actions.push(GridAction::OpenPath(item.id));
            ui.close();
        }
        if ui.button("以管理员身份运行").clicked() {
            actions.push(GridAction::LaunchAdmin(item.id));
            ui.close();
        }
        ui.separator();
        if ui.button("编辑").clicked() {
            actions.push(GridAction::Edit(item.id));
            ui.close();
        }
        if ui.button("删除").clicked() {
            actions.push(GridAction::Delete(item.id));
            ui.close();
        }
    });
}
