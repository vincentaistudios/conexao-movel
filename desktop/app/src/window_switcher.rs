// SPDX-License-Identifier: GPL-3.0-or-later
//! Real-time active window detection, semantic app mapping, and window focusing
//! for the NectarLink mobile Stream Deck.

use nectarlink_core::{DeckAction, DeckPageConfig, DeckTileConfig};
use std::process::Command;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenAppWindow {
    pub wid: String,
    pub title: String,
    pub app_name: String,
    pub icon: String,
    pub color: String,
    pub is_focused: bool,
}

/// Lists currently visible top-level application windows on the PC.
pub fn list_open_windows() -> Vec<OpenAppWindow> {
    #[cfg(target_os = "linux")]
    {
        list_linux_windows()
    }
    #[cfg(target_os = "windows")]
    {
        list_windows_windows()
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        Vec::new()
    }
}

#[cfg(target_os = "linux")]
fn list_linux_windows() -> Vec<OpenAppWindow> {
    if std::env::var_os("DISPLAY").is_none() && std::env::var_os("WAYLAND_DISPLAY").is_none() {
        return Vec::new();
    }

    let active_wid = get_active_window_id_linux();

    // Query visible windows via `wmctrl -lp`
    let output = match Command::new("wmctrl").arg("-lp").output() {
        Ok(out) if out.status.success() => String::from_utf8_lossy(&out.stdout).to_string(),
        _ => return Vec::new(),
    };

    let mut result = Vec::new();

    for line in output.lines() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 4 {
            continue;
        }

        let wid = parts[0];
        let desktop = parts[1];
        let pid_str = parts[2];
        let host = parts[3];

        // Skip sticky desktop windows, panels, docks, and wallpaper layers
        if desktop == "-1" {
            continue;
        }

        let pid: u32 = pid_str.parse().unwrap_or(0);

        // Find the start of the title following the hostname
        let title = if let Some(idx) = line.find(host) {
            line[idx + host.len()..].trim().to_string()
        } else {
            String::new()
        };

        if title.is_empty() {
            continue;
        }

        let comm = get_process_comm(pid);
        let comm_lower = comm.to_ascii_lowercase();

        // Filter system layers, panels, and desktop widgets
        if comm_lower == "xfce4-panel"
            || comm_lower == "xfdesktop"
            || comm_lower == "linux-wallpaperengine"
            || comm_lower.starts_with("sys-desktop-widget")
            || comm_lower == "nectarlink"
            || comm_lower == "conky"
            || comm_lower == "polybar"
            || comm_lower == "waybar"
        {
            continue;
        }

        let (app_name, icon, color) = classify_window(&comm_lower, &title);
        let is_focused = active_wid.as_deref().is_some_and(|act| normalize_wid(act) == normalize_wid(wid));

        result.push(OpenAppWindow { wid: wid.to_string(), title, app_name, icon, color, is_focused });
    }

    result
}

#[cfg(target_os = "linux")]
fn get_process_comm(pid: u32) -> String {
    if pid == 0 {
        return String::new();
    }
    std::fs::read_to_string(format!("/proc/{pid}/comm")).map(|s| s.trim().to_string()).unwrap_or_default()
}

#[cfg(target_os = "linux")]
fn get_active_window_id_linux() -> Option<String> {
    if let Ok(out) = Command::new("xprop").args(["-root", "_NET_ACTIVE_WINDOW"]).output() {
        if out.status.success() {
            let text = String::from_utf8_lossy(&out.stdout);
            // Example: "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x6a00003, 0x0"
            if let Some(idx) = text.find('#') {
                let rest = &text[idx + 1..];
                let wid = rest.split(',').next().unwrap_or("").trim();
                if !wid.is_empty() {
                    return Some(wid.to_string());
                }
            }
        }
    }
    None
}

fn normalize_wid(wid: &str) -> String {
    let trimmed = wid.trim();
    let hex = trimmed.strip_prefix("0x").or_else(|| trimmed.strip_prefix("0X")).unwrap_or(trimmed);
    let hex_clean = hex.trim_start_matches('0');
    if hex_clean.is_empty() { "0".to_string() } else { hex_clean.to_ascii_lowercase() }
}

