use std::ffi::c_void;
use winreg::RegKey;
use winreg::enums::HKEY_CURRENT_USER;

use windows_sys::Win32::UI::WindowsAndMessaging::{
    SPI_GETMOUSESPEED, SPI_SETMOUSESPEED, SPIF_SENDCHANGE, SPIF_UPDATEINIFILE, SystemParametersInfoW,
};

pub fn get() -> u32 {
    let mut value: u32 = 0;
    let ok = unsafe {
        SystemParametersInfoW(
            SPI_GETMOUSESPEED,
            0,
            &mut value as *mut u32 as *mut c_void,
            0,
        )
    };
    if ok != 0 && value > 0 {
        return value.clamp(1, 20);
    }

    registry_speed().unwrap_or(10)
}

pub fn set(speed: u32) -> u32 {
    let speed = speed.clamp(1, 20);
    unsafe {
        SystemParametersInfoW(
            SPI_SETMOUSESPEED,
            0,
            speed as usize as *mut c_void,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        );
    }
    speed
}

pub fn next_speed(current: u32, presets: &[u32]) -> u32 {
    presets
        .iter()
        .copied()
        .filter(|preset| *preset > current)
        .min()
        .or_else(|| presets.first().copied())
        .unwrap_or(10)
}

pub fn speed_name(value: u32) -> &'static str {
    match value {
        5 => "慢",
        10 => "标准",
        15 => "快",
        20 => "极快",
        _ => "",
    }
}

fn registry_speed() -> Option<u32> {
    let key = RegKey::predef(HKEY_CURRENT_USER)
        .open_subkey(r"Control Panel\Mouse")
        .ok()?;
    let value: String = key.get_value("MouseSensitivity").ok()?;
    value.trim().parse::<u32>().ok().map(|v| v.clamp(1, 20))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cycles_presets() {
        let presets = [5, 10, 15, 20];
        assert_eq!(next_speed(10, &presets), 15);
        assert_eq!(next_speed(20, &presets), 5);
        assert_eq!(next_speed(3, &presets), 5);
    }
}
