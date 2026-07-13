from faster_whisper import WhisperModel

# Isso valida se o modelo carrega corretamente na CPU com 8-bit
try:
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("🚀 Faster-Whisper instalado e configurado com sucesso para CPU!")
except Exception as e:
    print(f"❌ Ocorreu um erro na configuração: {e}")