#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Gerenciador de Simulacao e Testes Multiplataforma (Docker/KVM).
Permite iniciar, inspecionar e encerrar ambientes simulados de Android e Windows.
"""

import os
import sys
import argparse
import subprocess
import time
import json
from typing import Dict, Any, Optional

COMPOSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-compose.yml")

PRESETS = {
    "phone": {
        "width": 1080,
        "height": 2400,
        "dpi": 420,
        "description": "Smartphone moderno (aspecto 20:9, densidade xxhdpi)",
    },
    "tablet": {
        "width": 1600,
        "height": 2560,
        "dpi": 320,
        "description": "Tablet 10 polegadas (aspecto 16:10, densidade xhdpi)",
    },
    "compact": {
        "width": 720,
        "height": 1600,
        "dpi": 280,
        "description": "Smartphone basico de entrada (aspecto 20:9, densidade hdpi)",
    },
}

def run_command(cmd: list, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        check=check,
    )

def check_kvm_support() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)

def check_docker_support() -> bool:
    res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0

def start_mobile_simulation(preset_name: str = "phone", detached: bool = True) -> bool:
    preset = PRESETS.get(preset_name, PRESETS["phone"])
    env = dict(os.environ)
    env["SIM_WIDTH"] = str(preset["width"])
    env["SIM_HEIGHT"] = str(preset["height"])
    env["SIM_DPI"] = str(preset["dpi"])

    print(f"Iniciando simulacao Mobile Android ({preset_name}: {preset['width']}x{preset['height']} @ {preset['dpi']}dpi)...")
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "--profile", "mobile", "up"]
    if detached:
        cmd.append("-d")
    
    res = subprocess.run(cmd, env=env)
    return res.returncode == 0

def start_windows_simulation(version: str = "11", detached: bool = True) -> bool:
    env = dict(os.environ)
    env["WIN_VERSION"] = version

    print(f"Iniciando simulacao Desktop Windows {version} via KVM...")
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "--profile", "windows", "up"]
    if detached:
        cmd.append("-d")

    res = subprocess.run(cmd, env=env)
    return res.returncode == 0

def stop_simulation(profile: str = "all") -> bool:
    print(f"Encerrando contêineres de simulacao ({profile})...")
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "--profile", profile, "down"]
    res = subprocess.run(cmd)
    return res.returncode == 0

def status_simulation() -> Dict[str, Any]:
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "--profile", "all", "ps", "--format", "json"]
    try:
        res = run_command(cmd)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        services = []
        for line in lines:
            try:
                services.append(json.loads(line))
            except Exception:
                pass
        return {"active": len(services) > 0, "services": services}
    except Exception as e:
        return {"active": False, "error": str(e), "services": []}

def check_adb_ready(host: str = "127.0.0.1", port: int = 5555, timeout_sec: int = 20) -> bool:
    target = f"{host}:{port}"
    start = time.time()
    while time.time() - start < timeout_sec:
        res = subprocess.run(["adb", "connect", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "connected to" in res.stdout.lower() or "already connected" in res.stdout.lower():
            return True
        time.sleep(2)
    return False

def main():
    parser = argparse.ArgumentParser(description="Orquestrador de Simulacao Docker para Testes Multiplataforma")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponiveis")

    start_parser = subparsers.add_parser("start", help="Inicia uma instancia simulada")
    start_parser.add_argument("target", choices=["mobile", "windows", "all"], help="Alvo da simulacao")
    start_parser.add_argument("--preset", choices=list(PRESETS.keys()), default="phone", help="Perfil de tela mobile")
    start_parser.add_argument("--win-version", choices=["10", "11"], default="11", help="Versao do Windows")

    stop_parser = subparsers.add_parser("stop", help="Encerra instancias simuladas")
    stop_parser.add_argument("target", choices=["mobile", "windows", "all"], default="all", nargs="?")

    subparsers.add_parser("status", help="Exibe status dos servicos simulados")
    subparsers.add_parser("check", help="Valida suporte KVM e Docker no sistema host")

    args = parser.parse_args()

    if args.command == "check":
        kvm = check_kvm_support()
        doc = check_docker_support()
        print(f"Suporte KVM (/dev/kvm): {'ATIVO E ACESSIVEL' if kvm else 'INDISPONIVEL'}")
        print(f"Suporte Docker: {'ATIVO E OPERACIONAL' if doc else 'INATIVO'}")
        sys.exit(0 if (kvm and doc) else 1)

    elif args.command == "start":
        if not check_kvm_support():
            print("Aviso: /dev/kvm nao esta acessivel. A simulacao pode falhar ou degradar performance.", file=sys.stderr)
        if args.target in ["mobile", "all"]:
            start_mobile_simulation(preset_name=args.preset)
        if args.target in ["windows", "all"]:
            start_windows_simulation(version=args.win_version)

    elif args.command == "stop":
        stop_simulation(profile=args.target)

    elif args.command == "status":
        st = status_simulation()
        print(json.dumps(st, indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

