#!/usr/bin/env python3
"""
area_de_testes/test_conexao_movel_localization.py
Suite de validacao automatizada da nacionalizacao e refino do Conexao Movel:
- Teste 1: Verificacao da sintaxe XML de todos os arquivos de strings.
- Teste 2: Auditoria de eliminacao de 'NectarLink' em strings do usuario final.
- Teste 3: Verificacao dos termos padronizados (Painel de Atalhos, Acesso Avancado, Conexao Movel).
- Teste 4: Verificacao da traducao do Desktop Qt (nectarlink_pt_BR.ts).
- Teste 5: Verificacao da integridade e assinatura do APK gerado.
"""

import os
import subprocess
import xml.etree.ElementTree as ET
import sys

def test_xml_syntax():
    res_dir = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/res"
    folders = ["values", "values-pt", "values-pt-rBR"]
    for f in folders:
        path = os.path.join(res_dir, f, "strings.xml")
        assert os.path.isfile(path), f"Arquivo nao encontrado: {path}"
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            assert root.tag == "resources", f"Tag raiz invalida em {path}: {root.tag}"
        except Exception as e:
            raise AssertionError(f"Erro de sintaxe XML em {path}: {e}")
    print("Teste 1 Aprovado: Todos os arquivos strings.xml do Android possuem sintaxe XML valida e integra.")

def test_absence_of_legacy_branding():
    res_dir = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/res"
    folders = ["values", "values-pt", "values-pt-rBR"]
    for f in folders:
        path = os.path.join(res_dir, f, "strings.xml")
        tree = ET.parse(path)
        root = tree.getroot()
        for elem in root.findall("string"):
            text = elem.text or ""
            if "NectarLink" in text:
                raise AssertionError(f"Legado 'NectarLink' ainda presente em {f}: [{elem.get('name')}] -> {text}")
    print("Teste 2 Aprovado: Zero ocorrencias de 'NectarLink' em todos os recursos de strings do Android.")

def test_canonical_terms():
    path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/res/values-pt-rBR/strings.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    strings_dict = {elem.get("name"): elem.text for elem in root.findall("string")}
    
    assert strings_dict.get("app_name") == "Conexão Móvel", f"app_name incorreto: {strings_dict.get('app_name')}"
    assert "Painel de Atalhos" in strings_dict.get("action_deck_pc", ""), "Falha na traducao de Deck"
    assert "Acesso Avançado" in strings_dict.get("walkthrough_power_elevated_title", ""), "Falha na traducao de Elevated"
    assert "Acessibilidade" in strings_dict.get("walkthrough_power_assist_title", ""), "Falha na traducao de Assist"
    assert "Versão de Testes" in strings_dict.get("update_channel_nightly", ""), "Falha na traducao de Nightly"
    print("Teste 3 Aprovado: Termos canonicos padronizados validados com sucesso.")

def test_desktop_translations():
    ts_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/i18n/nectarlink_pt_BR.ts"
    assert os.path.isfile(ts_path), f"Arquivo .ts nao encontrado: {ts_path}"
    tree = ET.parse(ts_path)
    root = tree.getroot()
    for elem in root.iter("translation"):
        if elem.text and "NectarLink" in elem.text:
            raise AssertionError(f"Legado 'NectarLink' presente na traducao do Desktop: {elem.text}")
    print("Teste 4 Aprovado: Traducoes da interface Desktop Qt 100% livres de 'NectarLink'.")

def test_apk_integrity_and_signature():
    apk_paths = [
        "/home/Vincent/Downloads/nectarlink-apk/ConexaoMovel.apk",
        "/home/Vincent/Área de trabalho/ConexaoMovel.apk"
    ]
    for apk_path in apk_paths:
        assert os.path.isfile(apk_path), f"APK nao encontrado: {apk_path}"
        size_mb = os.path.getsize(apk_path) / (1024 * 1024)
        assert size_mb > 45, f"Tamanho do APK suspeito ({size_mb:.1f} MB)"
        
        # Validar assinatura com apksigner
        res = subprocess.run(["apksigner", "verify", "--verbose", apk_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Falha na verificacao de assinatura do APK: {res.stderr}"
        assert "Verified using v2 scheme (APK Signature Scheme v2): true" in res.stdout, "Assinatura v2 ausente"
        assert "Verified using v3 scheme (APK Signature Scheme v3): true" in res.stdout, "Assinatura v3 ausente"
    print(f"Teste 5 Aprovado: Ambos os APKs ({size_mb:.1f} MB) estao integros e com assinatura criptografica valida.")

if __name__ == "__main__":
    try:
        test_xml_syntax()
        test_absence_of_legacy_branding()
        test_canonical_terms()
        test_desktop_translations()
        test_apk_integrity_and_signature()
        print("\nTodos os 5 testes da suite de nacionalizacao foram APROVADOS com 100% de sucesso!")
    except Exception as e:
        print(f"\nFALHA NO TESTE: {e}", file=sys.stderr)
        sys.exit(1)

