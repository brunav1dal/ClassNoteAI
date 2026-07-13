import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from transcricao import obter_modelo


try:
    obter_modelo()
    print("Faster-Whisper instalado e configurado com sucesso para CPU.")
except Exception as erro:
    print(f"Erro na configuração do Faster-Whisper: {erro}")
