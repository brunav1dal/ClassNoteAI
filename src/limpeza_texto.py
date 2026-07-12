import re


def limpar_texto(texto):
    texto = texto.replace("=" * 60, " ")
    texto = re.sub(r"[^\w\sÀ-ÿ]", " ", texto)
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()
