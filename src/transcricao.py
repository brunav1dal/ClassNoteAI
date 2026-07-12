from datetime import datetime
import importlib
import os
import threading
from pathlib import Path

import numpy as np
from scipy.io import wavfile
import whisper

from audio_utils import adicionar_ffmpeg_ao_path

# whisper/__init__.py faz "from .transcribe import transcribe", o que sobrescreve
# o atributo whisper.transcribe (o submódulo) com a função de mesmo nome. Por isso
# não dá para usar "import whisper.transcribe as X" aqui - precisamos pegar o
# módulo real via importlib para conseguir substituir a tqdm usada internamente.
whisper_transcribe_module = importlib.import_module("whisper.transcribe")


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_PADRAO = BASE_DIR / "audio" / "aula.wav"
RESULTADOS_DIR = BASE_DIR / "resultados"

_MODELOS = {}
_MODELOS_LOCKS = {}
_MODELOS_LOCK_CRIACAO = threading.Lock()
_progresso_local = threading.local()
_patch_lock = threading.Lock()
_patch_contadores = 0


def obter_modelo(nome):
    if nome not in _MODELOS:
        print(f"Carregando modelo Whisper: {nome}")
        _MODELOS[nome] = whisper.load_model(nome)
    return _MODELOS[nome]


def obter_lock_do_modelo(nome):
    # model.transcribe() muta o cache interno (KV-cache) do próprio objeto do
    # modelo. Como o modelo é reaproveitado entre jobs (para não recarregar a
    # cada transcrição), duas transcrições concorrentes usando o MESMO modelo
    # corrompem esse estado e derrubam o processo. Um lock por modelo serializa
    # apenas transcrições que compartilham a mesma instância, sem bloquear
    # transcrições concorrentes que usem modelos diferentes.
    with _MODELOS_LOCK_CRIACAO:
        if nome not in _MODELOS_LOCKS:
            _MODELOS_LOCKS[nome] = threading.Lock()
        return _MODELOS_LOCKS[nome]


class _TqdmComCallback:
    """Substitui a tqdm.tqdm usada internamente por whisper.transcribe para
    repassar o progresso real (fração de frames processados) para quem chamou
    transcrever(), sem exigir mudanças na biblioteca whisper."""

    def __init__(self, total=None, *args, **kwargs):
        self.total = total or 0
        self.n = 0

    def update(self, n=1):
        self.n += n
        callback = getattr(_progresso_local, "callback", None)
        if callback and self.total:
            try:
                callback(min(self.n / self.total, 1.0))
            except Exception:
                pass

    def set_description(self, *args, **kwargs):
        pass

    def set_postfix(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _WhisperProgressoContexto:
    """Instala o hook de progresso apenas enquanto o bloco `with` está ativo.
    Usa contagem de referências porque FFT e Whisper podem rodar em threads
    simultâneas (ThreadPoolExecutor) e não devemos restaurar a tqdm original
    enquanto outra transcrição concorrente ainda estiver usando o hook."""

    def __init__(self, callback):
        self.callback = callback

    def __enter__(self):
        global _patch_contadores
        _progresso_local.callback = self.callback
        with _patch_lock:
            if _patch_contadores == 0:
                self._original = whisper_transcribe_module.tqdm.tqdm
                whisper_transcribe_module.tqdm.tqdm = _TqdmComCallback
            _patch_contadores += 1
        return self

    def __exit__(self, *exc_info):
        global _patch_contadores
        with _patch_lock:
            _patch_contadores -= 1
            if _patch_contadores == 0:
                whisper_transcribe_module.tqdm.tqdm = self._original
        _progresso_local.callback = None
        return False


def carregar_wav_rapido(caminho):
    fs, audio = wavfile.read(str(caminho))

    if fs != 16000:
        return str(caminho)

    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = audio.astype(np.float32)
        pico = np.max(np.abs(audio))
        if pico > 1:
            audio = audio / pico

    return audio


def transcrever(audio_path=None, whisper_model=None, sufixo=None, progress_callback=None):
    adicionar_ffmpeg_ao_path(os.environ)

    audio_path = Path(audio_path) if audio_path else AUDIO_PADRAO
    modelo_nome = (whisper_model or os.environ.get("CLASSNOTE_WHISPER_MODEL", "tiny")).strip() or "tiny"

    agora = datetime.now()
    data = agora.strftime("%d/%m/%Y")
    hora = agora.strftime("%H:%M:%S")
    timestamp = agora.strftime("%Y%m%d_%H%M%S")

    model = obter_modelo(modelo_nome)

    print("Carregando WAV preparado...")
    audio = carregar_wav_rapido(audio_path)

    print("Transcrevendo em português...")
    with obter_lock_do_modelo(modelo_nome), _WhisperProgressoContexto(progress_callback):
        resultado = model.transcribe(
            audio,
            language="pt",
            fp16=False,
            verbose=False,
            temperature=0,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
        )

    texto = resultado["text"].strip()

    RESULTADOS_DIR.mkdir(exist_ok=True)
    nome = f"transcricao_{sufixo}_{timestamp}.txt" if sufixo else f"transcricao_{timestamp}.txt"
    arquivo_saida = RESULTADOS_DIR / nome

    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - TRANSCRIÇÃO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {data}\n")
        arquivo.write(f"Hora: {hora}\n\n")
        arquivo.write(f"Modelo Whisper: {modelo_nome}\n")
        arquivo.write(f"Arquivo de áudio: {audio_path.name}\n")
        arquivo.write(f"Caminho: {audio_path}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("TRANSCRIÇÃO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto)

    return texto, arquivo_saida


if __name__ == "__main__":
    texto, arquivo_saida = transcrever()
    print("\nTRANSCRIÇÃO:")
    print(texto)
    print("\nArquivo salvo em:")
    print(arquivo_saida)
