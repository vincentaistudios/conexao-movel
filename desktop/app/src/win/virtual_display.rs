// SPDX-License-Identifier: GPL-3.0-or-later
//! Windows virtual display stub for API parity with Linux.

use windows::Win32::Foundation::RECT;

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

pub fn active_virtual_geometry() -> Option<VirtualDisplayGeometry> {
    None
}

pub fn set_active_virtual_geometry(_geom: Option<VirtualDisplayGeometry>) {}

pub struct VirtualDisplay {
    pub output_name: String,
    pub geometry: VirtualDisplayGeometry,
}

impl VirtualDisplay {
    pub fn acquire(_target_w: u32, _target_h: u32) -> Result<Self, String> {
        Err("Virtual display is not supported on this platform".into())
    }

    pub fn region(&self) -> RECT {
        RECT::default()
    }

    pub fn release(&mut self) {}
}
