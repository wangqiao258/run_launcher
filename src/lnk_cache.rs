use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};
use std::time::UNIX_EPOCH;

type CacheKey = (PathBuf, u64);
type CacheMap = HashMap<CacheKey, Option<PathBuf>>;

fn target_cache() -> &'static Mutex<CacheMap> {
    static CACHE: OnceLock<Mutex<CacheMap>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

pub fn resolve(path: &std::path::Path) -> Option<PathBuf> {
    let modified = std::fs::metadata(path)
        .ok()
        .and_then(|meta| meta.modified().ok())
        .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos() as u64)
        .unwrap_or(0);
    let key = (path.to_path_buf(), modified);

    if let Ok(cache) = target_cache().lock()
        && let Some(cached) = cache.get(&key)
    {
        return cached.clone();
    }

    let resolved = lnk::ShellLink::open(path, lnk::encoding::WINDOWS_1252)
        .ok()
        .and_then(|link| link.link_target())
        .map(PathBuf::from)
        .filter(|target| target.is_file());

    if let Ok(mut cache) = target_cache().lock() {
        if cache.len() >= 512 {
            cache.clear();
        }
        cache.insert(key, resolved.clone());
    }
    resolved
}
