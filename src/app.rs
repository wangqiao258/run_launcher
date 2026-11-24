use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Receiver, Sender};
use std::time::{Duration, Instant};

use eframe::egui;
use global_hotkey::GlobalHotKeyManager;
use global_hotkey::hotkey::HotKey;
use tray_icon::menu::{Menu, MenuItem, PredefinedMenuItem};
use tray_icon::{TrayIcon, TrayIconBuilder};
use windows_sys::Win32::Foundation::POINT;
use windows_sys::Win32::UI::WindowsAndMessaging::GetCursorPos;

use crate::events::{self, AppEvent};
use crate::hotkey;
use crate::icons::IconStore;
use crate::lnk_cache;
use crate::logging;
use crate::{config, launch, mouse_speed, paths, search, startup};

pub struct ItemDrag {
    pub ids: Vec<u64>,
}

pub struct TabDrag {
    pub from: usize,
}

pub struct SettingsState {
    pub title: String,
    pub hotkey: String,
    pub mouse_hotkey: String,
    pub autostart: bool,
    pub recording_main: bool,
    pub recording_mouse: bool,
    pub error: Option<String>,
}

pub struct EditState {
    pub id: u64,
    pub name: String,
    pub path: String,
    pub icon: String,
    pub error: Option<String>,
}

pub enum InputPurpose {
    AddCategory,
    RenameCategory(usize),
}

pub struct InputState {
    pub purpose: InputPurpose,
    pub title: String,
    pub label: String,
    pub value: String,
}

pub enum Dialog {
    None,
    Settings(SettingsState),
    Edit(EditState),
    Input(InputState),
    About,
    Message(String),
}

pub struct LauncherApp {
    pub config: config::Config,
    pub current_cat: usize,
    pub filter: String,
    pub selected: BTreeSet<u64>,
    pub icons: IconStore,
    pub dialog: Dialog,
    pub osd: crate::ui::osd::OsdState,
    pub visible: bool,
    pub focus_search: bool,
    pub search_id: Option<egui::Id>,
    pub last_window_rect: Option<egui::Rect>,
    pub select_anchor: Option<u64>,
    pub marquee_start: Option<egui::Pos2>,
    pub marquee_current: Option<egui::Pos2>,
    pub events_tx: Sender<AppEvent>,
    events_rx: Receiver<AppEvent>,
    pub hotkey_manager: Option<GlobalHotKeyManager>,
    pub main_hotkey: Option<HotKey>,
    pub mouse_hotkey: Option<HotKey>,
    pub tray: Option<TrayIcon>,
    dirty_since: Option<Instant>,
    quit: bool,
}

