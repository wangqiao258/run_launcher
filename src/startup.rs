use winreg::RegKey;
use winreg::enums::HKEY_CURRENT_USER;

const RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
const VALUE_NAME: &str = "RunLauncherRust";

pub fn command() -> String {
    let exe = std::env::current_exe().unwrap_or_default();
    format!("\"{}\"", exe.display())
}

pub fn is_enabled() -> bool {
    RegKey::predef(HKEY_CURRENT_USER)
        .open_subkey(RUN_KEY)
        .and_then(|key| key.get_value::<String, _>(VALUE_NAME))
        .map(|value| value == command())
        .unwrap_or(false)
}

pub fn set_enabled(enabled: bool) -> Result<(), String> {
    let current_user = RegKey::predef(HKEY_CURRENT_USER);
    let key = current_user
        .create_subkey(RUN_KEY)
        .map_err(|e| format!("open Run key: {e}"))?
        .0;

    if enabled {
        let cmd = command();
        key.set_value(VALUE_NAME, &cmd)
            .map_err(|e| format!("write autostart: {e}"))?;
        let verified = key
            .get_value::<String, _>(VALUE_NAME)
            .map_err(|e| format!("verify autostart: {e}"))?;
        if verified != cmd {
            return Err("autostart verification failed".to_string());
        }
    } else {
        match key.delete_value(VALUE_NAME) {
            Ok(()) => {}
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {}
            Err(err) => return Err(format!("remove autostart: {err}")),
        }
    }

    Ok(())
}
