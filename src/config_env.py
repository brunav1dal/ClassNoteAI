import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


ARQUIVOS_ENV = (".env", "senha.env")


def carregar_env():
    for nome_arquivo in ARQUIVOS_ENV:
        arquivo_env = BASE_DIR / nome_arquivo
        if not arquivo_env.exists():
            continue

        for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue

            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")

            if chave and chave not in os.environ:
                os.environ[chave] = valor