/// Maps process name and window title to semantic app name, vector icon, and color.
pub fn classify_window(comm_lower: &str, title: &str) -> (String, String, String) {
    let title_lower = title.to_ascii_lowercase();

    if comm_lower.contains("spotify") || title_lower.contains("spotify") {
        ("Spotify".to_string(), "music".to_string(), "emerald".to_string())
    } else if comm_lower.contains("minecraft") || title_lower.contains("minecraft") {
        ("Minecraft".to_string(), "gamepad".to_string(), "amber".to_string())
    } else if comm_lower.contains("discord") || title_lower.contains("discord") {
        ("Discord".to_string(), "chat".to_string(), "indigo".to_string())
    } else if comm_lower.contains("obs") || title_lower.contains("obs") {
        ("OBS Studio".to_string(), "video".to_string(), "ruby".to_string())
    } else if comm_lower.contains("chromium")
        || comm_lower.contains("chrome")
        || comm_lower.contains("firefox")
        || comm_lower.contains("brave")
        || comm_lower.contains("edge")
    {
        if title_lower.contains("twitch") {
            ("Twitch".to_string(), "video".to_string(), "purple".to_string())
        } else if title_lower.contains("crunchyroll") {
            ("Crunchyroll".to_string(), "video".to_string(), "orange".to_string())
        } else if title_lower.contains("youtube") {
            ("YouTube".to_string(), "video".to_string(), "ruby".to_string())
        } else {
            ("Navegador".to_string(), "globe".to_string(), "sapphire".to_string())
        }
    } else if comm_lower.contains("steam") || title_lower.contains("steam") {
        ("Steam".to_string(), "gamepad".to_string(), "slate".to_string())
    } else if comm_lower.contains("antigravity") || title_lower.contains("antigravity") {
        ("Antigravity".to_string(), "terminal".to_string(), "slate".to_string())
    } else if comm_lower.contains("terminal")
        || comm_lower.contains("bash")
        || comm_lower.contains("zsh")
        || comm_lower.contains("alacritty")
        || comm_lower.contains("kitty")
    {
        ("Terminal".to_string(), "terminal".to_string(), "graphite".to_string())
    } else {
        // Fallback: use first meaningful words of title
        let short_title = title.split(['—', '-', '•', '|']).next().unwrap_or(title).trim();
        let display_name = if short_title.len() > 18 {
            format!("{}...", &short_title[..15])
        } else if !short_title.is_empty() {
            short_title.to_string()
        } else {
            "Aplicativo".to_string()
        };
        (display_name, "window".to_string(), "sapphire".to_string())
    }
}

/// Focuses and raises a window by its raw ID string (e.g. "0x09000004").
pub fn focus_window_by_id(wid_str: &str) -> Result<(), String> {
    let clean = wid_str.trim();
    if clean.is_empty() {
        return Err("Empty window ID".to_string());
    }

    // Security check: only allow hexadecimal or decimal alphanumeric characters
    let hex_part = clean.strip_prefix("0x").or_else(|| clean.strip_prefix("0X")).unwrap_or(clean);
    if !hex_part.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err(format!("Invalid window ID format: {clean:?}"));
    }

    let hwnd = if let Some(hex) = clean.strip_prefix("0x").or_else(|| clean.strip_prefix("0X")) {
        isize::from_str_radix(hex, 16).map_err(|e| e.to_string())?
    } else {
        clean.parse::<isize>().map_err(|e| e.to_string())?
    };

    if hwnd == 0 {
        return Err("Zero window handle".to_string());
    }

    // Try in-process focus first
    #[cfg(target_os = "linux")]
    {
        let focused = crate::win::tray::focus_window(hwnd);
        if !focused {
            // CLI fallback with wmctrl
            let formatted = format!("0x{:x}", hwnd as usize);
            let _ = Command::new("wmctrl").args(["-i", "-a", &formatted]).status();
        }
        Ok(())
    }

    #[cfg(target_os = "windows")]
    {
        let focused = crate::win::tray::focus_window(hwnd);
        if focused { Ok(()) } else { Err("Failed to focus window on Windows".to_string()) }
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        let _ = hwnd;
        Err("Unsupported operating system".to_string())
    }
}

