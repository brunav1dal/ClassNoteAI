from pathlib import Path

from scipy.io import wavfile
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
fs, audio = wavfile.read(str(BASE_DIR / "audio" / "aula.wav"))

plt.plot(audio)

plt.title("Sinal de Voz")
plt.xlabel("Amostras")
plt.ylabel("Amplitude")

plt.show()