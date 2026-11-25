// SPDX-License-Identifier: GPL-3.0-or-later
//! Watcher em segundo plano para detecção automática da Spike do Valorant no Windows.
//! Opera por amostragem visual não invasiva de pixels no topo central do HUD (via GDI),
//! sendo 100% seguro contra o anticheat Riot Vanguard (sem leitura de memória ou injeção).

use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

/// Assinatura cromática do Vermelho característico da Spike armada no Valorant (#FF4655).
pub fn classify_pixel_is_spike_red(r: u8, g: u8, b: u8) -> bool {
    r > 190 && g < 115 && b < 135 && r.saturating_sub(g) > 90 && r.saturating_sub(b) > 75
}

/// Avalia se uma matriz de pixels amostrada contém densidade suficiente de vermelho Spike.
pub fn is_spike_hud_active(pixels: &[(u8, u8, u8)]) -> bool {
    if pixels.is_empty() {
        return false;
    }
    let count = pixels.iter().filter(|&&(r, g, b)| classify_pixel_is_spike_red(r, g, b)).count();
    let ratio = count as f32 / pixels.len() as f32;
    // Se ao menos 12% da área central apresentar o vermelho Spike característico
    ratio >= 0.12
}

/// Máquina de estados para transições da Spike.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpikeWatcherStatus {
    Idle,
    Planted,
}

#[derive(Debug)]
pub struct SpikeStateMachine {
    pub status: SpikeWatcherStatus,
    pub consecutive_positives: u32,
    pub consecutive_negatives: u32,
    pub planted_instant: Option<Instant>,
}

impl Default for SpikeStateMachine {
    fn default() -> Self {
        Self::new()
    }
}

impl SpikeStateMachine {
    pub fn new() -> Self {
        Self {
            status: SpikeWatcherStatus::Idle,
            consecutive_positives: 0,
            consecutive_negatives: 0,
            planted_instant: None,
        }
    }

    /// Processa um frame amostrado. Retorna `Some(action)` caso ocorra transição de estado.
    /// Ações possíveis: `"planted"`, `"reset"`.
    pub fn update(&mut self, is_positive: bool) -> Option<&'static str> {
        match self.status {
            SpikeWatcherStatus::Idle => {
                if is_positive {
                    self.consecutive_positives += 1;
                    // Debounce: 2 frames consecutivos positivos (aprox. 160ms) para evitar falso-positivo
                    if self.consecutive_positives >= 2 {
                        self.status = SpikeWatcherStatus::Planted;
                        self.planted_instant = Some(Instant::now());
                        self.consecutive_positives = 0;
                        self.consecutive_negatives = 0;
                        return Some("planted");
                    }
                } else {
                    self.consecutive_positives = 0;
                }
                None
            }
            SpikeWatcherStatus::Planted => {
                let elapsed = self.planted_instant.map(|t| t.elapsed()).unwrap_or_default();
                // Limite máximo de uma Spike no Valorant é 45 segundos (40s para detonar + margem)
                if elapsed > Duration::from_secs(45) {
                    self.status = SpikeWatcherStatus::Idle;
                    self.consecutive_negatives = 0;
                    self.planted_instant = None;
                    return Some("reset");
                }

                if !is_positive {
                    self.consecutive_negatives += 1;
                    // Spike desarmada ou rodada terminada: 8 frames negativos consecutivos (~640ms)
                    if self.consecutive_negatives >= 8 {
                        self.status = SpikeWatcherStatus::Idle;
                        self.consecutive_negatives = 0;
                        self.planted_instant = None;
                        return Some("reset");
                    }
                } else {
                    self.consecutive_negatives = 0;
                }
                None
            }
        }
    }
}

static WATCHER_RUNNING: AtomicBool = AtomicBool::new(false);

/// Inicia o daemon do Spike Watcher em segundo plano.
pub fn start_watcher() {
    if WATCHER_RUNNING.swap(true, Ordering::SeqCst) {
        return;
    }

    tracing::info!("Inicializando Spike Watcher autônomo para Valorant");

    std::thread::Builder::new()
        .name("spike-watcher".into())
        .spawn(move || {
            run_watcher_loop();
        })
        .expect("falha ao iniciar thread do spike-watcher");
}

