# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Modulo Core de Download de Midias para o Conexao Movel.
Orquestra o yt-dlp e ffmpeg de forma isolada, resiliente e assincrona.
"""

import os
import re
import sys
import json
import time
import shutil
import threading
import subprocess
from typing import Dict, Any, Optional, List, Callable

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

def get_yt_dlp_binary() -> str:
    user_bin = os.path.expanduser("~/.local/bin/yt-dlp")
    if os.path.exists(user_bin) and os.access(user_bin, os.X_OK):
        return user_bin
    system_bin = shutil.which("yt-dlp")
    if system_bin:
        return system_bin
    raise FileNotFoundError("Binario yt-dlp nao encontrado no sistema.")

class MediaDownloader:
    """Gerencia inspecao de metadados e execucao de downloads de midia."""

    def __init__(self, output_dir: str = DOWNLOADS_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def inspect_url(self, url: str) -> Dict[str, Any]:
        """Extrai metadados do video de forma rapida e sem baixar o arquivo."""
        url = (url or "").strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            return {"success": False, "error": "URL invalida. Forneca um link http/https valido."}

        yt_bin = get_yt_dlp_binary()
        cmd = [
            yt_bin,
            "--dump-json",
            "--no-playlist",
            "--no-warnings",
            "--socket-timeout", "10",
            url
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if res.returncode != 0:
                err = res.stderr.strip() or "Falha ao extrair metadados do link."
                return {"success": False, "error": err}

            data = json.loads(res.stdout)
            return {
                "success": True,
                "title": data.get("title", "Midia sem titulo"),
                "uploader": data.get("uploader") or data.get("channel") or "Autor desconhecido",
                "duration": data.get("duration", 0),
                "thumbnail": data.get("thumbnail") or "",
                "extractor": data.get("extractor", "web"),
                "webpage_url": data.get("webpage_url", url)
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Tempo limite excedido ao inspecionar o link."}
        except Exception as e:
            return {"success": False, "error": f"Erro inesperado: {str(e)}"}

    def start_download(
        self,
        task_id: str,
        url: str,
        media_format: str = "video",
        destination: str = "pc",
        device_id: str = "",
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Inicia um download assincrono em segundo plano."""
        url = (url or "").strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            return {"success": False, "error": "URL invalida."}

        media_format = (media_format or "video").lower()
        if media_format not in ["audio", "video", "both"]:
            media_format = "video"

        destination = (destination or "pc").lower()
        if destination not in ["pc", "phone", "both"]:
            destination = "pc"

        yt_bin = get_yt_dlp_binary()

        # Estrutura de estado da tarefa
        task_data = {
            "id": task_id,
            "url": url,
            "format": media_format,
            "destination": destination,
            "device_id": device_id,
            "status": "downloading",
            "progress": 0.0,
            "speed": "Iniciando...",
            "eta": "--:--",
            "title": "Baixando midia...",
            "generated_files": [],
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }

        with self._lock:
            self.active_tasks[task_id] = task_data

        # Thread de execucao do download
        thread = threading.Thread(
            target=self._run_download_thread,
            args=(task_id, yt_bin, url, media_format, on_progress),
            daemon=True
        )
        thread.start()

        return {"success": True, "task_id": task_id}

    def _run_download_thread(
        self,
        task_id: str,
        yt_bin: str,
        url: str,
        media_format: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]]
    ):
        """Thread executora com streaming de progresso e tratamento para o modo 'both'."""
        try:
            if media_format == "audio":
                files = self._download_audio(task_id, yt_bin, url, on_progress)
            elif media_format == "video":
                files = self._download_video(task_id, yt_bin, url, on_progress)
            else: # both
                # No modo 'both', baixa o video com audio integrado e depois extrai a faixa MP3
                files = self._download_video_and_extract_audio(task_id, yt_bin, url, on_progress)

            with self._lock:
                task = self.active_tasks.get(task_id)
                if task:
                    task["status"] = "completed"
                    task["progress"] = 100.0
                    task["speed"] = "Concluido"
                    task["eta"] = "00:00"
                    task["generated_files"] = files
                    task["completed_at"] = time.time()
                    if files:
                        task["title"] = os.path.basename(files[0])
                    if on_progress:
                        on_progress(task)

        except Exception as e:
            with self._lock:
                task = self.active_tasks.get(task_id)
                if task:
                    task["status"] = "failed"
                    task["error"] = str(e)
                    task["completed_at"] = time.time()
                    if on_progress:
                        on_progress(task)
        finally:
            with self._lock:
                self.active_processes.pop(task_id, None)

    def _execute_yt_dlp_cmd(
        self,
        task_id: str,
        cmd: List[str],
        on_progress: Optional[Callable[[Dict[str, Any]], None]],
        progress_weight: float = 1.0,
        progress_offset: float = 0.0
    ) -> List[str]:
        """Executa o comando yt-dlp capturando linhas de progresso e arquivos gerados."""
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        with self._lock:
            self.active_processes[task_id] = proc

        generated_files = []
        progress_pattern = re.compile(r"(\d+(?:\.\d+)?)%")
        speed_pattern = re.compile(r"at\s+([0-9\.]+[kKMmGg]i?B/s)")
        eta_pattern = re.compile(r"ETA\s+([0-9:]+)")
        dest_pattern = re.compile(r"\[(?:download|Merger|ExtractAudio)\]\s+Destination:\s+(.+)")
        merge_pattern = re.compile(r"Merging formats into \"(.+)\"")
        already_pattern = re.compile(r"\[download\]\s+(.+)\s+has already been downloaded")

        for line in proc.stdout:
            line_str = line.strip()

            # Captura progresso
            p_match = progress_pattern.search(line_str)
            if p_match:
                raw_pct = float(p_match.group(1))
                norm_pct = round(progress_offset + (raw_pct * progress_weight), 1)
                speed = speed_pattern.search(line_str)
                eta = eta_pattern.search(line_str)

                with self._lock:
                    task = self.active_tasks.get(task_id)
                    if task:
                        task["progress"] = min(100.0, norm_pct)
                        if speed:
                            task["speed"] = speed.group(1)
                        if eta:
                            task["eta"] = eta.group(1)
                        if on_progress:
                            on_progress(task)

            # Captura caminho do arquivo de saida
            d_match = dest_pattern.search(line_str)
            if d_match:
                p = d_match.group(1).strip()
                if os.path.exists(p) and p not in generated_files:
                    generated_files.append(p)

            m_match = merge_pattern.search(line_str)
            if m_match:
                p = m_match.group(1).strip()
                if os.path.exists(p) and p not in generated_files:
                    generated_files.append(p)

            a_match = already_pattern.search(line_str)
            if a_match:
                p = a_match.group(1).strip()
                if os.path.exists(p) and p not in generated_files:
                    generated_files.append(p)

        proc.wait()
        if proc.returncode != 0 and proc.returncode != -15:
            raise RuntimeError(f"O processo de download falhou com codigo {proc.returncode}")

        # Varredura adicional no diretorio para capturar arquivos recem-criados se nao identificados por regex
        if not generated_files:
            generated_files = self._find_recently_modified_files(30)

        return generated_files

    def _download_audio(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        out_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        cmd = [
            yt_bin,
            "--newline",
            "--no-playlist",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", out_template,
            url
        ]
        return self._execute_yt_dlp_cmd(task_id, cmd, on_progress)

    def _download_video(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        out_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        cmd = [
            yt_bin,
            "--newline",
            "--no-playlist",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", out_template,
            url
        ]
        return self._execute_yt_dlp_cmd(task_id, cmd, on_progress)

    def _download_video_and_extract_audio(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        # Fase 1: Baixa o video MP4 (0% a 75% do progresso total)
        video_files = self._download_video(task_id, yt_bin, url, on_progress)
        if not video_files:
            raise RuntimeError("Nenhum arquivo de video foi gerado na fase 1.")

        main_video = video_files[0]
        base, _ = os.path.splitext(main_video)
        audio_out = f"{base}.mp3"

        # Fase 2: Extrai o audio MP3 320k via FFmpeg (75% a 100%)
        with self._lock:
            task = self.active_tasks.get(task_id)
            if task:
                task["progress"] = 80.0
                task["speed"] = "Extraindo MP3..."
                if on_progress:
                    on_progress(task)

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            audio_out
        ]

        res = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            return video_files

        return [main_video, audio_out]

    def _find_recently_modified_files(self, seconds: int = 30) -> List[str]:
        now = time.time()
        res = []
        try:
            for f in os.listdir(self.output_dir):
                full = os.path.join(self.output_dir, f)
                if os.path.isfile(full) and (now - os.path.getmtime(full)) <= seconds:
                    res.append(full)
        except Exception:
            pass
        return res

    def cancel_download(self, task_id: str) -> bool:
        with self._lock:
            proc = self.active_processes.get(task_id)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            task = self.active_tasks.get(task_id)
            if task:
                task["status"] = "cancelled"
                task["speed"] = "Cancelado"
                task["completed_at"] = time.time()
                return True
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.active_tasks.get(task_id)

    def get_recent_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = list(self.active_tasks.values())
        tasks.sort(key=lambda t: t.get("started_at", 0), reverse=True)
        return tasks[:limit]

