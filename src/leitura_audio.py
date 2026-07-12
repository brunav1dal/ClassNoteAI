from pathlib import Path

from scipy.io import wavfile


BASE_DIR = Path(__file__).resolve().parent.parent
arquivo_audio = BASE_DIR / "audio" / "aula.wav"

fs, audio = wavfile.read(str(arquivo_audio))

print("Taxa de amostragem:", fs)
print("Número de amostras:", len(audio))