fn run_watcher_loop() {
    #[allow(unused_mut, unused_variables)]
    let mut state_machine = SpikeStateMachine::new();

    loop {
        std::thread::sleep(Duration::from_millis(80));

        if !crate::settings::valorant_spike_auto_detect() {
            continue;
        }

        #[cfg(windows)]
        {
            if !is_valorant_foreground() {
                // Se o Valorant não está em foco e estávamos em Idle, apenas continua
                if state_machine.status == SpikeWatcherStatus::Idle {
                    state_machine.consecutive_positives = 0;
                    continue;
                }
            }

            let sample = sample_hud_pixels_windows();
            let is_positive = sample.as_deref().map(is_spike_hud_active).unwrap_or(false);

            if let Some(action) = state_machine.update(is_positive) {
                tracing::info!(action, "Spike Watcher disparou transição automática");
                let _ = crate::deck::handle_spike_command(action);
            }
        }

        #[cfg(not(windows))]
        {
            // Em ambiente não-Windows (desenvolvimento/testes), o watcher aguarda passivamente
            std::thread::sleep(Duration::from_millis(500));
        }
    }
}

#[cfg(windows)]
#[allow(unsafe_code)]
fn is_valorant_foreground() -> bool {
    use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowTextW};

    unsafe {
        let hwnd = GetForegroundWindow();
        if hwnd.0.is_null() {
            return false;
        }

        let mut title_buf = [0u16; 256];
        let len = GetWindowTextW(hwnd, &mut title_buf);
        if len > 0 {
            let title = String::from_utf16_lossy(&title_buf[..len as usize]);
            if title.contains("VALORANT") {
                return true;
            }
        }
        false
    }
}

#[cfg(windows)]
#[allow(unsafe_code)]
fn sample_hud_pixels_windows() -> Option<Vec<(u8, u8, u8)>> {
    use windows::Win32::Graphics::Gdi::{
        BI_RGB, BITMAPINFO, BITMAPINFOHEADER, BitBlt, CreateCompatibleBitmap, CreateCompatibleDC,
        DIB_RGB_COLORS, DeleteDC, DeleteObject, GetDC, GetDIBits, ReleaseDC, SRCCOPY, SelectObject,
    };
    use windows::Win32::UI::WindowsAndMessaging::{GetSystemMetrics, SM_CXSCREEN, SM_CYSCREEN};

    unsafe {
        let screen_w = GetSystemMetrics(SM_CXSCREEN);
        let screen_h = GetSystemMetrics(SM_CYSCREEN);
        if screen_w <= 0 || screen_h <= 0 {
            return None;
        }

        // Região central superior do HUD do Valorant onde o relógio/Spike é posicionado
        let sample_w: i32 = 16;
        let sample_h: i32 = 16;
        let center_x = screen_w / 2;
        let center_y = (screen_h as f32 * 0.040) as i32;

        let start_x = (center_x - sample_w / 2).max(0);
        let start_y = (center_y - sample_h / 2).max(0);

        let hdc_screen = GetDC(None);
        if hdc_screen.0.is_null() {
            return None;
        }

        let hdc_mem = CreateCompatibleDC(Some(hdc_screen));
        if hdc_mem.0.is_null() {
            let _ = ReleaseDC(None, hdc_screen);
            return None;
        }

        let hbitmap = CreateCompatibleBitmap(hdc_screen, sample_w, sample_h);
        if hbitmap.0.is_null() {
            let _ = DeleteDC(hdc_mem);
            let _ = ReleaseDC(None, hdc_screen);
            return None;
        }

        let old_bmp = SelectObject(hdc_mem, hbitmap.into());

        let blt_res = BitBlt(hdc_mem, 0, 0, sample_w, sample_h, Some(hdc_screen), start_x, start_y, SRCCOPY);

        let mut pixels = Vec::with_capacity((sample_w * sample_h) as usize);

        if blt_res.is_ok() {
            let mut bmi = BITMAPINFO {
                bmiHeader: BITMAPINFOHEADER {
                    biSize: std::mem::size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: sample_w,
                    biHeight: -sample_h, // Orientação de cima para baixo
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: BI_RGB.0,
                    ..Default::default()
                },
                ..Default::default()
            };

            let mut buffer = vec![0u8; (sample_w * sample_h * 4) as usize];
            let lines = GetDIBits(
                hdc_mem,
                hbitmap,
                0,
                sample_h as u32,
                Some(buffer.as_mut_ptr() as *mut _),
                &mut bmi,
                DIB_RGB_COLORS,
            );

            if lines > 0 {
                for chunk in buffer.chunks_exact(4) {
                    let b = chunk[0];
                    let g = chunk[1];
                    let r = chunk[2];
                    pixels.push((r, g, b));
                }
            }
        }

        let _ = SelectObject(hdc_mem, old_bmp);
        let _ = DeleteObject(hbitmap.into());
        let _ = DeleteDC(hdc_mem);
        let _ = ReleaseDC(None, hdc_screen);

        if pixels.is_empty() { None } else { Some(pixels) }
    }
}
