from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_PADRAO = BASE_DIR / "audio" / "aula.wav"
RESULTADOS_DIR = BASE_DIR / "resultados"


def gerar_fft(audio_path=None, sufixo=None):
    audio_path = Path(audio_path) if audio_path else AUDIO_PADRAO
    fs, audio = wavfile.read(str(audio_path))

    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    audio = audio.astype(np.float32)
    audio = audio - np.mean(audio)

    fft = np.fft.rfft(audio)
    freq = np.fft.rfftfreq(len(audio), d=1 / fs)
    magnitude = np.abs(fft)

    plt.figure(figsize=(10, 5))
    plt.plot(freq, magnitude)
    plt.xlabel("Frequência (Hz)")
    plt.ylabel("Magnitude")
    plt.title("Espectro da voz")
    plt.tight_layout()

    RESULTADOS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"espectro_{sufixo}_{timestamp}.png" if sufixo else f"espectro_{timestamp}.png"
    arquivo_saida = RESULTADOS_DIR / nome

    plt.savefig(arquivo_saida)
    plt.close()

    return arquivo_saida


if __name__ == "__main__":
    print("Taxa de amostragem e shape do áudio:")
    fs, audio = wavfile.read(str(AUDIO_PADRAO))
    print("Taxa de amostragem:", fs)
    print("Shape:", audio.shape)

    arquivo_saida = gerar_fft()
    print(f"Imagem salva em:\n{arquivo_saida}")