impl LauncherApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        crate::ui::theme::install(&cc.egui_ctx);
        logging::log("Launcher started");
        logging::log(&format!("config={}", paths::config_file().display()));

        let config = config::load();
        let (events_tx, events_rx) = mpsc::channel();
        events::spawn_wakers(events_tx.clone(), cc.egui_ctx.clone());

        let icons = IconStore::new(&cc.egui_ctx, events_tx.clone());
        let mut app = Self {
            current_cat: 0,
            filter: String::new(),
            selected: BTreeSet::new(),
            icons,
            dialog: Dialog::None,
            osd: crate::ui::osd::OsdState,
            visible: false,
            focus_search: false,
            search_id: None,
            last_window_rect: None,
            select_anchor: None,
            marquee_start: None,
            marquee_current: None,
            events_tx,
            events_rx,
            hotkey_manager: None,
            main_hotkey: None,
            mouse_hotkey: None,
            tray: None,
            dirty_since: None,
            quit: false,
            config,
        };

        app.setup_tray();
        app.register_current_hotkeys();
        let categories = app.config.categories.clone();
        app.icons.preload(&categories);
        cc.egui_ctx
            .send_viewport_cmd(egui::ViewportCommand::RequestPaintWhileHidden);
        cc.egui_ctx
            .send_viewport_cmd(egui::ViewportCommand::Visible(false));
        app
    }

    fn tray_tooltip(&self) -> String {
        format!(
            "{} ({})",
            self.config.general.title, self.config.general.hotkey
        )
    }

    fn setup_tray(&mut self) {
        let Some(icon) = make_tray_icon() else {
            logging::log("tray icon generation failed");
            return;
        };
        let menu = Menu::new();
        let _ = menu.append(&MenuItem::with_id("toggle", "显示/隐藏", true, None));
        let _ = menu.append(&PredefinedMenuItem::separator());
        let _ = menu.append(&MenuItem::with_id("settings", "设置", true, None));
        let _ = menu.append(&MenuItem::with_id("about", "关于", true, None));
        let _ = menu.append(&PredefinedMenuItem::separator());
        let _ = menu.append(&MenuItem::with_id("quit", "退出", true, None));

        match TrayIconBuilder::new()
            .with_icon(icon)
            .with_tooltip(self.tray_tooltip())
            .with_menu(Box::new(menu))
            .build()
        {
            Ok(tray) => self.tray = Some(tray),
            Err(err) => logging::log(&format!("tray create failed: {err}")),
        }
    }

    fn update_tray_tooltip(&self) {
        if let Some(tray) = &self.tray {
            let _ = tray.set_tooltip(Some(self.tray_tooltip()));
        }
    }

    fn ensure_manager(&mut self) -> bool {
        if self.hotkey_manager.is_none() {
            match GlobalHotKeyManager::new() {
                Ok(manager) => self.hotkey_manager = Some(manager),
                Err(err) => {
                    logging::log(&format!("hotkey manager failed: {err}"));
                    return false;
                }
            }
        }
        true
    }

    fn register_current_hotkeys(&mut self) {
        if !self.ensure_manager() {
            return;
        }
        let main = hotkey::parse(&self.config.general.hotkey);
        let mouse = hotkey::parse(&self.config.general.mouse_speed_hotkey);
        let mut main_error = None;
        let mut mouse_error = None;
        let (main_ok, mouse_ok) = if let Some(manager) = &self.hotkey_manager {
            let main_ok = match main {
                Some(value) => match manager.register(value) {
                    Ok(()) => true,
                    Err(err) => {
                        main_error = Some(err.to_string());
                        false
                    }
                },
                None => false,
            };
            let different = mouse.map(|value| value.id) != main.map(|value| value.id);
            let mouse_ok = if different {
                match mouse {
                    Some(value) => match manager.register(value) {
                        Ok(()) => true,
                        Err(err) => {
                            mouse_error = Some(err.to_string());
                            false
                        }
                    },
                    None => false,
                }
            } else {
                false
            };
            (main_ok, mouse_ok)
        } else {
            (false, false)
        };

        if main_ok {
            self.main_hotkey = main;
        }
        if mouse_ok {
            self.mouse_hotkey = mouse;
        }
        if let Some(err) = main_error {
            logging::log(&format!("main hotkey registration failed: {err}"));
        }
        if let Some(err) = mouse_error {
            logging::log(&format!("mouse hotkey registration failed: {err}"));
        }
        logging::log(&format!(
            "hotkeys registered: main={main_ok}, mouse={mouse_ok}"
        ));
    }

    fn unregister_hotkeys(&mut self) {
        let main = self.main_hotkey.take();
        let mouse = self.mouse_hotkey.take();
        if let Some(manager) = &self.hotkey_manager {
            if let Some(main) = main {
                let _ = manager.unregister(main);
            }
            if let Some(mouse) = mouse {
                let _ = manager.unregister(mouse);
            }
        }
    }

    fn toggle(&mut self, ctx: &egui::Context) {
        if self.visible {
            self.hide(ctx);
        } else {
            self.show(ctx);
        }
    }

    fn show(&mut self, ctx: &egui::Context) {
        let width = self.config.window.width;
        let position = match (self.config.window.x, self.config.window.y) {
            (Some(x), Some(y)) => Some(egui::pos2(x as f32, y as f32)),
            _ => cursor_logical(ctx).map(|pos| egui::pos2(pos.x - width / 2.0, pos.y - 20.0)),
        };
        if let Some(position) = position {
            ctx.send_viewport_cmd(egui::ViewportCommand::OuterPosition(position));
        }
        ctx.send_viewport_cmd(egui::ViewportCommand::Visible(true));
        ctx.send_viewport_cmd(egui::ViewportCommand::Focus);
        self.visible = true;
        self.focus_search = true;
        self.icons.clear_failures();
        ctx.request_repaint();
    }

    fn hide(&mut self, ctx: &egui::Context) {
        self.capture_window_state(ctx);
        if matches!(self.dialog, Dialog::Settings(_)) {
            self.reopen_hotkeys();
        }
        self.dialog = Dialog::None;
        self.visible = false;
        ctx.send_viewport_cmd(egui::ViewportCommand::Visible(false));
        self.save_config_now();
    }

    fn capture_window_state(&mut self, ctx: &egui::Context) {
        if let Some(rect) = ctx.input(|input| input.viewport().outer_rect) {
            self.last_window_rect = Some(rect);
        }
        if let Some(rect) = self.last_window_rect {
            let x = rect.min.x.round() as i32;
            let y = rect.min.y.round() as i32;
            let width = rect.width().max(config::MIN_WINDOW);
            let height = rect.height().max(config::MIN_HEIGHT);
            if self.config.window.x != Some(x)
                || self.config.window.y != Some(y)
                || (self.config.window.width - width).abs() > 0.5
                || (self.config.window.height - height).abs() > 0.5
            {
                self.config.window.x = Some(x);
                self.config.window.y = Some(y);
                self.config.window.width = width;
                self.config.window.height = height;
                self.mark_dirty();
            }
        }
    }

    fn mark_dirty(&mut self) {
        if self.dirty_since.is_none() {
            self.dirty_since = Some(Instant::now());
        }
    }

    fn autosave(&mut self) {
        if let Some(since) = self.dirty_since
            && since.elapsed() >= Duration::from_millis(250)
        {
            self.dirty_since = None;
            self.save_config_now();
        }
    }

    pub fn save_config_now(&mut self) {
        if let Err(err) = config::save(&self.config) {
            logging::log(&format!("save config failed: {err}"));
        }
        self.dirty_since = None;
    }

    fn shutdown(&mut self, ctx: &egui::Context) {
        self.quit = true;
        self.capture_window_state(ctx);
        self.save_config_now();
        self.icons.shutdown();
        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
    }

    fn quit(&mut self, ctx: &egui::Context) {
        self.shutdown(ctx);
    }

    fn drain_events(&mut self, ctx: &egui::Context) {
        while let Ok(event) = self.events_rx.try_recv() {
            match event {
                AppEvent::Hotkey(id) => {
                    if Some(id) == self.main_hotkey.map(|hotkey| hotkey.id) {
                        self.toggle(ctx);
                    } else if Some(id) == self.mouse_hotkey.map(|hotkey| hotkey.id) {
                        self.cycle_mouse_speed(ctx);
                    }
                }
                AppEvent::TrayDoubleClick => self.toggle(ctx),
                AppEvent::Menu(id) => match id.as_str() {
                    "toggle" => self.toggle(ctx),
                    "settings" => {
                        if !self.visible {
                            self.show(ctx);
                        }
                        self.open_settings();
                    }
                    "about" => {
                        if !self.visible {
                            self.show(ctx);
                        }
                        self.dialog = Dialog::About;
                    }
                    "quit" => self.quit(ctx),
                    _ => {}
                },
                AppEvent::IconReady(ready) => {
                    self.icons.on_ready(ctx, ready);
                    ctx.request_repaint();
                }
                AppEvent::IconFailed(key) => self.icons.on_failed(key),
                AppEvent::Error(message) => {
                    if !self.visible {
                        self.show(ctx);
                    }
                    self.dialog = Dialog::Message(message);
                }
            }
        }
    }

    fn cycle_mouse_speed(&mut self, ctx: &egui::Context) {
        let presets = &self.config.general.mouse_speed_presets;
        let current = mouse_speed::get();
        let target = mouse_speed::next_speed(current, presets);
        mouse_speed::set(target);
        let name = mouse_speed::speed_name(target);
        let text = if name.is_empty() {
            format!("鼠标速度  {target}/20")
        } else {
            format!("鼠标速度  {name}  {target}/20")
        };
        logging::log(&format!("mouse speed: {current} -> {target}"));
        self.osd.popup(text);
        ctx.request_repaint();
    }

    pub fn open_settings(&mut self) {
        self.unregister_hotkeys();
        self.dialog = Dialog::Settings(SettingsState {
            title: self.config.general.title.clone(),
            hotkey: self.config.general.hotkey.clone(),
            mouse_hotkey: self.config.general.mouse_speed_hotkey.clone(),
            autostart: startup::is_enabled(),
            recording_main: false,
            recording_mouse: false,
            error: None,
        });
    }

    pub fn cancel_settings(&mut self) {
        self.dialog = Dialog::None;
        self.reopen_hotkeys();
    }

    fn reopen_hotkeys(&mut self) {
        if !self.ensure_manager() {
            return;
        }
        let main = hotkey::parse(&self.config.general.hotkey);
        let mouse = hotkey::parse(&self.config.general.mouse_speed_hotkey);
        let (main_ok, mouse_ok) = if let Some(manager) = &self.hotkey_manager {
            let main_ok = main
                .map(|value| manager.register(value).is_ok())
                .unwrap_or(false);
            let different = mouse.map(|value| value.id) != main.map(|value| value.id);
            let mouse_ok = different
                && mouse
                    .map(|value| manager.register(value).is_ok())
                    .unwrap_or(false);
            (main_ok, mouse_ok)
        } else {
            (false, false)
        };
        if main_ok {
            self.main_hotkey = main;
        }
        if mouse_ok {
            self.mouse_hotkey = mouse;
        }
    }

    pub fn apply_settings(
        &mut self,
        title: String,
        hotkey_text: String,
        mouse_hotkey_text: String,
        autostart: bool,
    ) -> Result<(), String> {
        let Some(main) = hotkey::parse(&hotkey_text) else {
            return Err("呼出热键格式无效".to_string());
        };
        let Some(mouse) = hotkey::parse(&mouse_hotkey_text) else {
            return Err("鼠标速度热键格式无效".to_string());
        };
        if main.id == mouse.id {
            return Err("两个热键不能相同".to_string());
        }

        if !self.ensure_manager() {
            return Err("无法初始化全局热键".to_string());
        }

        self.unregister_hotkeys();
        let register_mouse = if let Some(manager) = &self.hotkey_manager {
            manager
                .register(main)
                .map_err(|err| format!("注册呼出热键失败: {err}"))?;
            manager.register(mouse)
        } else {
            return Err("无法初始化全局热键".to_string());
        };
        if let Err(err) = register_mouse {
            if let Some(manager) = &self.hotkey_manager {
                let _ = manager.unregister(main);
                if let Some(old) = hotkey::parse(&self.config.general.hotkey) {
                    let _ = manager.register(old);
                }
            }
            return Err(format!("注册鼠标速度热键失败: {err}"));
        }
        self.main_hotkey = Some(main);
        self.mouse_hotkey = Some(mouse);

        self.config.general.title = title.trim().to_string();
        self.config.general.hotkey = hotkey::format(&main);
        self.config.general.mouse_speed_hotkey = hotkey::format(&mouse);

        if let Err(err) = startup::set_enabled(autostart) {
            logging::log(&format!("autostart failed: {err}"));
        }
        self.mark_dirty();
        self.save_config_now();
        self.update_tray_tooltip();
        self.dialog = Dialog::None;
        Ok(())
    }

    pub fn visible_items(&self) -> Vec<(usize, usize)> {
        let mut items = Vec::new();
        if self.filter.trim().is_empty() {
            if let Some(category) = self.config.categories.get(self.current_cat) {
                for index in 0..category.items.len() {
                    items.push((self.current_cat, index));
                }
            }
        } else {
            let query = self.filter.trim().to_lowercase();
            for (cat_index, category) in self.config.categories.iter().enumerate() {
                for (item_index, item) in category.items.iter().enumerate() {
                    if search::matches(item, &query) {
                        items.push((cat_index, item_index));
                    }
                }
            }
        }
        items
    }

    pub fn item_by_id(&self, id: u64) -> Option<&config::Item> {
        self.config
            .categories
            .iter()
            .flat_map(|category| category.items.iter())
            .find(|item| item.id == id)
    }

    pub fn item_clone(&self, id: u64) -> Option<config::Item> {
        self.item_by_id(id).cloned()
    }

    pub fn selected_ids(&self) -> Vec<u64> {
        self.selected.iter().copied().collect()
    }

    pub fn select_clicked(&mut self, id: u64, ctrl: bool, shift: bool) {
        if ctrl {
            if !self.selected.remove(&id) {
                self.selected.insert(id);
            }
            self.select_anchor = Some(id);
            return;
        }
        if shift && let Some(anchor) = self.select_anchor {
            let visible: Vec<u64> = self
                .visible_items()
                .into_iter()
                .filter_map(|(cat, idx)| {
                    self.config
                        .categories
                        .get(cat)
                        .and_then(|category| category.items.get(idx))
                        .map(|item| item.id)
                })
                .collect();
            if let (Some(a), Some(b)) = (
                visible.iter().position(|value| *value == anchor),
                visible.iter().position(|value| *value == id),
            ) {
                let (start, end) = if a <= b { (a, b) } else { (b, a) };
                self.selected.clear();
                for selected in &visible[start..=end] {
                    self.selected.insert(*selected);
                }
                return;
            }
        }
        self.selected.clear();
        self.selected.insert(id);
        self.select_anchor = Some(id);
    }

    pub fn refresh(&mut self) {
        self.icons.clear_failures();
    }

    pub fn add_paths(&mut self, paths: Vec<PathBuf>) {
        let mut next_id = self.config.next_id();
        let Some(category) = self.config.categories.get_mut(self.current_cat) else {
            return;
        };
        for path in paths {
            if !path.exists() {
                continue;
            }
            let name = path
                .file_stem()
                .or_else(|| path.file_name())
                .map(|value| value.to_string_lossy().to_string())
                .unwrap_or_else(|| path.to_string_lossy().to_string());
            category.items.push(config::Item::new(
                next_id,
                name,
                path.to_string_lossy().to_string(),
                None,
            ));
            next_id += 1;
        }
        self.mark_dirty();
        self.refresh();
    }

    pub fn launch_item(&mut self, ctx: &egui::Context, id: u64, admin: bool) {
        let Some(item) = self.item_clone(id) else {
            return;
        };
        let mut target = PathBuf::from(&item.path);
        if !target.exists()
            && item.path.to_lowercase().ends_with(".lnk")
            && let Some(resolved) = lnk_cache::resolve(&target)
        {
            target = resolved;
        }
        if !target.exists() {
            self.dialog = Dialog::Message(format!(
                "找不到目标，可能已卸载或被移动：\n{}\n\n解析路径：{}",
                item.path,
                target.display()
            ));
            return;
        }

        self.hide(ctx);
        let tx = self.events_tx.clone();
        std::thread::spawn(move || {
            if let Err(err) = launch::launch(&target, admin) {
                let _ = tx.send(AppEvent::Error(format!("启动失败: {err}")));
            }
        });
    }

    pub fn open_item_path(&mut self, id: u64) {
        let Some(item) = self.item_by_id(id) else {
            return;
        };
        if let Err(err) = launch::open_folder(Path::new(&item.path)) {
            self.dialog = Dialog::Message(err);
        }
    }

    pub fn edit_item(&mut self, id: u64) {
        let Some(item) = self.item_by_id(id) else {
            return;
        };
        self.dialog = Dialog::Edit(EditState {
            id,
            name: item.name.clone(),
            path: item.path.clone(),
            icon: item.icon.clone().unwrap_or_default(),
            error: None,
        });
    }

    pub fn apply_edit(
        &mut self,
        id: u64,
        name: String,
        path: String,
        icon: String,
    ) -> Result<(), String> {
        if name.trim().is_empty() {
            return Err("名称不能为空".to_string());
        }
        let path_buf = PathBuf::from(path.trim());
        if !path_buf.exists() {
            return Err("路径不存在".to_string());
        }
        let icon = icon.trim();
        let icon_value = if icon.is_empty() {
            None
        } else if Path::new(icon).exists() {
            Some(icon.to_string())
        } else {
            return Err("图标文件不存在".to_string());
        };

        let Some(item) = self
            .config
            .categories
            .iter_mut()
            .flat_map(|category| category.items.iter_mut())
            .find(|item| item.id == id)
        else {
            return Err("条目不存在".to_string());
        };
        item.name = name.trim().to_string();
        item.path = path_buf.to_string_lossy().to_string();
        item.icon = icon_value;
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
        Ok(())
    }

    pub fn remove_item(&mut self, id: u64) {
        for category in &mut self.config.categories {
            category.items.retain(|item| item.id != id);
        }
        self.selected.remove(&id);
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
    }

    pub fn delete_selected(&mut self) {
        if self.selected.is_empty() {
            return;
        }
        let selected = self.selected.clone();
        for category in &mut self.config.categories {
            category.items.retain(|item| !selected.contains(&item.id));
        }
        self.selected.clear();
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
    }

    pub fn set_category(&mut self, index: usize) {
        if index < self.config.categories.len() {
            self.current_cat = index;
            self.refresh();
        }
    }

    pub fn add_category(&mut self, name: String) {
        if name.trim().is_empty() {
            return;
        }
        self.config.categories.push(config::Category {
            name: name.trim().to_string(),
            items: Vec::new(),
        });
        self.current_cat = self.config.categories.len() - 1;
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
    }

    pub fn rename_category(&mut self, index: usize, name: String) {
        if name.trim().is_empty() {
            return;
        }
        if let Some(category) = self.config.categories.get_mut(index) {
            category.name = name.trim().to_string();
            self.mark_dirty();
            self.save_config_now();
        }
    }

    pub fn delete_category(&mut self, index: usize) {
        if self.config.categories.len() <= 1 || index >= self.config.categories.len() {
            return;
        }
        self.config.categories.remove(index);
        if self.current_cat >= self.config.categories.len() {
            self.current_cat = self.config.categories.len() - 1;
        }
        self.selected.clear();
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
    }

    pub fn reorder_category(&mut self, from: usize, to: usize) {
        if from >= self.config.categories.len() || to >= self.config.categories.len() || from == to
        {
            return;
        }
        let category = self.config.categories.remove(from);
        self.config.categories.insert(to, category);
        self.current_cat = to;
        self.mark_dirty();
        self.save_config_now();
    }

    pub fn move_items(&mut self, ids: Vec<u64>, destination: usize) {
        if ids.is_empty() || destination >= self.config.categories.len() {
            return;
        }
        let selected: BTreeSet<u64> = ids.into_iter().collect();
        let mut moved = Vec::new();
        for category in &mut self.config.categories {
            let mut index = 0;
            while index < category.items.len() {
                if selected.contains(&category.items[index].id) {
                    moved.push(category.items.remove(index));
                } else {
                    index += 1;
                }
            }
        }
        if moved.is_empty() {
            return;
        }
        if let Some(category) = self.config.categories.get_mut(destination) {
            category.items.extend(moved);
        }
        self.mark_dirty();
        self.save_config_now();
        self.refresh();
    }

    pub fn visible_count(&self) -> usize {
        self.visible_items().len()
    }

    fn draw(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        let dropped: Vec<PathBuf> = ui.ctx().input(|input| {
            input
                .raw
                .dropped_files
                .iter()
                .map(|file| file.path().to_path_buf())
                .collect()
        });
        if !dropped.is_empty() {
            self.add_paths(dropped);
        }

        let rect = ui.max_rect();
        ui.painter().rect_filled(
            rect,
            egui::CornerRadius::same(12),
            crate::ui::theme::background(),
        );
        self.handle_window_edges(&ctx, rect);

        let content = rect.shrink2(egui::vec2(14.0, 10.0));
        ui.scope_builder(egui::UiBuilder::new().max_rect(content), |ui| {
            ui.set_min_size(content.size());
            self.draw_content(ui);
        });

        crate::ui::dialogs::show(self, &ctx);
    }

    fn draw_content(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        let title = self.config.general.title.clone();

        ui.horizontal(|ui| {
            let width = (ui.available_width() - 32.0).max(0.0);
            let (rect, response) =
                ui.allocate_exact_size(egui::vec2(width, 36.0), egui::Sense::drag());
            ui.painter().text(
                rect.left_center() + egui::vec2(2.0, 0.0),
                egui::Align2::LEFT_CENTER,
                title,
                egui::FontId::proportional(15.0),
                crate::ui::theme::TEXT,
            );
            if response.drag_started() {
                ctx.send_viewport_cmd(egui::ViewportCommand::StartDrag);
            }
            if crate::ui::widgets::close_button(ui) {
                self.hide(&ctx);
            }
        });

        ui.add_space(2.0);
        let search = egui::TextEdit::singleline(&mut self.filter)
            .hint_text("搜索应用、文件或拼音…")
            .desired_width(f32::INFINITY);
        let response = ui.add_sized([ui.available_width(), 40.0], search);
        self.search_id = Some(response.id);
        if self.focus_search {
            response.request_focus();
            self.focus_search = false;
        }
        if response.changed() {
            self.selected.clear();
            self.icons.clear_failures();
        }

        ui.add_space(4.0);
        if let Some(action) = crate::ui::tabs::show(self, ui) {
            match action {
                crate::ui::tabs::TabAction::Select(index) => self.set_category(index),
                crate::ui::tabs::TabAction::Add => {
                    self.dialog = Dialog::Input(InputState {
                        purpose: InputPurpose::AddCategory,
                        title: "添加分类".to_string(),
                        label: "分类名称:".to_string(),
                        value: String::new(),
                    });
                }
                crate::ui::tabs::TabAction::Rename(index) => {
                    let value = self
                        .config
                        .categories
                        .get(index)
                        .map(|category| category.name.clone())
                        .unwrap_or_default();
                    self.dialog = Dialog::Input(InputState {
                        purpose: InputPurpose::RenameCategory(index),
                        title: "重命名分类".to_string(),
                        label: "新名称:".to_string(),
                        value,
                    });
                }
                crate::ui::tabs::TabAction::Delete(index) => self.delete_category(index),
                crate::ui::tabs::TabAction::MoveItems { ids, destination } => {
                    self.move_items(ids, destination)
                }
                crate::ui::tabs::TabAction::Reorder { from, to } => self.reorder_category(from, to),
            }
        }

        ui.add_space(4.0);
        let footer_height = 26.0;
        let grid_height = (ui.available_height() - footer_height).max(80.0);
        crate::ui::grid::show(self, ui, grid_height);
        self.draw_footer(ui);
    }

    fn draw_footer(&mut self, ui: &mut egui::Ui) {
        ui.add_space(2.0);
        ui.horizontal(|ui| {
            crate::ui::widgets::muted(ui, &format!("{} 个项目", self.visible_count()));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                crate::ui::widgets::muted(ui, &self.config.general.hotkey);
            });
        });
    }

    fn handle_window_edges(&self, ctx: &egui::Context, rect: egui::Rect) {
        if !matches!(self.dialog, Dialog::None) {
            return;
        }
        let Some(pos) = ctx.input(|input| input.pointer.hover_pos()) else {
            return;
        };
        if !rect.contains(pos) {
            return;
        }
        let content = rect.shrink2(egui::vec2(14.0, 10.0));
        if content.contains(pos) {
            return;
        }

        let edge = edge_at(rect, pos);
        let Some(edge) = edge else {
            return;
        };

        if ctx.input(|input| input.pointer.primary_pressed()) {
            ctx.send_viewport_cmd(egui::ViewportCommand::BeginResize(edge_direction(edge)));
            return;
        }
        ctx.set_cursor_icon(edge_cursor(edge));
    }
}