/// Detects the active screen geometry in pixels (width, height), respecting Ultrawide layouts.
pub fn get_screen_dimensions() -> (i32, i32) {
    #[cfg(target_os = "linux")]
    {
        if let Ok(out) = Command::new("xrandr").arg("--current").output() {
            let text = String::from_utf8_lossy(&out.stdout);
            for line in text.lines() {
                if let Some(idx) = line.find("current ") {
                    let rest = &line[idx + 8..];
                    let parts: Vec<&str> =
                        rest.split(',').next().unwrap_or("").split('x').map(|s| s.trim()).collect();
                    if parts.len() == 2 {
                        let w = parts[0].parse::<i32>().unwrap_or(0);
                        let h = parts[1].parse::<i32>().unwrap_or(0);
                        if w > 0 && h > 0 {
                            return (w, h);
                        }
                    }
                }
            }
        }
    }
    (1920, 1080)
}

/// Snaps and positions a window on the PC screen (fullscreen, maximize, half, quarters, center).
pub fn snap_window(wid_raw: &str, layout: &str) -> Result<(), String> {
    let clean = wid_raw.trim().replace("0x_", "0x");
    let (sw, sh) = get_screen_dimensions();

    #[cfg(target_os = "linux")]
    {
        // First ensure window is focused
        let _ = focus_window_by_id(&clean);

        match layout {
            "fullscreen" => {
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-b", "add,fullscreen"]).status();
            }
            "maximize" | "max" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "add,maximized_vert,maximized_horz"])
                    .status();
            }
            "left" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let geom = format!("0,0,0,{half_w},{sh}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "right" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let geom = format!("0,{half_w},0,{half_w},{sh}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "center" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let cw = (sw as f64 * 0.7) as i32;
                let ch = (sh as f64 * 0.8) as i32;
                let cx = (sw - cw) / 2;
                let cy = (sh - ch) / 2;
                let geom = format!("0,{cx},{cy},{cw},{ch}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "top_left" | "topleft" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let half_h = sh / 2;
                let geom = format!("0,0,0,{half_w},{half_h}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "top_right" | "topright" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let half_h = sh / 2;
                let geom = format!("0,{half_w},0,{half_w},{half_h}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "bottom_left" | "bottomleft" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let half_h = sh / 2;
                let geom = format!("0,0,{half_h},{half_w},{half_h}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            "bottom_right" | "bottomright" => {
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
                    .status();
                let half_w = sw / 2;
                let half_h = sh / 2;
                let geom = format!("0,{half_w},{half_h},{half_w},{half_h}");
                let _ = Command::new("wmctrl").args(["-i", "-r", &clean, "-e", &geom]).status();
            }
            _ => {
                // Default: focus and maximize full screen
                let _ = Command::new("wmctrl")
                    .args(["-i", "-r", &clean, "-b", "add,maximized_vert,maximized_horz"])
                    .status();
            }
        }
        let _ = Command::new("wmctrl").args(["-i", "-a", &clean]).status();
        Ok(())
    }

    #[cfg(not(target_os = "linux"))]
    {
        let _ = layout;
        focus_window_by_id(&clean)
    }
}

/// Builds a dynamic Deck page containing tiles for all open windows.
pub fn build_active_windows_page(windows: &[OpenAppWindow]) -> DeckPageConfig {
    let mut tiles = Vec::new();

    for win in windows {
        if tiles.len() >= nectarlink_core::MAX_DECK_TILES_PER_PAGE {
            break;
        }

        // Clean alphanumeric tile ID
        let clean_wid = win.wid.trim().replace("0x", "0x_");
        let tile_id = format!("focus_win_{clean_wid}");

        let label = if win.app_name.len() > 14 {
            format!("{}...", &win.app_name[..11])
        } else {
            win.app_name.clone()
        };

        tiles.push(DeckTileConfig {
            id: tile_id,
            label,
            icon: win.icon.clone(),
            color: win.color.clone(),
            action: DeckAction::SwitchWindow,
        });
    }

    DeckPageConfig { id: "page_active_windows".to_string(), name: "Janelas no PC".to_string(), tiles }
}

#[cfg(target_os = "windows")]
fn list_windows_windows() -> Vec<OpenAppWindow> {
    let win_list = crate::win::browser::windows();
    let mut out = Vec::new();
    for w in win_list {
        let wid = format!("0x{:x}", w.hwnd.0 as usize);
        let comm_lower = w.program.to_ascii_lowercase();
        let (app_name, icon, color) = classify_window(&comm_lower, &w.title);
        out.push(OpenAppWindow { wid, title: w.title, app_name, icon, color, is_focused: false });
    }
    out
}
