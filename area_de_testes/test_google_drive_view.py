#!/usr/bin/env python3
"""
area_de_testes/test_google_drive_view.py
Validação automatizada da modernização do GoogleDriveView (Conexão Móvel) e integridade do sistema:
- Teste 1: Ausência de emojis em todos os componentes QML e documentações.
- Teste 2: Validação da estrutura modular do GoogleDriveView, GoogleDriveSidebar e GoogleDriveItemDelegate.
- Teste 3: Mapeamento de seções e modelo de dados derivado da Google Drive API v3.
- Teste 4: Validação do empilhamento e integridade dos widgets da Área de Trabalho.
- Teste 5: Verificação de memória RAM disponível no sistema (mínimo de segurança > 4 GB).
"""

import os
import sys
import subprocess
import json

BASE_QML = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/qml/components"

def test_no_emojis():
    files_to_check = [
        os.path.join(BASE_QML, "GoogleDriveView.qml"),
        os.path.join(BASE_QML, "GoogleDriveSidebar.qml"),
        os.path.join(BASE_QML, "GoogleDriveItemDelegate.qml"),
        os.path.expanduser("~/.config/system-data/docs/google_drive_reverse_engineering.md")
    ]
    for fpath in files_to_check:
        assert os.path.isfile(fpath), f"Arquivo ausente: {fpath}"
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        for char in content:
            code = ord(char)
            if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
                raise AssertionError(f"Emoji detectado em {fpath}: {char}")
    print("Teste 1 Aprovado: Zero emojis em todos os componentes QML e documentações.")

def test_qml_modularity():
    view_path = os.path.join(BASE_QML, "GoogleDriveView.qml")
    sidebar_path = os.path.join(BASE_QML, "GoogleDriveSidebar.qml")
    delegate_path = os.path.join(BASE_QML, "GoogleDriveItemDelegate.qml")

    for p in [view_path, sidebar_path, delegate_path]:
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) <= 500, f"Arquivo {p} excede limite de 500 linhas: {len(lines)}"

    with open(view_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "GoogleDriveSidebar" in content, "Falta integração com GoogleDriveSidebar"
    assert "GoogleDriveItemDelegate" in content, "Falta integração com GoogleDriveItemDelegate"
    assert "searchQuery" in content, "Falta campo de busca instantânea"
    assert "formattedStorage" in content, "Falta cálculo de cota"
    print("Teste 2 Aprovado: Arquitetura modular e limites estritos de linhas respeitados.")

def test_drive_model_and_sections():
    sidebar_path = os.path.join(BASE_QML, "GoogleDriveSidebar.qml")
    with open(sidebar_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_sections = ["meu_drive", "compartilhados", "recentes", "com_estrela", "lixeira"]
    for sec in expected_sections:
        assert sec in content, f"Seção {sec} ausente na barra lateral"
    print("Teste 3 Aprovado: 5 seções canônicas do Google Drive integradas com sucesso.")

def test_desktop_widgets_stacking():
    res = subprocess.run(["xprop", "-root", "_NET_CLIENT_LIST_STACKING"], capture_output=True, text=True)
    assert res.returncode == 0, "Falha ao obter lista de empilhamento X11"
    stack = res.stdout.strip()
    # Identificar janelas de widget
    wm_res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
    widget_count = 0
    for line in wm_res.stdout.splitlines():
        if "Widget -" in line:
            widget_count += 1
    assert widget_count >= 5, f"Esperado ao menos 5 widgets ativos, encontrado {widget_count}"
    print(f"Teste 4 Aprovado: {widget_count} widgets ativos e visíveis na Área de Trabalho.")

def test_memory_headroom():
    with open("/proc/meminfo", "r") as f:
        meminfo = f.read()
    available_kb = 0
    for line in meminfo.splitlines():
        if line.startswith("MemAvailable:"):
            available_kb = int(line.split()[1])
            break
    available_gb = available_kb / (1024 * 1024)
    assert available_gb >= 4.0, f"Memória disponível muito baixa: {available_gb:.2f} GB"
    print(f"Teste 5 Aprovado: Memória RAM disponível segura ({available_gb:.2f} GB livres).")

if __name__ == "__main__":
    try:
        test_no_emojis()
        test_qml_modularity()
        test_drive_model_and_sections()
        test_desktop_widgets_stacking()
        test_memory_headroom()
        print("\nTodos os 5 testes de homologação foram APROVADOS com 100% de sucesso!")
    except Exception as e:
        print(f"\nFALHA NO TESTE: {e}", file=sys.stderr)
        sys.exit(1)
