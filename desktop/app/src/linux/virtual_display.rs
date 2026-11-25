// SPDX-License-Identifier: GPL-3.0-or-later
//! Virtual display management for Linux X11 systems.
//! Extends the desktop onto a disconnected GPU display output (e.g. DisplayPort-0)
//! to turn mobile devices and tablets into physical second screens.

use std::process::Command;
use std::sync::Mutex;
use crate::win::browser::RECT;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VirtualDisplayGeometry {
    pub left: i32,
    pub top: i32,
    pub width: u32,
    pub height: u32,
}

impl VirtualDisplayGeometry {
    pub fn to_rect(&self) -> RECT {
        RECT {
            left: self.left,
            top: self.top,
            right: self.left + self.width as i32,
            bottom: self.top + self.height as i32,
        }
    }

    pub fn map_normalized(&self, nx: f32, ny: f32) -> (i32, i32) {
        let cx = nx.clamp(0.0, 1.0);
        let cy = ny.clamp(0.0, 1.0);
        let px = self.left + (cx * self.width as f32).round() as i32;
        let py = self.top + (cy * self.height as f32).round() as i32;
        (px, py)
    }
}

/// Active virtual display geometry shared for remote pointer mapping.
static ACTIVE_GEOMETRY: Mutex<Option<VirtualDisplayGeometry>> = Mutex::new(None);

pub fn active_virtual_geometry() -> Option<VirtualDisplayGeometry> {
    *ACTIVE_GEOMETRY.lock().unwrap_or_else(|e| e.into_inner())
}

pub fn set_active_virtual_geometry(geom: Option<VirtualDisplayGeometry>) {
    *ACTIVE_GEOMETRY.lock().unwrap_or_else(|e| e.into_inner()) = geom;
}

/// Parses `xrandr --query` output to extract the primary connected display and
/// available disconnected outputs.
pub fn parse_xrandr_query(output: &str) -> (Option<(String, u32, u32)>, Vec<String>) {
    let mut primary = None;
    let mut disconnected = Vec::new();

    for line in output.lines() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 2 {
            continue;
        }

        let name = parts[0].to_string();
        if parts[1] == "connected" {
            // Find resolution token formatted like 2560x1080+0+0
            for part in &parts[2..] {
                if let Some((dims, _offsets)) = part.split_once('+') {
                    if let Some((w_str, h_str)) = dims.split_once('x') {
                        if let (Ok(w), Ok(h)) = (w_str.parse::<u32>(), h_str.parse::<u32>()) {
                            if primary.is_none() || parts.contains(&"primary") {
                                primary = Some((name.clone(), w, h));
                            }
                            break;
                        }
                    }
                }
            }
        } else if parts[1] == "disconnected" {
            disconnected.push(name);
        }
    }

    (primary, disconnected)
}

/// RAII wrapper for managing a physical second screen virtual output via xrandr.
pub struct VirtualDisplay {
    pub output_name: String,
    pub geometry: VirtualDisplayGeometry,
    pub active: bool,
}

impl VirtualDisplay {
    /// Attempts to acquire an extended virtual display positioned right of the primary display.
    pub fn acquire(target_w: u32, target_h: u32) -> Result<Self, String> {
        let query_cmd = Command::new("xrandr")
            .arg("--query")
            .output()
            .map_err(|e| format!("failed to execute xrandr: {e}"))?;

        if !query_cmd.status.success() {
            return Err("xrandr query failed with non-zero exit status".into());
        }

        let raw_query = String::from_utf8_lossy(&query_cmd.stdout);
        let (primary, disconnected) = parse_xrandr_query(&raw_query);

        let (prim_name, prim_w, _prim_h) = primary
            .ok_or_else(|| "no connected primary display detected via xrandr".to_string())?;

        let chosen_output = disconnected
            .into_iter()
            .find(|name| name.starts_with("DisplayPort") || name.starts_with("HDMI") || name.starts_with("DVI"))
            .ok_or_else(|| "no suitable disconnected output available for virtual display".to_string())?;

        let mode_name = format!("{target_w}x{target_h}");

        // Add mode to the chosen disconnected output (may already exist, ignore non-fatal status).
        let _ = Command::new("xrandr")
            .args(["--addmode", &chosen_output, &mode_name])
            .status();

        // Enable the output positioned to the right of the primary display.
        let enable_status = Command::new("xrandr")
            .args([
                "--output",
                &chosen_output,
                "--mode",
                &mode_name,
                "--right-of",
                &prim_name,
            ])
            .status()
            .map_err(|e| format!("failed to enable virtual output {chosen_output}: {e}"))?;

        if !enable_status.success() {
            return Err(format!("xrandr returned failure enabling {chosen_output} with mode {mode_name}"));
        }

        let geometry = VirtualDisplayGeometry {
            left: prim_w as i32,
            top: 0,
            width: target_w,
            height: target_h,
        };

        set_active_virtual_geometry(Some(geometry));

        Ok(Self {
            output_name: chosen_output,
            geometry,
            active: true,
        })
    }

    pub fn region(&self) -> RECT {
        self.geometry.to_rect()
    }

    pub fn release(&mut self) {
        if self.active {
            let _ = Command::new("xrandr")
                .args(["--output", &self.output_name, "--off"])
                .status();
            self.active = false;
            set_active_virtual_geometry(None);
        }
    }
}

impl Drop for VirtualDisplay {
    fn drop(&mut self) {
        self.release();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_primary_and_disconnected_outputs_correctly() {
        let sample = "Screen 0: minimum 320 x 200, current 2560 x 1080, maximum 16384 x 16384\n\
                      DisplayPort-0 disconnected (normal left inverted right x axis y axis)\n\
                      DisplayPort-1 disconnected (normal left inverted right x axis y axis)\n\
                      HDMI-A-0 connected primary 2560x1080+0+0 798mm x 334mm\n";

        let (primary, disconnected) = parse_xrandr_query(sample);
        assert_eq!(primary, Some(("HDMI-A-0".to_string(), 2560, 1080)));
        assert_eq!(disconnected, vec!["DisplayPort-0".to_string(), "DisplayPort-1".to_string()]);
    }

    #[test]
    fn geometry_maps_normalized_coordinates_to_target_rectangle() {
        let geom = VirtualDisplayGeometry {
            left: 2560,
            top: 0,
            width: 1920,
            height: 1080,
        };

        let (x0, y0) = geom.map_normalized(0.0, 0.0);
        assert_eq!((x0, y0), (2560, 0));

        let (x_mid, y_mid) = geom.map_normalized(0.5, 0.5);
        assert_eq!((x_mid, y_mid), (3520, 540));

        let (x_max, y_max) = geom.map_normalized(1.0, 1.0);
        assert_eq!((x_max, y_max), (4480, 1080));
    }
}