impl eframe::App for LauncherApp {
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.drain_events(ctx);
        if self.quit {
            return;
        }
        if self.visible {
            self.capture_window_state(ctx);
        }
        self.autosave();
        if !self.visible {
            ctx.request_repaint_after(Duration::from_millis(500));
        }
    }

    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        if !self.visible {
            return;
        }
        self.draw(ui);
    }

    fn clear_color(&self, _visuals: &egui::Visuals) -> [f32; 4] {
        [0.0, 0.0, 0.0, 0.0]
    }
}

impl Drop for LauncherApp {
    fn drop(&mut self) {
        self.save_config_now();
        self.icons.shutdown();
    }
}

#[derive(Clone, Copy)]
enum Edge {
    Left,
    Right,
    Top,
    Bottom,
    TopLeft,
    TopRight,
    BottomLeft,
    BottomRight,
}

fn edge_at(rect: egui::Rect, pos: egui::Pos2) -> Option<Edge> {
    let margin = 10.0;
    let corner = 16.0;
    let left = pos.x < rect.left() + corner;
    let right = pos.x > rect.right() - corner;
    let top = pos.y < rect.top() + corner;
    let bottom = pos.y > rect.bottom() - corner;
    if top && left {
        return Some(Edge::TopLeft);
    }
    if top && right {
        return Some(Edge::TopRight);
    }
    if bottom && left {
        return Some(Edge::BottomLeft);
    }
    if bottom && right {
        return Some(Edge::BottomRight);
    }
    if pos.x < rect.left() + margin {
        return Some(Edge::Left);
    }
    if pos.x > rect.right() - margin {
        return Some(Edge::Right);
    }
    if pos.y < rect.top() + margin {
        return Some(Edge::Top);
    }
    if pos.y > rect.bottom() - margin {
        return Some(Edge::Bottom);
    }
    None
}

