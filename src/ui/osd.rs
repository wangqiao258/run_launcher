use std::ptr;
use std::sync::atomic::{AtomicIsize, Ordering};
use std::thread;

use windows_sys::Win32::Foundation::{COLORREF, HWND, LPARAM, LRESULT, RECT, WPARAM};
use windows_sys::Win32::Graphics::Gdi::{
    BeginPaint, CreateFontW, CreateRoundRectRgn, CreateSolidBrush, DeleteObject, DrawTextW,
    EndPaint, FillRect, HBRUSH, PAINTSTRUCT, SelectObject, SetBkMode, SetTextColor, SetWindowRgn,
    UpdateWindow,
};
use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
use windows_sys::Win32::UI::WindowsAndMessaging::{
    CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetClientRect, GetMessageW,
    GetSystemMetrics, GetWindowTextW, KillTimer, MSG, PostMessageW, PostQuitMessage,
    RegisterClassW, SM_CXSCREEN, SM_CYSCREEN, SW_SHOWNOACTIVATE, SetTimer, SetWindowTextW,
    ShowWindow, TranslateMessage, WM_CLOSE, WM_DESTROY, WM_PAINT, WM_TIMER, WNDCLASSW,
    WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST, WS_EX_TRANSPARENT, WS_POPUP,
};

const OSD_WIDTH: i32 = 300;
const OSD_HEIGHT: i32 = 64;
const OSD_CLASS: &str = "RunLauncherOsd";
const DT_CENTER: u32 = 0x0000_0001;
const DT_VCENTER: u32 = 0x0000_0004;
const DT_SINGLELINE: u32 = 0x0000_0020;

static LAST_HWND: AtomicIsize = AtomicIsize::new(0);

#[derive(Default)]
pub struct OsdState;

impl OsdState {
    pub fn popup(&mut self, text: String) {
        let previous = LAST_HWND.swap(0, Ordering::SeqCst);
        if previous != 0 {
            unsafe {
                PostMessageW(previous as HWND, WM_CLOSE, 0, 0);
            }
        }

        thread::spawn(move || unsafe {
            show_osd_window(&text);
        });
    }
}

#[allow(unsafe_op_in_unsafe_fn)]
unsafe fn show_osd_window(text: &str) {
    let class_name = wide(OSD_CLASS);
    let instance = GetModuleHandleW(ptr::null());
    if instance.is_null() {
        return;
    }

    let mut window_class: WNDCLASSW = std::mem::zeroed();
    window_class.lpfnWndProc = Some(wndproc);
    window_class.hInstance = instance;
    window_class.lpszClassName = class_name.as_ptr();
    let _ = RegisterClassW(&window_class);

    let title = wide(text);
    let x = (GetSystemMetrics(SM_CXSCREEN) - OSD_WIDTH) / 2;
    let y = GetSystemMetrics(SM_CYSCREEN) - 140 - OSD_HEIGHT;
    let hwnd = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT,
        class_name.as_ptr(),
        title.as_ptr(),
        WS_POPUP,
        x,
        y,
        OSD_WIDTH,
        OSD_HEIGHT,
        ptr::null_mut(),
        ptr::null_mut(),
        instance,
        ptr::null(),
    );
    if hwnd.is_null() {
        return;
    }

    let region = CreateRoundRectRgn(0, 0, OSD_WIDTH + 1, OSD_HEIGHT + 1, 24, 24);
    if !region.is_null() {
        SetWindowRgn(hwnd, region, 1);
    }

    let _ = SetWindowTextW(hwnd, title.as_ptr());
    ShowWindow(hwnd, SW_SHOWNOACTIVATE);
    UpdateWindow(hwnd);
    SetTimer(hwnd, 1, 1100, None);
    LAST_HWND.store(hwnd as isize, Ordering::SeqCst);

    let mut message: MSG = std::mem::zeroed();
    while GetMessageW(&mut message, ptr::null_mut(), 0, 0) > 0 {
        let _ = TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    let _ = KillTimer(hwnd, 1);
}

#[allow(unsafe_op_in_unsafe_fn)]
unsafe extern "system" fn wndproc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    match message {
        WM_PAINT => {
            let mut paint: PAINTSTRUCT = std::mem::zeroed();
            let hdc = BeginPaint(hwnd, &mut paint);
            let mut rect: RECT = std::mem::zeroed();
            GetClientRect(hwnd, &mut rect);

            let brush: HBRUSH = CreateSolidBrush(rgb(28, 30, 34));
            if !brush.is_null() {
                FillRect(hdc, &rect, brush);
                let _ = DeleteObject(brush);
            }

            let mut buffer = [0u16; 256];
            let length = GetWindowTextW(hwnd, buffer.as_mut_ptr(), buffer.len() as i32);
            if length > 0 {
                let face = wide("Microsoft YaHei");
                let font = CreateFontW(-22, 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 5, 0, face.as_ptr());
                if !font.is_null() {
                    let previous = SelectObject(hdc, font);
                    SetBkMode(hdc, 1);
                    SetTextColor(hdc, rgb(74, 158, 255));
                    DrawTextW(
                        hdc,
                        buffer.as_ptr(),
                        length,
                        &mut rect,
                        DT_CENTER | DT_VCENTER | DT_SINGLELINE,
                    );
                    SelectObject(hdc, previous);
                    let _ = DeleteObject(font);
                }
            }

            EndPaint(hwnd, &paint);
            0
        }
        WM_TIMER => {
            let _ = KillTimer(hwnd, 1);
            DestroyWindow(hwnd);
            0
        }
        WM_CLOSE => {
            DestroyWindow(hwnd);
            0
        }
        WM_DESTROY => {
            LAST_HWND.store(0, Ordering::SeqCst);
            PostQuitMessage(0);
            0
        }
        _ => DefWindowProcW(hwnd, message, wparam, lparam),
    }
}

fn wide(text: &str) -> Vec<u16> {
    text.encode_utf16().chain(std::iter::once(0)).collect()
}

fn rgb(r: u8, g: u8, b: u8) -> COLORREF {
    r as u32 | ((g as u32) << 8) | ((b as u32) << 16)
}
