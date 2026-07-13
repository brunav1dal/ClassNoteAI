import os
import shutil
import subprocess
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"

FFMPEG_FALLBACK = Path(
    r"C:\Users\Bruna\Downloads\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
)


def encontrar_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    caminho_env = os.environ.get("CLASSNOTE_FFMPEG_PATH")
    if caminho_env and Path(caminho_env).exists():
        return caminho_env

    if FFMPEG_FALLBACK.exists():
        return str(FFMPEG_FALLBACK)

    return None


def adicionar_ffmpeg_ao_path(env):
    ffmpeg = encontrar_ffmpeg()
    if not ffmpeg:
        return env

    pasta_ffmpeg = str(Path(ffmpeg).parent)
    paths = env.get("PATH", "").split(os.pathsep)
    if pasta_ffmpeg not in paths:
        env["PATH"] = pasta_ffmpeg + os.pathsep + env.get("PATH", "")

    return env


def preparar_audio(origem, destino, max_seconds=None, timeout=600, medidor=None):
    destino = Path(destino)
    destino.parent.mkdir(exist_ok=True)
    origem = Path(origem)
    ffmpeg = encontrar_ffmpeg()

    if ffmpeg:
        inicio = time.perf_counter()
        comando = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(origem),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-af",
            "silenceremove=start_periods=1:start_duration=0.35:start_threshold=-45dB:stop_periods=-1:stop_duration=0.8:stop_threshold=-45dB,loudnorm=I=-18:TP=-2:LRA=11",
            "-sample_fmt",
            "s16",
        ]
        if max_seconds:
            comando.extend(["-t", str(max_seconds)])
        comando.append(str(destino))
        subprocess.run(
            comando,
            check=True,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if medidor:
            medidor.registrar("FFmpeg - conversão e pré-processamento", time.perf_counter() - inicio)
        detalhes = "WAV mono, 16 kHz, 16 bits, silêncio removido e volume normalizado"
        if max_seconds:
            detalhes += f", limitado a {max_seconds}s"
        return f"Audio preparado em {detalhes}."

    if origem.suffix.lower() != ".wav":
        raise RuntimeError(
            "FFmpeg nao encontrado. Instale o FFmpeg, defina CLASSNOTE_FFMPEG_PATH "
            "ou envie um arquivo WAV."
        )

    if origem.resolve() != destino.resolve():
        inicio = time.perf_counter()
        shutil.copy2(origem, destino)
        if medidor:
            medidor.registrar("Disco - cópia do áudio WAV", time.perf_counter() - inicio)
        return "Arquivo WAV copiado para processamento."

    return "Usando o arquivo WAV existente."
