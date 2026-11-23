use global_hotkey::hotkey::{Code, HotKey, Modifiers};

pub fn parse(text: &str) -> Option<HotKey> {
    let mut mods = Modifiers::empty();
    let mut key = None;

    for raw in text.split('+') {
        let part = raw.trim();
        if part.is_empty() {
            continue;
        }
        match part.to_ascii_lowercase().as_str() {
            "ctrl" | "control" => mods |= Modifiers::CONTROL,
            "alt" => mods |= Modifiers::ALT,
            "shift" => mods |= Modifiers::SHIFT,
            "meta" | "win" | "super" => mods |= Modifiers::META,
            other => {
                if let Some(code) = code_from_name(other) {
                    key = Some(code);
                }
            }
        }
    }

    key.map(|code| HotKey::new(Some(mods), code))
}

pub fn format(hotkey: &HotKey) -> String {
    let mut parts = Vec::new();
    if hotkey.mods.contains(Modifiers::CONTROL) {
        parts.push("Ctrl".to_string());
    }
    if hotkey.mods.contains(Modifiers::ALT) {
        parts.push("Alt".to_string());
    }
    if hotkey.mods.contains(Modifiers::SHIFT) {
        parts.push("Shift".to_string());
    }
    if hotkey.mods.contains(Modifiers::META) {
        parts.push("Meta".to_string());
    }
    parts.push(code_name(hotkey.key).to_string());
    parts.join("+")
}

fn code_from_name(name: &str) -> Option<Code> {
    let lower = name.to_ascii_lowercase();
    let code = match lower.as_str() {
        "a" => Code::KeyA,
        "b" => Code::KeyB,
        "c" => Code::KeyC,
        "d" => Code::KeyD,
        "e" => Code::KeyE,
        "f" => Code::KeyF,
        "g" => Code::KeyG,
        "h" => Code::KeyH,
        "i" => Code::KeyI,
        "j" => Code::KeyJ,
        "k" => Code::KeyK,
        "l" => Code::KeyL,
        "m" => Code::KeyM,
        "n" => Code::KeyN,
        "o" => Code::KeyO,
        "p" => Code::KeyP,
        "q" => Code::KeyQ,
        "r" => Code::KeyR,
        "s" => Code::KeyS,
        "t" => Code::KeyT,
        "u" => Code::KeyU,
        "v" => Code::KeyV,
        "w" => Code::KeyW,
        "x" => Code::KeyX,
        "y" => Code::KeyY,
        "z" => Code::KeyZ,
        "0" => Code::Digit0,
        "1" => Code::Digit1,
        "2" => Code::Digit2,
        "3" => Code::Digit3,
        "4" => Code::Digit4,
        "5" => Code::Digit5,
        "6" => Code::Digit6,
        "7" => Code::Digit7,
        "8" => Code::Digit8,
        "9" => Code::Digit9,
        "space" => Code::Space,
        "esc" | "escape" => Code::Escape,
        "tab" => Code::Tab,
        "backspace" => Code::Backspace,
        "enter" | "return" => Code::Enter,
        "insert" | "ins" => Code::Insert,
        "delete" | "del" => Code::Delete,
        "home" => Code::Home,
        "end" => Code::End,
        "pageup" | "pgup" => Code::PageUp,
        "pagedown" | "pgdn" => Code::PageDown,
        "up" | "arrowup" => Code::ArrowUp,
        "down" | "arrowdown" => Code::ArrowDown,
        "left" | "arrowleft" => Code::ArrowLeft,
        "right" | "arrowright" => Code::ArrowRight,
        "minus" => Code::Minus,
        "equal" | "equals" => Code::Equal,
        "bracketleft" | "[" => Code::BracketLeft,
        "bracketright" | "]" => Code::BracketRight,
        "backslash" | "\\" => Code::Backslash,
        "semicolon" | ";" => Code::Semicolon,
        "quote" | "'" => Code::Quote,
        "backquote" | "`" => Code::Backquote,
        "comma" | "," => Code::Comma,
        "period" | "." => Code::Period,
        "slash" | "/" => Code::Slash,
        "f1" => Code::F1,
        "f2" => Code::F2,
        "f3" => Code::F3,
        "f4" => Code::F4,
        "f5" => Code::F5,
        "f6" => Code::F6,
        "f7" => Code::F7,
        "f8" => Code::F8,
        "f9" => Code::F9,
        "f10" => Code::F10,
        "f11" => Code::F11,
        "f12" => Code::F12,
        "f13" => Code::F13,
        "f14" => Code::F14,
        "f15" => Code::F15,
        "f16" => Code::F16,
        "f17" => Code::F17,
        "f18" => Code::F18,
        "f19" => Code::F19,
        "f20" => Code::F20,
        "f21" => Code::F21,
        "f22" => Code::F22,
        "f23" => Code::F23,
        "f24" => Code::F24,
        _ => return None,
    };
    Some(code)
}

