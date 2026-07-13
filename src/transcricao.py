from datetime import datetime
import os
import threading
import time
from pathlib import Path

from audio_utils import adicionar_ffmpeg_ao_path


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_PADRAO = BASE_DIR / "audio" / "aula.wav"
RESULTADOS_DIR = BASE_DIR / "resultados"
CACHE_MODELOS_DIR = BASE_DIR / ".cache"

_MODELO = None
_MODELO_LOCK = threading.Lock()


def obter_threads_ideais():
    """Usa os núcleos físicos estimados, evitando excesso de threads lógicas."""
    # No i7-8665U, 8 threads lógicas / 2 = 4 núcleos físicos para o CTranslate2.
    threads_ideais = (os.cpu_count() or 8) // 2
    return threads_ideais


def obter_modelo(medidor=None):
    """Carrega uma única instância do modelo base para reaproveitá-la entre áudios."""
    global _MODELO
    with _MODELO_LOCK:
        if _MODELO is None:
            inicio = time.perf_counter()
            # Evita gravar o modelo em um diretório global sem permissão no Windows.
            CACHE_MODELOS_DIR.mkdir(exist_ok=True)
            os.environ.setdefault("HF_HOME", str(CACHE_MODELOS_DIR))
            # O cache continua funcional sem links simbólicos ou Xet no Windows.
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            try:
                from faster_whisper import WhisperModel
            except ImportError as erro:
                raise RuntimeError(
                    "O pacote faster-whisper não está instalado. "
                    "Instale-o com: pip install faster-whisper"
                ) from erro

            print("Carregando faster-whisper base para CPU...")
            _MODELO = WhisperModel(
                "base",
                # Executa exclusivamente no processador, sem exigir GPU dedicada.
                device="cpu",
                # Usa quantização int8: menos RAM e melhor desempenho na CPU.
                compute_type="int8",
                # Usa núcleos físicos estimados e evita contenção do Hyper-Threading.
                cpu_threads=obter_threads_ideais(),
            )
            if medidor:
                medidor.registrar("Whisper - carregamento do modelo", time.perf_counter() - inicio)
    return _MODELO


def transcrever_audio(caminho_audio, progress_callback=None, medidor=None):
    """Transcreve um áudio local em português e devolve uma única string limpa."""
    adicionar_ffmpeg_ao_path(os.environ)
    caminho_audio = Path(caminho_audio)

    if not caminho_audio.is_file():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {caminho_audio}")

    if progress_callback:
        progress_callback(0.0)

    inicio_configuracao = time.perf_counter()
    segmentos, _ = obter_modelo(medidor=medidor).transcribe(
        str(caminho_audio),
        # Evita a detecção automática do idioma e acelera o início da transcrição.
        language="pt",
        # Busca limitada a 2 alternativas: reduz cálculo mantendo boa precisão em português.
        beam_size=2,
        condition_on_previous_text=False,
        # Ignora silêncio e ruído de fundo, reduzindo o trabalho total da CPU.
        vad_filter=True,
    )
    if medidor:
        medidor.registrar("Whisper - preparação da inferência", time.perf_counter() - inicio_configuracao)

    # `segmentos` é um iterador; juntar `segment.text` produz o texto final limpo.
    inicio_transcricao = time.perf_counter()
    texto = " ".join(segmento.text.strip() for segmento in segmentos if segmento.text.strip())
    if medidor:
        medidor.registrar("Whisper - transcrição + VAD", time.perf_counter() - inicio_transcricao)
    inicio_pos = time.perf_counter()
    texto = " ".join(texto.split())
    if medidor:
        medidor.registrar("Whisper - pós-processamento do texto", time.perf_counter() - inicio_pos)

    if progress_callback:
        progress_callback(1.0)

    return texto


def transcrever(audio_path=None, whisper_model=None, sufixo=None, progress_callback=None, medidor=None):
    """Mantém a integração do projeto e salva a transcrição produzida em disco.

    O argumento ``whisper_model`` é ignorado intencionalmente: a aplicação usa
    sempre o modelo ``base`` para o perfil local de CPU.
    """
    audio_path = Path(audio_path) if audio_path else AUDIO_PADRAO
    texto = transcrever_audio(audio_path, progress_callback=progress_callback, medidor=medidor)

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    nome = f"transcricao_{sufixo}_{timestamp}.txt" if sufixo else f"transcricao_{timestamp}.txt"
    RESULTADOS_DIR.mkdir(exist_ok=True)
    arquivo_saida = RESULTADOS_DIR / nome

    inicio_escrita = time.perf_counter()
    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - TRANSCRIÇÃO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {agora.strftime('%d/%m/%Y')}\n")
        arquivo.write(f"Hora: {agora.strftime('%H:%M:%S')}\n\n")
        arquivo.write(
            f"Modelo Whisper: base (faster-whisper, CPU int8, {obter_threads_ideais()} threads)\n"
        )
        arquivo.write(f"Arquivo de áudio: {audio_path.name}\n")
        arquivo.write(f"Caminho: {audio_path}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("TRANSCRIÇÃO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto)
    if medidor:
        medidor.registrar("Disco - escrita da transcrição", time.perf_counter() - inicio_escrita)

    return texto, arquivo_saida


if __name__ == "__main__":
    texto, arquivo_saida = transcrever()
    print("\nTRANSCRIÇÃO:")
    print(texto)
    print("\nArquivo salvo em:")
    print(arquivo_saida)
