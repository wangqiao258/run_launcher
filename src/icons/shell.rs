use std::ffi::c_void;
use std::path::Path;
use std::ptr;
use std::time::Duration;

use windows_sys::Win32::Graphics::Gdi::{
    BI_RGB, BITMAP, BITMAPINFO, BITMAPINFOHEADER, DIB_RGB_COLORS, DeleteObject, GetDC, GetDIBits,
    GetObjectW, HBITMAP, ReleaseDC,
};
use windows_sys::Win32::UI::Shell::{
    ExtractIconExW, SHFILEINFOW, SHGFI_ICON, SHGFI_LARGEICON, SHGetFileInfoW,
};
use windows_sys::Win32::UI::WindowsAndMessaging::{DestroyIcon, GetIconInfo, HICON, ICONINFO};

#[derive(Clone)]
pub struct RgbaIcon {
    pub width: u32,
    pub height: u32,
    pub pixels: Vec<u8>,
}

pub fn extract_from_path(path: &Path) -> Option<RgbaIcon> {
    let hicon = extract_hicon(path)?;
    let result = hicon_to_rgba(hicon);
    unsafe {
        DestroyIcon(hicon);
    }
    result
}

pub fn extract_shell_icon(path: &Path) -> Option<RgbaIcon> {
    let wide = wide(path);
    let mut info: SHFILEINFOW = unsafe { std::mem::zeroed() };
    let result = unsafe {
        SHGetFileInfoW(
            wide.as_ptr(),
            0,
            &mut info,
            std::mem::size_of::<SHFILEINFOW>() as u32,
            SHGFI_ICON | SHGFI_LARGEICON,
        )
    };
    if result == 0 || info.hIcon.is_null() {
        return None;
    }
    let icon = hicon_to_rgba(info.hIcon);
    unsafe {
        DestroyIcon(info.hIcon);
    }
    icon
}

fn extract_hicon(path: &Path) -> Option<HICON> {
    let wide = wide(path);
    for attempt in 0..3 {
        let mut large: HICON = ptr::null_mut();
        let mut small: HICON = ptr::null_mut();
        let count = unsafe { ExtractIconExW(wide.as_ptr(), 0, &mut large, &mut small, 1) };
        if count > 0 {
            let chosen = if !large.is_null() { large } else { small };
            let unused = if !large.is_null() { small } else { large };
            if !unused.is_null() {
                unsafe {
                    DestroyIcon(unused);
                }
            }
            if !chosen.is_null() {
                return Some(chosen);
            }
        }
        if attempt < 2 {
            std::thread::sleep(Duration::from_millis(20));
        }
    }
    None
}

fn hicon_to_rgba(hicon: HICON) -> Option<RgbaIcon> {
    let mut info: ICONINFO = unsafe { std::mem::zeroed() };
    if unsafe { GetIconInfo(hicon, &mut info) } == 0 {
        return None;
    }

    let result = color_bitmap_to_rgba(info.hbmColor, info.hbmMask);

    if !info.hbmColor.is_null() {
        unsafe {
            DeleteObject(info.hbmColor);
        }
    }
    if !info.hbmMask.is_null() {
        unsafe {
            DeleteObject(info.hbmMask);
        }
    }
    result
}

fn color_bitmap_to_rgba(color: HBITMAP, mask: HBITMAP) -> Option<RgbaIcon> {
    if color.is_null() {
        return None;
    }

    let mut bitmap: BITMAP = unsafe { std::mem::zeroed() };
    let got = unsafe {
        GetObjectW(
            color,
            std::mem::size_of::<BITMAP>() as i32,
            &mut bitmap as *mut BITMAP as *mut c_void,
        )
    };
    if got == 0 || bitmap.bmWidth <= 0 || bitmap.bmHeight <= 0 {
        return None;
    }

    let width = bitmap.bmWidth as u32;
    let height = bitmap.bmHeight as u32;
    if width > 512 || height > 512 {
        return None;
    }

    let mut bmi: BITMAPINFO = unsafe { std::mem::zeroed() };
    bmi.bmiHeader.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
    bmi.bmiHeader.biWidth = width as i32;
    bmi.bmiHeader.biHeight = -(height as i32);
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    let mut pixels = vec![0u8; (width * height * 4) as usize];
    let hdc = unsafe { GetDC(ptr::null_mut()) };
    if hdc.is_null() {
        return None;
    }
    let lines = unsafe {
        GetDIBits(
            hdc,
            color,
            0,
            height,
            pixels.as_mut_ptr() as *mut c_void,
            &mut bmi,
            DIB_RGB_COLORS,
        )
    };
    unsafe {
        ReleaseDC(ptr::null_mut(), hdc);
    }
    if lines == 0 {
        return None;
    }

    for pixel in pixels.as_chunks_mut::<4>().0 {
        pixel.swap(0, 2);
    }

    let all_transparent = pixels.as_chunks::<4>().0.iter().all(|pixel| pixel[3] == 0);
    if all_transparent && !apply_mask_alpha(mask, width, height, &mut pixels) {
        for pixel in pixels.as_chunks_mut::<4>().0 {
            pixel[3] = 255;
        }
    }

    Some(RgbaIcon {
        width,
        height,
        pixels,
    })
}

fn apply_mask_alpha(mask: HBITMAP, width: u32, height: u32, pixels: &mut [u8]) -> bool {
    if mask.is_null() {
        return false;
    }

    let mut bitmap: BITMAP = unsafe { std::mem::zeroed() };
    let got = unsafe {
        GetObjectW(
            mask,
            std::mem::size_of::<BITMAP>() as i32,
            &mut bitmap as *mut BITMAP as *mut c_void,
        )
    };
    if got == 0 || bitmap.bmWidth <= 0 || bitmap.bmHeight <= 0 {
        return false;
    }

    let stride = width.div_ceil(32) * 4;
    let mut buffer = vec![0u8; (stride * height) as usize];

    let mut bmi: BITMAPINFO = unsafe { std::mem::zeroed() };
    bmi.bmiHeader.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
    bmi.bmiHeader.biWidth = width as i32;
    bmi.bmiHeader.biHeight = -(height as i32);
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 1;
    bmi.bmiHeader.biCompression = BI_RGB;

    let hdc = unsafe { GetDC(ptr::null_mut()) };
    if hdc.is_null() {
        return false;
    }
    let lines = unsafe {
        GetDIBits(
            hdc,
            mask,
            0,
            height,
            buffer.as_mut_ptr() as *mut c_void,
            &mut bmi,
            DIB_RGB_COLORS,
        )
    };
    unsafe {
        ReleaseDC(ptr::null_mut(), hdc);
    }
    if lines == 0 {
        return false;
    }

    for y in 0..height {
        for x in 0..width {
            let byte = buffer[(y * stride + x / 8) as usize];
            let bit = (byte >> (7 - (x % 8))) & 1;
            let index = ((y * width + x) * 4 + 3) as usize;
            pixels[index] = if bit == 1 { 0 } else { 255 };
        }
    }
    true
}

fn wide(path: &Path) -> Vec<u16> {
    path.to_string_lossy()
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect()
}
