# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Modulo Core de Download de Midias para o Conexao Movel.
Orquestra o yt-dlp e ffmpeg de forma isolada, resiliente e assincrona.
Contem sanitizacao rigorosa de URLs, prevencao contra Command e Option Injection,
e validacao estrita de caminhos contra Path Traversal.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",
})


def validate_download_url(url: str) -> str:
    """Valida e sanitiza a URL de midia contra injecoes e requisicoes SSRF."""
    if not url or not isinstance(url, str):
        raise ValueError("URL invalida: parametro ausente ou nao textual.")

    url_clean = url.strip()
    if len(url_clean) > 4096:
        raise ValueError("URL invalida: comprimento excede 4096 caracteres.")

    if any(c.isspace() or ord(c) < 32 for c in url_clean):
        raise ValueError("URL invalida: caracteres de espaco ou controle nao sao permitidos.")

    parsed = urlparse(url_clean)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError("URL invalida: esquema nao suportado. Utilize apenas http:// ou https://.")

    netloc = parsed.netloc
    if not netloc or "@" in netloc:
        raise ValueError("URL invalida: autoridade ausente ou credenciais embutidas.")

    hostname = (parsed.hostname or "").lower().strip("[]")
    if not hostname:
        raise ValueError("URL invalida: nome de host ausente.")

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError("URL invalida: enderecos de rede local e metadados internos sao bloqueados.")

    return url_clean


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Verifica se o caminho de destino reside estritamente dentro da pasta base."""
    try:
        real_base = os.path.realpath(base_dir)
        real_target = os.path.realpath(target_path)
        return os.path.commonpath([real_base, real_target]) == real_base
    except Exception:
        return False


def get_yt_dlp_binary() -> str:
    """Localiza o binario yt-dlp seguro no ambiente do usuario ou sistema."""
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
        self.output_dir = os.path.realpath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_active_downloads_count(self) -> int:
        """Retorna o numero de tarefas ativas em download no momento."""
        with self._lock:
            return sum(1 for t in self.active_tasks.values() if t.get("status") == "downloading")

    def inspect_url(self, url: str) -> Dict[str, Any]:
        """Extrai metadados do video de forma rapida e sem baixar o arquivo."""
        try:
            valid_url = validate_download_url(url)
        except ValueError as err:
            return {"success": False, "error": str(err)}

        try:
            yt_bin = get_yt_dlp_binary()
        except FileNotFoundError as err:
            return {"success": False, "error": str(err)}

        cmd = [
            yt_bin,
            "--dump-json",
            "--no-playlist",
            "--no-warnings",
            "--socket-timeout", "10",
            "--",
            valid_url,
        ]

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20,
            )
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
                "webpage_url": data.get("webpage_url", valid_url),
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
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Inicia um download assincrono em segundo plano com validacao estrita."""
        try:
            valid_url = validate_download_url(url)
        except ValueError as err:
            return {"success": False, "error": str(err)}

        clean_task_id = (task_id or "").strip()
        if not clean_task_id or not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", clean_task_id):
            return {"success": False, "error": "Identificador task_id invalido."}

        clean_format = (media_format or "video").lower()
        if clean_format not in ["audio", "video", "both"]:
            clean_format = "video"

        clean_dest = (destination or "pc").lower()
        if clean_dest not in ["pc", "phone", "both"]:
            clean_dest = "pc"

        try:
            yt_bin = get_yt_dlp_binary()
        except FileNotFoundError as err:
            return {"success": False, "error": str(err)}

        task_data = {
            "id": clean_task_id,
            "url": valid_url,
            "format": clean_format,
            "destination": clean_dest,
            "device_id": str(device_id)[:128],
            "status": "downloading",
            "progress": 0.0,
            "speed": "Iniciando...",
            "eta": "--:--",
            "title": "Baixando midia...",
            "generated_files": [],
            "error": None,
            "started_at": time.time(),
            "completed_at": None,
        }

        with self._lock:
            self.active_tasks[clean_task_id] = task_data

        thread = threading.Thread(
            target=self._run_download_thread,
            args=(clean_task_id, yt_bin, valid_url, clean_format, on_progress),
            daemon=True,
        )
        thread.start()

        return {"success": True, "task_id": clean_task_id}

    def _run_download_thread(
        self,
        task_id: str,
        yt_bin: str,
        url: str,
        media_format: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]],
    ):
        """Thread executora com streaming de progresso e filtragem de arquivos seguros."""
        try:
            if media_format == "audio":
                raw_files = self._download_audio(task_id, yt_bin, url, on_progress)
            elif media_format == "video":
                raw_files = self._download_video(task_id, yt_bin, url, on_progress)
            else:
                raw_files = self._download_video_and_extract_audio(task_id, yt_bin, url, on_progress)

            # Filtragem estrita contra Path Traversal em arquivos gerados
            safe_files = [f for f in raw_files if is_safe_path(self.output_dir, f)]

            with self._lock:
                task = self.active_tasks.get(task_id)
                if task:
                    task["status"] = "completed"
                    task["progress"] = 100.0
                    task["speed"] = "Concluido"
                    task["eta"] = "00:00"
                    task["generated_files"] = safe_files
                    task["completed_at"] = time.time()
                    if safe_files:
                        task["title"] = os.path.basename(safe_files[0])
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
        progress_offset: float = 0.0,
    ) -> List[str]:
        """Executa o comando yt-dlp capturando linhas de progresso e caminhos seguros."""
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
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

            for pat in (dest_pattern, merge_pattern, already_pattern):
                match = pat.search(line_str)
                if match:
                    candidate = match.group(1).strip()
                    if os.path.exists(candidate) and is_safe_path(self.output_dir, candidate):
                        if candidate not in generated_files:
                            generated_files.append(candidate)

        proc.wait()
        if proc.returncode != 0 and proc.returncode != -15:
            raise RuntimeError(f"O processo de download falhou com codigo {proc.returncode}")

        if not generated_files:
            generated_files = self._find_recently_modified_files(30)

        return generated_files

    def _download_audio(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        out_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        cmd = [
            yt_bin,
            "--newline",
            "--no-playlist",
            "--no-warnings",
            "--restrict-filenames",
            "--windows-filenames",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", out_template,
            "--",
            url,
        ]
        return self._execute_yt_dlp_cmd(task_id, cmd, on_progress)

    def _download_video(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        out_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        cmd = [
            yt_bin,
            "--newline",
            "--no-playlist",
            "--no-warnings",
            "--restrict-filenames",
            "--windows-filenames",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", out_template,
            "--",
            url,
        ]
        return self._execute_yt_dlp_cmd(task_id, cmd, on_progress)

    def _download_video_and_extract_audio(self, task_id: str, yt_bin: str, url: str, on_progress) -> List[str]:
        video_files = self._download_video(task_id, yt_bin, url, on_progress)
        if not video_files:
            raise RuntimeError("Nenhum arquivo de video foi gerado na fase 1.")

        main_video = video_files[0]
        if not is_safe_path(self.output_dir, main_video):
            raise RuntimeError("Caminho de video inseguro detectado.")

        base, _ = os.path.splitext(main_video)
        audio_out = f"{base}.mp3"

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
            audio_out,
        ]

        res = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0 or not is_safe_path(self.output_dir, audio_out):
            return video_files

        return [main_video, audio_out]

    def _find_recently_modified_files(self, seconds: int = 30) -> List[str]:
        now = time.time()
        res = []
        try:
            for f in os.listdir(self.output_dir):
                full = os.path.join(self.output_dir, f)
                if os.path.isfile(full) and is_safe_path(self.output_dir, full):
                    if (now - os.path.getmtime(full)) <= seconds:
                        res.append(full)
        except Exception:
            pass
        return res

    def cancel_download(self, task_id: str) -> bool:
        """Cancela uma tarefa de download ativa."""
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
        """Consulta o status atual de uma tarefa."""
        with self._lock:
            return self.active_tasks.get(task_id)

    def get_recent_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Recupera o historico recente ordenado de downloads."""
        with self._lock:
            tasks = list(self.active_tasks.values())
        tasks.sort(key=lambda t: t.get("started_at", 0), reverse=True)
        return tasks[:limit]
