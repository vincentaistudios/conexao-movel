// SPDX-License-Identifier: GPL-3.0-or-later
//! O emblema oficial do Conexão Móvel (monograma 'V' com losango central ciano
//! sobre squircle escuro, fiel a `sys-device-link.svg`). Desenhado por código
//! em qualquer resolução (ícones de bandeja, janela, toasts e recurso do executável
//! em tempo de compilação via `build.rs`), sem dependências externas além da `std`.

const BG_START: [f32; 3] = rgb(0x0F, 0x17, 0x2A);
const BG_MID: [f32; 3] = rgb(0x11, 0x18, 0x27);
const BG_END: [f32; 3] = rgb(0x03, 0x07, 0x12);

const BORDER_START: [f32; 3] = rgb(0x38, 0xBD, 0xF8);
const BORDER_MID: [f32; 3] = rgb(0x63, 0x66, 0xF1);
const BORDER_END: [f32; 3] = rgb(0x0E, 0xA5, 0xE9);

const GLOW_CYAN: [f32; 3] = rgb(0x38, 0xBD, 0xF8);
const GLOW_INDIGO: [f32; 3] = rgb(0x63, 0x66, 0xF1);

const V_LEFT_START: [f32; 3] = rgb(0xFF, 0xFF, 0xFF);
const V_LEFT_MID: [f32; 3] = rgb(0xF1, 0xF5, 0xF9);
const V_LEFT_END: [f32; 3] = rgb(0xCB, 0xD5, 0xE1);

const V_RIGHT_START: [f32; 3] = rgb(0xE2, 0xE8, 0xF0);
const V_RIGHT_MID: [f32; 3] = rgb(0x94, 0xA3, 0xB8);
const V_RIGHT_END: [f32; 3] = rgb(0x64, 0x74, 0x8B);

const V_CENTER_TOP: [f32; 3] = rgb(0x38, 0xBD, 0xF8);
const V_CENTER_BOTTOM: [f32; 3] = rgb(0x60, 0xA5, 0xFA);
const V_TIP_WHITE: [f32; 3] = rgb(0xFF, 0xFF, 0xFF);

/// Mapeamento do grupo `<g transform="translate(25.6, 15) scale(0.90)">` da grade 512×512 para 100×100.
const fn map_svg(sx: f32, sy: f32) -> (f32, f32) {
    ((25.6 + 0.90 * sx) * (100.0 / 512.0), (15.0 + 0.90 * sy) * (100.0 / 512.0))
}

const LEFT_WING: [(f32, f32); 4] =
    [map_svg(72.0, 96.0), map_svg(168.0, 96.0), map_svg(256.0, 364.0), map_svg(216.0, 428.0)];
const RIGHT_WING: [(f32, f32); 4] =
    [map_svg(440.0, 96.0), map_svg(344.0, 96.0), map_svg(256.0, 364.0), map_svg(296.0, 428.0)];
const CENTER_DIAMOND: [(f32, f32); 4] =
    [map_svg(256.0, 120.0), map_svg(284.0, 175.0), map_svg(256.0, 230.0), map_svg(228.0, 175.0)];
const BOTTOM_TIP: [(f32, f32); 4] =
    [map_svg(256.0, 364.0), map_svg(216.0, 428.0), map_svg(256.0, 448.0), map_svg(296.0, 428.0)];

/// Grade de supersampling por pixel (`SS×SS`) para bordas suaves e nítidas.
const SS: usize = 4;

const fn rgb(r: u8, g: u8, b: u8) -> [f32; 3] {
    [r as f32, g as f32, b as f32]
}