pub fn code_name(code: Code) -> &'static str {
    match code {
        Code::KeyA => "A",
        Code::KeyB => "B",
        Code::KeyC => "C",
        Code::KeyD => "D",
        Code::KeyE => "E",
        Code::KeyF => "F",
        Code::KeyG => "G",
        Code::KeyH => "H",
        Code::KeyI => "I",
        Code::KeyJ => "J",
        Code::KeyK => "K",
        Code::KeyL => "L",
        Code::KeyM => "M",
        Code::KeyN => "N",
        Code::KeyO => "O",
        Code::KeyP => "P",
        Code::KeyQ => "Q",
        Code::KeyR => "R",
        Code::KeyS => "S",
        Code::KeyT => "T",
        Code::KeyU => "U",
        Code::KeyV => "V",
        Code::KeyW => "W",
        Code::KeyX => "X",
        Code::KeyY => "Y",
        Code::KeyZ => "Z",
        Code::Digit0 => "0",
        Code::Digit1 => "1",
        Code::Digit2 => "2",
        Code::Digit3 => "3",
        Code::Digit4 => "4",
        Code::Digit5 => "5",
        Code::Digit6 => "6",
        Code::Digit7 => "7",
        Code::Digit8 => "8",
        Code::Digit9 => "9",
        Code::Space => "Space",
        Code::Escape => "Esc",
        Code::Tab => "Tab",
        Code::Backspace => "Backspace",
        Code::Enter => "Enter",
        Code::Insert => "Insert",
        Code::Delete => "Delete",
        Code::Home => "Home",
        Code::End => "End",
        Code::PageUp => "PageUp",
        Code::PageDown => "PageDown",
        Code::ArrowUp => "Up",
        Code::ArrowDown => "Down",
        Code::ArrowLeft => "Left",
        Code::ArrowRight => "Right",
        Code::Minus => "Minus",
        Code::Equal => "Equal",
        Code::BracketLeft => "BracketLeft",
        Code::BracketRight => "BracketRight",
        Code::Backslash => "Backslash",
        Code::Semicolon => "Semicolon",
        Code::Quote => "Quote",
        Code::Backquote => "Backquote",
        Code::Comma => "Comma",
        Code::Period => "Period",
        Code::Slash => "Slash",
        Code::F1 => "F1",
        Code::F2 => "F2",
        Code::F3 => "F3",
        Code::F4 => "F4",
        Code::F5 => "F5",
        Code::F6 => "F6",
        Code::F7 => "F7",
        Code::F8 => "F8",
        Code::F9 => "F9",
        Code::F10 => "F10",
        Code::F11 => "F11",
        Code::F12 => "F12",
        Code::F13 => "F13",
        Code::F14 => "F14",
        Code::F15 => "F15",
        Code::F16 => "F16",
        Code::F17 => "F17",
        Code::F18 => "F18",
        Code::F19 => "F19",
        Code::F20 => "F20",
        Code::F21 => "F21",
        Code::F22 => "F22",
        Code::F23 => "F23",
        Code::F24 => "F24",
        _ => "Key",
    }
}

