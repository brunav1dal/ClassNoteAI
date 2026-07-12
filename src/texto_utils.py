MARCADORES_TRANSCRICAO = [
    "TRANSCRIÇÃO CORRIGIDA",
    "TRANSCRIÇÃO",
    "TRANSCRIÃ‡ÃƒO CORRIGIDA",
    "TRANSCRIÃ‡ÃƒO",
]


def extrair_corpo_transcricao(conteudo):
    texto = conteudo

    for marcador in MARCADORES_TRANSCRICAO:
        if marcador in texto:
            texto = texto.split(marcador)[-1]
            break

    linhas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if set(linha) == {"="}:
            continue
        linhas.append(linha)

    return " ".join(linhas).strip()


def limitar_texto(texto, max_palavras=3500):
    palavras = texto.split()
    if len(palavras) <= max_palavras:
        return texto
    return " ".join(palavras[:max_palavras])