/// Renderiza o ícone em RGBA straight-alpha (`size × size`), linha a linha.
pub fn render(size: usize) -> Vec<u8> {
    if size == 0 {
        return Vec::new();
    }
    let inset = if size <= 32 { 2.0 } else { 4.0 };
    let corner = 22.0;
    let span = 100.0 - 2.0 * inset;
    let unit = 100.0 / size as f32;
    let rim = (1.1f32).max(unit * 0.85);

    let lw_bounds = bounds(&LEFT_WING);
    let rw_bounds = bounds(&RIGHT_WING);
    let cd_y0 = CENTER_DIAMOND[0].1;
    let cd_y1 = CENTER_DIAMOND[2].1;

    let mut out = vec![0u8; size * size * 4];
    for py in 0..size {
        for px in 0..size {
            let mut color = [0f32; 3];
            let mut covered = 0usize;
            for sy in 0..SS {
                for sx in 0..SS {
                    let x = (px as f32 + (sx as f32 + 0.5) / SS as f32) * unit;
                    let y = (py as f32 + (sy as f32 + 0.5) / SS as f32) * unit;
                    let edge = rounded_square_distance(x, y, inset, corner);
                    if edge > 0.0 {
                        continue;
                    }
                    covered += 1;

                    let diag_t = (((x - inset) + (y - inset)) / (2.0 * span)).clamp(0.0, 1.0);
                    let mut bg = grad3(BG_START, BG_MID, BG_END, 0.5, diag_t);

                    // Brilho radial ambiente atrás do monograma (`cx=50, cy=48.4` e `50, 50`).
                    let d_cyan = ((x - 50.0).powi(2) + (y - 48.4375).powi(2)).sqrt();
                    if d_cyan < 31.25 {
                        let fade = (1.0 - d_cyan / 31.25).clamp(0.0, 1.0);
                        bg = mix(bg, GLOW_CYAN, 0.12 * (0.4 + 0.6 * fade));
                    }
                    let d_indigo = ((x - 50.0).powi(2) + (y - 50.0).powi(2)).sqrt();
                    if d_indigo < 19.53125 {
                        let fade = (1.0 - d_indigo / 19.53125).clamp(0.0, 1.0);
                        bg = mix(bg, GLOW_INDIGO, 0.16 * (0.4 + 0.6 * fade));
                    }

                    let paint = if point_in_poly((x, y), &BOTTOM_TIP) {
                        V_TIP_WHITE
                    } else if point_in_poly((x, y), &CENTER_DIAMOND) {
                        let t = ((y - cd_y0) / (cd_y1 - cd_y0)).clamp(0.0, 1.0);
                        mix(V_CENTER_TOP, V_CENTER_BOTTOM, t)
                    } else if point_in_poly((x, y), &LEFT_WING) {
                        let t = diag_in_bounds(x, y, lw_bounds);
                        grad3(V_LEFT_START, V_LEFT_MID, V_LEFT_END, 0.60, t)
                    } else if point_in_poly((x, y), &RIGHT_WING) {
                        let t = diag_in_bounds(x, y, rw_bounds);
                        grad3(V_RIGHT_START, V_RIGHT_MID, V_RIGHT_END, 0.50, t)
                    } else if -edge <= rim {
                        let border_col = grad3(BORDER_START, BORDER_MID, BORDER_END, 0.50, diag_t);
                        let border_alpha = if diag_t <= 0.5 {
                            0.8 - 0.4 * (diag_t / 0.5)
                        } else {
                            0.4 + 0.4 * ((diag_t - 0.5) / 0.5)
                        };
                        mix(bg, border_col, border_alpha)
                    } else {
                        bg
                    };

                    for c in 0..3 {
                        color[c] += paint[c];
                    }
                }
            }
            if covered == 0 {
                continue;
            }
            let i = (py * size + px) * 4;
            for c in 0..3 {
                out[i + c] = (color[c] / covered as f32).round() as u8;
            }
            out[i + 3] = ((covered as f32 / (SS * SS) as f32) * 255.0).round() as u8;
        }
    }
    out
}

fn mix(a: [f32; 3], b: [f32; 3], t: f32) -> [f32; 3] {
    [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]
}

fn grad3(c0: [f32; 3], c1: [f32; 3], c2: [f32; 3], mid: f32, t: f32) -> [f32; 3] {
    if t <= mid {
        mix(c0, c1, (t / mid).clamp(0.0, 1.0))
    } else {
        mix(c1, c2, ((t - mid) / (1.0 - mid)).clamp(0.0, 1.0))
    }
}

fn bounds(poly: &[(f32, f32)]) -> (f32, f32, f32, f32) {
    let mut min_x = f32::INFINITY;
    let mut min_y = f32::INFINITY;
    let mut max_x = f32::NEG_INFINITY;
    let mut max_y = f32::NEG_INFINITY;
    for &(x, y) in poly {
        min_x = min_x.min(x);
        min_y = min_y.min(y);
        max_x = max_x.max(x);
        max_y = max_y.max(y);
    }
    (min_x, min_y, max_x, max_y)
}

