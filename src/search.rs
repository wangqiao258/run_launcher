use crate::config::Item;
use crate::lnk_cache;
use pinyin::ToPinyin;

pub fn pinyin_initials(text: &str) -> String {
    let mut output = String::new();
    for ch in text.chars() {
        if ('\u{4e00}'..='\u{9fff}').contains(&ch) {
            if let Some(pinyin) = ch.to_pinyin() {
                output.push_str(pinyin.first_letter());
            }
        } else {
            output.extend(ch.to_lowercase());
        }
    }
    output
}

pub fn matches(item: &Item, query: &str) -> bool {
    let query = query.trim().to_lowercase();
    if query.is_empty() {
        return true;
    }
    if item.name.to_lowercase().contains(&query) {
        return true;
    }
    if pinyin_initials(&item.name).contains(&query) {
        return true;
    }
    let path = item.path.to_lowercase();
    if path.contains(&query) {
        return true;
    }
    if path.ends_with(".lnk")
        && let Some(target) = lnk_cache::resolve(std::path::Path::new(&item.path))
        && target.to_string_lossy().to_lowercase().contains(&query)
    {
        return true;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    fn item(name: &str, path: &str) -> Item {
        Item::new(1, name.to_string(), path.to_string(), None)
    }

    #[test]
    fn pinyin_initials_work() {
        assert_eq!(pinyin_initials("微信"), "wx");
        assert_eq!(pinyin_initials("VS Code"), "vs code");
    }

    #[test]
    fn matches_name_path_and_pinyin() {
        let notepad = item("记事本", "C:/Windows/notepad.exe");
        assert!(matches(&notepad, "记事"));
        assert!(matches(&notepad, "jsb"));
        assert!(matches(&notepad, "notepad"));
        assert!(!matches(&notepad, "chrome"));
    }
}
