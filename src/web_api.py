import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import threading
import traceback
import uuid
import wave
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from audio_utils import preparar_audio
from config_env import carregar_env
from correcao_texto import corrigir_transcricao
from fft_audio import gerar_fft
from resultados_utils import arquivo_mais_recente, ler_texto_recente, imagem_data_url
from resumo_ia import gerar_material_estudo
from termos_chave_core import gerar_termos_chave
from transcricao import transcrever


BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
AUDIO_DIR = BASE_DIR / "audio"
RESULTADOS_DIR = BASE_DIR / "resultados"
JOBS = {}
JOBS_LOCK = threading.Lock()
RETENCAO_JOBS = timedelta(hours=6)

carregar_env()


def salvar_upload(payload):
    nome = Path(payload.get("filename") or "audio").name
    conteudo_base64 = payload.get("contentBase64")
    if not conteudo_base64:
        raise ValueError("Arquivo nao enviado.")

    if "," in conteudo_base64:
        conteudo_base64 = conteudo_base64.split(",", 1)[1]

    dados = base64.b64decode(conteudo_base64)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = AUDIO_DIR / f"upload_web_{timestamp}_{nome}"
    AUDIO_DIR.mkdir(exist_ok=True)
    destino.write_bytes(dados)
    return destino, nome


def info_audio(audio_path, nome_original):
    with wave.open(str(audio_path), "rb") as audio:
        fs = audio.getframerate()
        canais = audio.getnchannels()
        amostras = audio.getnframes()
        duracao = amostras / fs

    return {
        "arquivoOriginal": nome_original,
        "arquivoProcessado": str(audio_path),
        "taxaAmostragem": fs,
        "canais": canais,
        "amostras": amostras,
        "duracao": round(duracao, 2),
    }


def atualizar_job(job_id, **campos):
    if not job_id:
        return

    with JOBS_LOCK:
        job = JOBS.setdefault(job_id, {})
        job.update(campos)
        job["atualizadoEm"] = datetime.now()


def obter_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return None
        return {chave: valor for chave, valor in job.items() if chave != "atualizadoEm"}


def limpar_jobs_antigos():
    limite = datetime.now() - RETENCAO_JOBS
    with JOBS_LOCK:
        expirados = [
            job_id
            for job_id, job in JOBS.items()
            if job.get("done") and job.get("atualizadoEm", datetime.now()) < limite
        ]
        for job_id in expirados:
            del JOBS[job_id]


def montar_resultado(audio_path, nome_original="Último processamento", logs=None, sufixo=None, since=None):
    logs = logs or []

    try:
        audio = info_audio(audio_path, nome_original)
    except Exception as erro:
        audio = {
            "arquivoOriginal": nome_original,
            "erro": f"Não foi possível ler informações do áudio: {erro}",
        }

    padrao_transcricao = f"transcricao_corrigida_{sufixo}_*.txt" if sufixo else "transcricao_corrigida_*.txt"
    padrao_material = f"material_estudo_{sufixo}_*.txt" if sufixo else "material_estudo_*.txt"
    padrao_termos = f"palavras_chave_{sufixo}_*.txt" if sufixo else "palavras_chave_*.txt"
    padrao_fft = f"espectro_{sufixo}_*.png" if sufixo else "espectro_*.png"
    padrao_grafico = f"grafico_palavras_{sufixo}_*.png" if sufixo else "grafico_palavras_*.png"

    return {
        "audio": audio,
        "transcricao": ler_texto_recente(padrao_transcricao, since=since),
        "material": ler_texto_recente(padrao_material, since=since),
        "termos": ler_texto_recente(padrao_termos, since=since),
        "fftImagem": imagem_data_url(padrao_fft, since=since),
        "termosImagem": imagem_data_url(padrao_grafico, since=since),
        "logs": "\n".join(logs),
    }


def publicar_resultado_parcial(job_id, audio_path, nome_original, logs, sufixo=None, since=None):
    if not job_id:
        return

    try:
        atualizar_job(
            job_id,
            result=montar_resultado(audio_path, nome_original, logs, sufixo=sufixo, since=since),
        )
    except Exception as erro:
        atualizar_job(job_id, partialError=f"Falha ao montar resultado parcial: {erro}")


