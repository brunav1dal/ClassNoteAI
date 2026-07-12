import base64
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"


def arquivo_mais_recente(padrao, since=None, pasta=RESULTADOS_DIR):
    arquivos = list(pasta.glob(padrao))
    if since is not None:
        arquivos = [
            caminho for caminho in arquivos if caminho.stat().st_mtime >= since
        ]
    arquivos = sorted(arquivos, key=lambda caminho: caminho.stat().st_mtime, reverse=True)
    return arquivos[0] if arquivos else None


def ler_texto_recente(padrao, since=None):
    arquivo = arquivo_mais_recente(padrao, since=since)
    if not arquivo:
        return ""

    return arquivo.read_text(encoding="utf-8")


def imagem_data_url(padrao, since=None):
    arquivo = arquivo_mais_recente(padrao, since=since)
    if not arquivo:
        return ""

    conteudo = base64.b64encode(arquivo.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{conteudo}"
