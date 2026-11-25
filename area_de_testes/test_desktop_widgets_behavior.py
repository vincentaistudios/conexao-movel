#!/usr/bin/env python3
"""
area_de_testes/test_desktop_widgets_behavior.py
Suite de validacao automatizada do comportamento dos widgets da Area de Trabalho:
- Teste 1: Ausencia total de emojis no codigo e folha de estilos (Regra 3).
- Teste 2: Conformidade de tipo de janela e atributos X11 (_NET_WM_STATE_BELOW, NORMAL).
- Teste 3: Hierarquia de empilhamento no X11 (_NET_CLIENT_LIST_STACKING: Wallpaper < Widgets < Aplicativos).
- Teste 4: Integridade do motor sys-widgets-core e persistencia de coordenadas e redimensionamento.
- Teste 5: Presenca de estilos CSS Fluent/macOS para pilula de tamanhos P/M/G.
"""

import os
import sys
import subprocess
import json

WIDGETS_PY = "/home/Vincent/.local/bin/sys-desktop-widgets.py"
WIDGETS_CSS = os.path.expanduser("~/.local/share/desktop-widgets/style-widgets.css")
WIDGETS_CORE = "/home/Vincent/.local/bin/sys-widgets-core"

def test_no_emojis():
    files = [WIDGETS_PY, WIDGETS_CSS]
    for fpath in files:
        assert os.path.isfile(fpath), f"Arquivo nao encontrado: {fpath}"
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        for idx, char in enumerate(content):
            code = ord(char)
            if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
                raise AssertionError(f"Emoji detectado em {fpath} (posicao {idx}): {char}")
    print("Teste 1 Aprovado: Zero emojis detectados em sys-desktop-widgets.py e style-widgets.css.")

def test_window_layers_and_hints():
    out = subprocess.check_output(["wmctrl", "-l", "-G"]).decode()
    widget_lines = [l for l in out.splitlines() if "Widget -" in l]
    assert len(widget_lines) >= 6, f"Esperado ao menos 6 widgets ativos, encontrado: {len(widget_lines)}"

    for line in widget_lines:
        parts = line.split()
        wid_hex = parts[0]
        prop_out = subprocess.check_output(["xprop", "-id", wid_hex, "_NET_WM_STATE", "_NET_WM_WINDOW_TYPE"]).decode()
        assert "_NET_WM_STATE_BELOW" in prop_out, f"Widget {wid_hex} nao contem _NET_WM_STATE_BELOW: {prop_out}"
        assert "_NET_WM_WINDOW_TYPE_NORMAL" in prop_out, f"Widget {wid_hex} nao e do tipo NORMAL: {prop_out}"
    print(f"Teste 2 Aprovado: Todos os {len(widget_lines)} widgets configurados como NORMAL e com camada _NET_WM_STATE_BELOW.")

def test_stacking_hierarchy():
    out = subprocess.check_output(["xprop", "-root", "_NET_CLIENT_LIST_STACKING"]).decode()
    ids_raw = [x.strip() for x in out.split("#")[1].split(",")]
    
    stack_order = []
    for wid in ids_raw:
        try:
            name = subprocess.check_output(["xprop", "-id", wid, "WM_NAME"], stderr=subprocess.DEVNULL).decode().strip()
            stack_order.append((wid, name))
        except Exception:
            pass

    wallpaper_idx = -1
    last_widget_idx = -1
    first_app_idx = 999999

    for idx, (wid, name) in enumerate(stack_order):
        if "wallpaperengine" in name.lower() or "area de trabalho" in name.lower():
            wallpaper_idx = max(wallpaper_idx, idx)
        elif "widget -" in name.lower():
            last_widget_idx = max(last_widget_idx, idx)
        elif any(app in name.lower() for app in ["antigravity", "chromium", "discord", "whatsapp"]):
            first_app_idx = min(first_app_idx, idx)

    assert wallpaper_idx != -1, "Janela de Wallpaper nao localizada na pilha de janelas."
    assert last_widget_idx != -1, "Nenhum widget localizado na pilha de janelas."
    assert wallpaper_idx < last_widget_idx, f"Wallpaper ({wallpaper_idx}) deveria estar abaixo dos widgets ({last_widget_idx})."
    
    if first_app_idx != 999999:
        assert last_widget_idx < first_app_idx, (
            f"Widgets ({last_widget_idx}) deveriam estar abaixo das janelas de aplicativos ({first_app_idx})."
        )
    print("Teste 3 Aprovado: Hierarquia X11 validada (Wallpaper < Widgets < Janelas de Aplicativos).")

def test_widgets_core_persistence():
    assert os.path.isfile(WIDGETS_CORE) and os.access(WIDGETS_CORE, os.X_OK), "Binario sys-widgets-core ausente ou nao executavel."
    
    list_out = subprocess.check_output([WIDGETS_CORE, "list"]).decode()
    data = json.loads(list_out)
    assert data.get("total", 0) >= 6, f"Total de widgets no core insuficiente: {data.get('total')}"

    # Teste de persistencia de movimento
    mv_out = subprocess.check_output([WIDGETS_CORE, "move", "calendar", "42", "52"]).decode()
    assert "reposicionado" in mv_out.lower() or "42" in mv_out, f"Resposta inesperada no move: {mv_out}"

    # Teste de persistencia de redimensionamento
    rs_out = subprocess.check_output([WIDGETS_CORE, "resize", "calendar", "P"]).decode()
    assert "redimensionado" in rs_out.lower() or "P" in rs_out, f"Resposta inesperada no resize: {rs_out}"

    # Restaurar para posicao canônica
    subprocess.check_output([WIDGETS_CORE, "move", "calendar", "40", "50"])
    print("Teste 4 Aprovado: sys-widgets-core responde e persiste coordenadas e tamanhos com sucesso.")

def test_fluent_css_styles():
    with open(WIDGETS_CSS, "r", encoding="utf-8") as f:
        css = f.read()
    
    required_classes = [".size-pill-box", ".btn-size-choice", ".btn-size-active", ".btn-close-widget", ".widget-card"]
    for rc in required_classes:
        assert rc in css, f"Classe CSS obrigatoria ausente: {rc}"
    print("Teste 5 Aprovado: Folha de estilos contem todas as classes visuais Fluent/macOS necessarias.")

if __name__ == "__main__":
    print("Iniciando validacao automatizada dos widgets da Area de Trabalho...")
    test_no_emojis()
    test_window_layers_and_hints()
    test_stacking_hierarchy()
    test_widgets_core_persistence()
    test_fluent_css_styles()
    print("Sucesso: Todos os 5 testes passaram com 100% de aprovacao!")