def processar(payload, job_id=None):
    origem, nome_original = salvar_upload(payload)
    inicio_job = datetime.now().timestamp()
    whisper_model = payload.get("whisperModel") or "tiny"
    ia_provider = payload.get("aiProvider") or "auto"
    max_seconds = payload.get("maxSeconds")

    audio_destino = AUDIO_DIR / (f"aula_{job_id}.wav" if job_id else "aula.wav")

    logs = []
    atualizar_job(job_id, progress=8, status="Preparando áudio")
    logs.append(preparar_audio(origem, audio_destino, max_seconds=max_seconds))
    publicar_resultado_parcial(job_id, audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    atualizar_job(job_id, progress=18, status="Rodando FFT e Whisper em paralelo")
    progresso_maximo = [18]

    def avancar_progresso(valor, status):
        progresso_maximo[0] = max(valor, progresso_maximo[0])
        atualizar_job(job_id, progress=progresso_maximo[0], status=status)

    def reportar_progresso_whisper(fracao):
        valor = 18 + int(fracao * (56 - 18))
        avancar_progresso(valor, "Transcrevendo com Whisper")

    tarefas = {
        "FFT": lambda: gerar_fft(audio_path=audio_destino, sufixo=job_id),
        "Whisper": lambda: transcrever(
            audio_path=audio_destino,
            whisper_model=whisper_model,
            sufixo=job_id,
            progress_callback=reportar_progresso_whisper,
        ),
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = {executor.submit(tarefa): nome for nome, tarefa in tarefas.items()}
        concluidas = 0
        for futuro in as_completed(futuros):
            nome = futuros[futuro]
            futuro.result()
            logs.append(f"{nome} concluído.")
            concluidas += 1
            progresso = 34 if concluidas == 1 else 56
            avancar_progresso(progresso, f"{nome} concluído")
            publicar_resultado_parcial(job_id, audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    avancar_progresso(66, "Corrigindo transcrição")
    corrigir_transcricao(sufixo=job_id, ia_provider=ia_provider)
    logs.append("Transcrição corrigida.")
    publicar_resultado_parcial(job_id, audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    atualizar_job(job_id, progress=78, status="Extraindo termos-chave")
    padrao_corrigida = f"transcricao_corrigida_{job_id}_*.txt" if job_id else "transcricao_corrigida_*.txt"
    transcricao_corrigida = arquivo_mais_recente(padrao_corrigida)
    if not transcricao_corrigida:
        raise RuntimeError("Nenhuma transcrição encontrada para extrair termos-chave.")

    conteudo_transcricao = transcricao_corrigida.read_text(encoding="utf-8")
    termos = gerar_termos_chave(conteudo_transcricao, transcricao_corrigida.name, sufixo=job_id)
    logs.append(f"Termos-chave gerados: {termos['total']} termos analisados.")
    publicar_resultado_parcial(job_id, audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    atualizar_job(job_id, progress=92, status="Gerando material de estudo")
    gerar_material_estudo(sufixo=job_id, ia_provider=ia_provider)
    logs.append("Material de estudo gerado.")
    publicar_resultado_parcial(job_id, audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    atualizar_job(job_id, progress=96, status="Montando resposta final")
    resultado = montar_resultado(audio_destino, nome_original, logs, sufixo=job_id, since=inicio_job)

    try:
        if origem.exists():
            origem.unlink()
    except OSError:
        pass

    return resultado


def executar_job(job_id, payload):
    try:
        atualizar_job(job_id, ok=True, done=False, progress=1, status="Recebido pela API")
        resultado = processar(payload, job_id)
        atualizar_job(
            job_id,
            ok=True,
            done=True,
            progress=100,
            status="Processamento concluído",
            result=resultado,
        )
    except Exception as erro:
        atualizar_job(
            job_id,
            ok=False,
            done=True,
            progress=0,
            status="Erro no processamento",
            error=str(erro),
            traceback=traceback.format_exc(),
        )
    finally:
        limpar_jobs_antigos()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        caminho = urlparse(self.path)
        if caminho.path == "/api/latest":
            self.enviar_json(
                {
                    "ok": True,
                    "result": montar_resultado(
                        AUDIO_DIR / "aula.wav",
                        "Último processamento salvo",
                        ["Resultado carregado da pasta resultados."],
                    ),
                }
            )
            return

        if caminho.path == "/api/status":
            params = parse_qs(caminho.query)
            job_id = (params.get("jobId") or [None])[0]
            job = obter_job(job_id)
            if not job:
                self.enviar_json({"ok": False, "error": "Job não encontrado."}, 404)
                return

            self.enviar_json({"ok": True, "job": job})
            return

        super().do_GET()

    def do_POST(self):
        caminho = urlparse(self.path).path
        if caminho != "/api/process":
            self.enviar_json({"ok": False, "error": "Rota nao encontrada."}, 404)
            return

        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            corpo = self.rfile.read(tamanho)
            payload = json.loads(corpo.decode("utf-8"))
            job_id = uuid.uuid4().hex
            atualizar_job(
                job_id,
                ok=True,
                done=False,
                progress=0,
                status="Aguardando início",
            )
            thread = threading.Thread(
                target=executar_job,
                args=(job_id, payload),
                daemon=True,
            )
            thread.start()
            self.enviar_json({"ok": True, "jobId": job_id})
        except Exception as erro:
            self.enviar_json({"ok": False, "error": str(erro)}, 500)

    def enviar_json(self, dados, status=200):
        conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)


def main():
    host = "127.0.0.1"
    porta = int(os.environ.get("CLASSNOTE_WEB_PORT", "8000"))
    servidor = ThreadingHTTPServer((host, porta), Handler)
    print(f"ClassNote AI web rodando em http://{host}:{porta}")
    print("Pressione Ctrl+C para encerrar.")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
