use egui::{Align2, Color32, RichText, Sense, vec2};

use crate::app::{Dialog, InputPurpose, LauncherApp};
use crate::ui::theme::{ACCENT, DANGER, TEXT_DIM};

pub fn show(app: &mut LauncherApp, ctx: &egui::Context) {
    if matches!(app.dialog, Dialog::None) {
        return;
    }

    draw_overlay(ctx);
    let mut dialog = std::mem::replace(&mut app.dialog, Dialog::None);
    let mut keep = true;
    let mut cancel_settings = false;

    match &mut dialog {
        Dialog::Settings(state) => {
            let mut submit = false;
            let mut cancel = false;
            let was_recording = state.recording_main || state.recording_mouse;
            egui::Window::new("设置")
                .anchor(Align2::CENTER_CENTER, vec2(0.0, 0.0))
                .collapsible(false)
                .order(egui::Order::Foreground)
                .resizable(false)
                .show(ctx, |ui| {
                    if let Some(error) = &state.error {
                        ui.label(RichText::new(error).color(DANGER));
                        ui.add_space(4.0);
                    }
                    egui::Grid::new("settings-grid")
                        .num_columns(2)
                        .spacing(vec2(12.0, 10.0))
                        .show(ui, |ui| {
                            ui.label("标题");
                            ui.add(
                                egui::TextEdit::singleline(&mut state.title).desired_width(220.0),
                            );
                            ui.end_row();

                            ui.label("呼出热键");
                            crate::ui::shortcut_edit::show(
                                ui,
                                &mut state.hotkey,
                                &mut state.recording_main,
                            );
                            ui.end_row();

                            ui.label("鼠标速度热键");
                            crate::ui::shortcut_edit::show(
                                ui,
                                &mut state.mouse_hotkey,
                                &mut state.recording_mouse,
                            );
                            ui.end_row();

                            ui.label("");
                            ui.checkbox(&mut state.autostart, "开机自启动");
                            ui.end_row();
                        });

                    ui.add_space(10.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button("取消").clicked() {
                            cancel = true;
                        }
                        if ui.button("确定").clicked() {
                            submit = true;
                        }
                    });
                });

            if !was_recording && ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
                cancel = true;
            }

            if cancel {
                keep = false;
                cancel_settings = true;
            } else if submit {
                match app.apply_settings(
                    state.title.clone(),
                    state.hotkey.clone(),
                    state.mouse_hotkey.clone(),
                    state.autostart,
                ) {
                    Ok(()) => keep = false,
                    Err(error) => state.error = Some(error),
                }
            }
        }
        Dialog::Input(state) => {
            let mut submit = false;
            let mut cancel = false;
            let window_title = state.title.clone();
            egui::Window::new(window_title)
                .anchor(Align2::CENTER_CENTER, vec2(0.0, 0.0))
                .collapsible(false)
                .order(egui::Order::Foreground)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label(&state.label);
                    let response =
                        ui.add(egui::TextEdit::singleline(&mut state.value).desired_width(240.0));
                    if !response.has_focus() {
                        response.request_focus();
                    }
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button("取消").clicked() {
                            cancel = true;
                        }
                        if ui.button("确定").clicked() {
                            submit = true;
                        }
                    });
                    if ui.input(|input| input.key_pressed(egui::Key::Enter)) {
                        submit = true;
                    }
                });

            if cancel || ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
                keep = false;
            } else if submit {
                match &state.purpose {
                    InputPurpose::AddCategory => app.add_category(state.value.clone()),
                    InputPurpose::RenameCategory(index) => {
                        app.rename_category(*index, state.value.clone())
                    }
                }
                keep = false;
            }
        }
        Dialog::Edit(state) => {
            let mut submit = false;
            let mut cancel = false;
            egui::Window::new("编辑")
                .anchor(Align2::CENTER_CENTER, vec2(0.0, 0.0))
                .collapsible(false)
                .order(egui::Order::Foreground)
                .resizable(false)
                .show(ctx, |ui| {
                    if let Some(error) = &state.error {
                        ui.label(RichText::new(error).color(DANGER));
                        ui.add_space(4.0);
                    }
                    egui::Grid::new("edit-grid")
                        .num_columns(2)
                        .spacing(vec2(12.0, 10.0))
                        .show(ui, |ui| {
                            ui.label("名称");
                            ui.add(
                                egui::TextEdit::singleline(&mut state.name).desired_width(260.0),
                            );
                            ui.end_row();

                            ui.label("路径");
                            ui.add(
                                egui::TextEdit::singleline(&mut state.path).desired_width(260.0),
                            );
                            ui.end_row();

                            ui.label("图标");
                            ui.horizontal(|ui| {
                                ui.add(
                                    egui::TextEdit::singleline(&mut state.icon)
                                        .desired_width(180.0)
                                        .hint_text("留空自动提取"),
                                );
                                if ui.button("浏览...").clicked()
                                    && let Some(path) = rfd::FileDialog::new()
                                        .add_filter(
                                            "图标文件",
                                            &["ico", "png", "jpg", "jpeg", "bmp", "exe", "dll"],
                                        )
                                        .pick_file()
                                {
                                    state.icon = path.to_string_lossy().to_string();
                                }
                                if ui.button("清空").clicked() {
                                    state.icon.clear();
                                }
                            });
                            ui.end_row();
                        });

                    ui.add_space(10.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button("取消").clicked() {
                            cancel = true;
                        }
                        if ui.button("确定").clicked() {
                            submit = true;
                        }
                    });
                });

            if cancel || ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
                keep = false;
            } else if submit {
                match app.apply_edit(
                    state.id,
                    state.name.clone(),
                    state.path.clone(),
                    state.icon.clone(),
                ) {
                    Ok(()) => keep = false,
                    Err(error) => state.error = Some(error),
                }
            }
        }
        Dialog::About => {
            let mut close = false;
            egui::Window::new("关于")
                .anchor(Align2::CENTER_CENTER, vec2(0.0, 0.0))
                .collapsible(false)
                .order(egui::Order::Foreground)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.vertical_centered(|ui| {
                        ui.label(
                            RichText::new("Run Launcher")
                                .size(20.0)
                                .strong()
                                .color(ACCENT),
                        );
                        ui.label(format!("版本 v{}", env!("CARGO_PKG_VERSION")));
                        ui.label(
                            RichText::new("Windows 快速启动器")
                                .color(TEXT_DIM)
                                .size(12.0),
                        );
                        ui.add_space(8.0);
                        if ui.button("GitHub").clicked() {
                            let _ = crate::launch::open_url(
                                "https://github.com/wangqiao258/run_launcher",
                            );
                        }
                        ui.add_space(6.0);
                        if ui.button("关闭").clicked() {
                            close = true;
                        }
                    });
                });
            if close || ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
                keep = false;
            }
        }
        Dialog::Message(message) => {
            let mut close = false;
            egui::Window::new("提示")
                .anchor(Align2::CENTER_CENTER, vec2(0.0, 0.0))
                .collapsible(false)
                .order(egui::Order::Foreground)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label(message.as_str());
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button("确定").clicked() {
                            close = true;
                        }
                    });
                });
            if close || ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
                keep = false;
            }
        }
        Dialog::None => keep = false,
    }

    if keep {
        app.dialog = dialog;
    } else if cancel_settings {
        app.cancel_settings();
    }
}

fn draw_overlay(ctx: &egui::Context) {
    egui::Area::new(egui::Id::unique("modal-overlay"))
        .order(egui::Order::Middle)
        .fixed_pos(egui::Pos2::ZERO)
        .show(ctx, |ui| {
            let rect = ctx.content_rect();
            ui.painter().rect_filled(
                rect,
                egui::CornerRadius::ZERO,
                Color32::from_black_alpha(150),
            );
            ui.allocate_rect(rect, Sense::click());
        });
}