pub fn egui_key_to_code(key: egui::Key) -> Option<Code> {
    let code = match key {
        egui::Key::A => Code::KeyA,
        egui::Key::B => Code::KeyB,
        egui::Key::C => Code::KeyC,
        egui::Key::D => Code::KeyD,
        egui::Key::E => Code::KeyE,
        egui::Key::F => Code::KeyF,
        egui::Key::G => Code::KeyG,
        egui::Key::H => Code::KeyH,
        egui::Key::I => Code::KeyI,
        egui::Key::J => Code::KeyJ,
        egui::Key::K => Code::KeyK,
        egui::Key::L => Code::KeyL,
        egui::Key::M => Code::KeyM,
        egui::Key::N => Code::KeyN,
        egui::Key::O => Code::KeyO,
        egui::Key::P => Code::KeyP,
        egui::Key::Q => Code::KeyQ,
        egui::Key::R => Code::KeyR,
        egui::Key::S => Code::KeyS,
        egui::Key::T => Code::KeyT,
        egui::Key::U => Code::KeyU,
        egui::Key::V => Code::KeyV,
        egui::Key::W => Code::KeyW,
        egui::Key::X => Code::KeyX,
        egui::Key::Y => Code::KeyY,
        egui::Key::Z => Code::KeyZ,
        egui::Key::Num0 => Code::Digit0,
        egui::Key::Num1 => Code::Digit1,
        egui::Key::Num2 => Code::Digit2,
        egui::Key::Num3 => Code::Digit3,
        egui::Key::Num4 => Code::Digit4,
        egui::Key::Num5 => Code::Digit5,
        egui::Key::Num6 => Code::Digit6,
        egui::Key::Num7 => Code::Digit7,
        egui::Key::Num8 => Code::Digit8,
        egui::Key::Num9 => Code::Digit9,
        egui::Key::Space => Code::Space,
        egui::Key::Escape => Code::Escape,
        egui::Key::Tab => Code::Tab,
        egui::Key::Backspace => Code::Backspace,
        egui::Key::Enter => Code::Enter,
        egui::Key::Insert => Code::Insert,
        egui::Key::Delete => Code::Delete,
        egui::Key::Home => Code::Home,
        egui::Key::End => Code::End,
        egui::Key::PageUp => Code::PageUp,
        egui::Key::PageDown => Code::PageDown,
        egui::Key::ArrowUp => Code::ArrowUp,
        egui::Key::ArrowDown => Code::ArrowDown,
        egui::Key::ArrowLeft => Code::ArrowLeft,
        egui::Key::ArrowRight => Code::ArrowRight,
        egui::Key::Minus => Code::Minus,
        egui::Key::Equals => Code::Equal,
        egui::Key::OpenBracket => Code::BracketLeft,
        egui::Key::CloseBracket => Code::BracketRight,
        egui::Key::Backslash => Code::Backslash,
        egui::Key::Semicolon => Code::Semicolon,
        egui::Key::Quote => Code::Quote,
        egui::Key::Backtick => Code::Backquote,
        egui::Key::Comma => Code::Comma,
        egui::Key::Period => Code::Period,
        egui::Key::Slash => Code::Slash,
        egui::Key::F1 => Code::F1,
        egui::Key::F2 => Code::F2,
        egui::Key::F3 => Code::F3,
        egui::Key::F4 => Code::F4,
        egui::Key::F5 => Code::F5,
        egui::Key::F6 => Code::F6,
        egui::Key::F7 => Code::F7,
        egui::Key::F8 => Code::F8,
        egui::Key::F9 => Code::F9,
        egui::Key::F10 => Code::F10,
        egui::Key::F11 => Code::F11,
        egui::Key::F12 => Code::F12,
        egui::Key::F13 => Code::F13,
        egui::Key::F14 => Code::F14,
        egui::Key::F15 => Code::F15,
        egui::Key::F16 => Code::F16,
        egui::Key::F17 => Code::F17,
        egui::Key::F18 => Code::F18,
        egui::Key::F19 => Code::F19,
        egui::Key::F20 => Code::F20,
        egui::Key::F21 => Code::F21,
        egui::Key::F22 => Code::F22,
        egui::Key::F23 => Code::F23,
        egui::Key::F24 => Code::F24,
        _ => return None,
    };
    Some(code)
}

pub fn format_from_egui(modifiers: &egui::Modifiers, key: egui::Key) -> Option<String> {
    let code = egui_key_to_code(key)?;
    let mut mods = Modifiers::empty();
    if modifiers.ctrl {
        mods |= Modifiers::CONTROL;
    }
    if modifiers.alt {
        mods |= Modifiers::ALT;
    }
    if modifiers.shift {
        mods |= Modifiers::SHIFT;
    }
    if modifiers.mac_cmd {
        mods |= Modifiers::META;
    }
    Some(format(&HotKey::new(Some(mods), code)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips_default_hotkeys() {
        for text in ["Alt+Space", "Ctrl+Alt+M", "Ctrl+Shift+F5"] {
            let hotkey = parse(text).expect("parse");
            assert_eq!(format(&hotkey), text);
        }
    }

    #[test]
    fn rejects_unknown_keys() {
        assert!(parse("Ctrl+NotAKey").is_none());
    }
}