fn diag_in_bounds(x: f32, y: f32, (x0, y0, x1, y1): (f32, f32, f32, f32)) -> f32 {
    let tx = (x - x0) / (x1 - x0).max(1e-3);
    let ty = (y - y0) / (y1 - y0).max(1e-3);
    ((tx + ty) * 0.5).clamp(0.0, 1.0)
}

fn point_in_poly(p: (f32, f32), poly: &[(f32, f32)]) -> bool {
    let mut inside = false;
    let n = poly.len();
    let mut j = n - 1;
    for i in 0..n {
        let (xi, yi) = poly[i];
        let (xj, yj) = poly[j];
        let crosses = (yi > p.1) != (yj > p.1);
        if crosses && p.0 < (xj - xi) * (p.1 - yi) / (yj - yi) + xi {
            inside = !inside;
        }
        j = i;
    }
    inside
}

/// Distância externa ao squircle arredondado `[inset .. 100 - inset]` com raio `r`.
fn rounded_square_distance(x: f32, y: f32, inset: f32, r: f32) -> f32 {
    let (lo, hi) = (inset + r, 100.0 - inset - r);
    let qx = (x.clamp(lo, hi) - x).abs();
    let qy = (y.clamp(lo, hi) - y).abs();
    if x > lo && x < hi || y > lo && y < hi {
        let to_x = (x - inset).min(100.0 - inset - x);
        let to_y = (y - inset).min(100.0 - inset - y);
        return -to_x.min(to_y);
    }
    (qx * qx + qy * qy).sqrt() - r
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pixel(img: &[u8], size: usize, x: usize, y: usize) -> [u8; 4] {
        let i = (y * size + x) * 4;
        [img[i], img[i + 1], img[i + 2], img[i + 3]]
    }

    #[test]
    fn corners_are_transparent_and_diamond_is_cyan() {
        let size = 64;
        let img = render(size);
        assert_eq!(img.len(), size * size * 4);
        assert_eq!(pixel(&img, size, 0, 0)[3], 0, "canto arredondado transparente");

        // Centro do losango ciano: map_svg(256, 175) = (50.0, 33.69) -> px (32, 21) em 64px.
        let diamond = pixel(&img, size, 32, 21);
        assert_eq!(diamond[3], 255);
        assert!(diamond[2] > diamond[0] && diamond[1] > diamond[0], "losango ciano: {diamond:?}");

        // Fundo superior escuro do squircle (sem cores antigas de mel/marrom #FFB95F/#2C1600).
        let tile_top = pixel(&img, size, 32, 8);
        assert_eq!(tile_top[3], 255);
        assert!(tile_top[2] >= tile_top[0] && tile_top[0] < 0x40, "fundo escuro azulado: {tile_top:?}");

        // Garante que não restou nenhum pixel do antigo #FFB95F (R=255, G=185, B=95).
        let has_old_honey = img.chunks_exact(4).any(|p| p == [0xFF, 0xB9, 0x5F, 0xFF]);
        assert!(!has_old_honey, "nenhum pixel do antigo Waggle Dance");
    }

    #[test]
    fn both_v_wings_and_tip_are_drawn() {
        let size = 128;
        let img = render(size);
        let is_bright = |p: [u8; 4]| p[3] == 255 && p[0] > 0x90 && p[1] > 0xA0 && p[2] > 0xB0;
        let left = (16..58).any(|x| is_bright(pixel(&img, size, x, 34)));
        let right = (70..112).any(|x| is_bright(pixel(&img, size, x, 34)));
        let tip = pixel(&img, size, 64, 96);
        assert!(left && right, "ambas as asas do V devem ser desenhadas");
        assert!(tip[3] == 255 && tip[0] > 0xE0 && tip[1] > 0xE0 && tip[2] > 0xE0, "ponta branca: {tip:?}");
    }

    #[test]
    fn renders_every_icon_size() {
        for size in [16, 20, 24, 32, 40, 48, 64, 128, 256] {
            let img = render(size);
            assert_eq!(img.len(), size * size * 4);
            let center = pixel(&img, size, size / 2, size / 2);
            assert_eq!(center[3], 255, "{size}px deve ter centro opaco");
        }
    }
}