fn edge_direction(edge: Edge) -> egui::ResizeDirection {
    match edge {
        Edge::Left => egui::ResizeDirection::West,
        Edge::Right => egui::ResizeDirection::East,
        Edge::Top => egui::ResizeDirection::North,
        Edge::Bottom => egui::ResizeDirection::South,
        Edge::TopLeft => egui::ResizeDirection::NorthWest,
        Edge::TopRight => egui::ResizeDirection::NorthEast,
        Edge::BottomLeft => egui::ResizeDirection::SouthWest,
        Edge::BottomRight => egui::ResizeDirection::SouthEast,
    }
}

fn edge_cursor(edge: Edge) -> egui::CursorIcon {
    match edge {
        Edge::Left | Edge::Right => egui::CursorIcon::ResizeHorizontal,
        Edge::Top | Edge::Bottom => egui::CursorIcon::ResizeVertical,
        Edge::TopLeft | Edge::BottomRight => egui::CursorIcon::ResizeNwSe,
        Edge::TopRight | Edge::BottomLeft => egui::CursorIcon::ResizeNeSw,
    }
}

fn cursor_logical(ctx: &egui::Context) -> Option<egui::Pos2> {
    let mut point = POINT { x: 0, y: 0 };
    if unsafe { GetCursorPos(&mut point) } == 0 {
        return None;
    }
    let scale = ctx.pixels_per_point().max(1.0);
    Some(egui::pos2(point.x as f32 / scale, point.y as f32 / scale))
}

fn make_tray_icon() -> Option<tray_icon::Icon> {
    let size = 32u32;
    let mut rgba = vec![0u8; (size * size * 4) as usize];
    for y in 0..size {
        for x in 0..size {
            let dx = x.min(size - 1 - x) as i32;
            let dy = y.min(size - 1 - y) as i32;
            let inside = if dx < 6 && dy < 6 {
                let nx = 6 - dx;
                let ny = 6 - dy;
                nx * nx + ny * ny <= 36
            } else {
                true
            };
            if inside {
                let index = ((y * size + x) * 4) as usize;
                rgba[index] = 74;
                rgba[index + 1] = 158;
                rgba[index + 2] = 255;
                rgba[index + 3] = 255;
            }
        }
    }
    tray_icon::Icon::from_rgba(rgba, size, size).ok()
}
