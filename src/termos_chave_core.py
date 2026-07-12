from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from limpeza_texto import limpar_texto
from texto_utils import extrair_corpo_transcricao


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"


STOPWORDS = {
    "a",
    "acho",
    "ainda",
    "ai",
    "aí",
    "ante",
    "ao",
    "aos",
    "após",
    "aquela",
    "aquelas",
    "aquele",
    "aqueles",
    "aquilo",
    "as",
    "assim",
    "até",
    "através",
    "bem",
    "cada",
    "com",
    "como",
    "contra",
    "da",
    "daí",
    "das",
    "de",
    "dela",
    "dele",
    "deles",
    "demais",
    "dentro",
    "depois",
    "desde",
    "do",
    "dos",
    "e",
    "ela",
    "elas",
    "ele",
    "eles",
    "em",
    "então",
    "entre",
    "era",
    "essa",
    "essas",
    "esse",
    "esses",
    "esta",
    "estar",
    "estava",
    "este",
    "eu",
    "fora",
    "foi",
    "gente",
    "isso",
    "isto",
    "já",
    "lá",
    "mais",
    "mas",
    "mediante",
    "meio",
    "meu",
    "meus",
    "minha",
    "minhas",
    "muito",
    "muitos",
    "na",
    "não",
    "nas",
    "né",
    "no",
    "nos",
    "nossa",
    "num",
    "numa",
    "o",
    "os",
    "ou",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "perante",
    "pra",
    "porque",
    "por",
    "quando",
    "que",
    "se",
    "sem",
    "ser",
    "são",
    "só",
    "sob",
    "sobre",
    "também",
    "tem",
    "ter",
    "tipo",
    "trás",
    "tá",
    "um",
    "uma",
    "umas",
    "uns",
    "vai",
    "você",
    "vocês",
    "é",
}


PRONOMES = {
    "algum",
    "alguém",
    "alguma",
    "algumas",
    "alguns",
    "certa",
    "certas",
    "certo",
    "certos",
    "cuja",
    "cujas",
    "cujo",
    "cujos",
    "mesma",
    "mesmas",
    "mesmo",
    "mesmos",
    "nenhum",
    "nenhuma",
    "nenhumas",
    "nenhuns",
    "nós",
    "outra",
    "outras",
    "outro",
    "outros",
    "qual",
    "quaisquer",
    "quais",
    "qualquer",
    "quem",
    "seu",
    "seus",
    "sua",
    "suas",
    "tais",
    "tal",
    "teu",
    "teus",
    "toda",
    "todas",
    "todo",
    "todos",
    "tua",
    "tuas",
    "vós",
    "vosso",
    "vossos",
    "vossa",
    "vossas",
}


PALAVRAS_INFORMAIS = {
    "aham",
    "beleza",
    "caramba",
    "cara",
    "curti",
    "eita",
    "enfim",
    "galera",
    "hum",
    "mano",
    "massa",
    "poxa",
    "sabe",
    "saca",
    "sacou",
    "show",
    "suave",
    "tranquilo",
    "viu",
    "véi",
    "ué",
}


VERBOS_COMUNS = {
    "acha",
    "achando",
    "achar",
    "acontece",
    "acontecer",
    "aparece",
    "chama",
    "chamamos",
    "chamar",
    "chega",
    "chegar",
    "chegou",
    "coloca",
    "colocar",
    "conta",
    "contar",
    "começa",
    "começar",
    "consegue",
    "conseguir",
    "define",
    "definir",
    "diz",
    "dizer",
    "disse",
    "dando",
    "dar",
    "deu",
    "dá",
    "entende",
    "entender",
    "entendendo",
    "explica",
    "explicar",
    "falando",
    "falar",
    "falou",
    "fala",
    "fazer",
    "feito",
    "ficaram",
    "fica",
    "ficar",
    "ficou",
    "haver",
    "houve",
    "há",
    "importa",
    "importar",
    "leia",
    "lembra",
    "lembrar",
    "lê",
    "lendo",
    "mostra",
    "mostrar",
    "olha",
    "olhando",
    "olhar",
    "passa",
    "passar",
    "pega",
    "pegar",
    "pensa",
    "pensando",
    "pensar",
    "permite",
    "permitir",
    "pode",
    "podem",
    "poder",
    "precisa",
    "precisar",
    "quer",
    "representa",
    "representar",
    "saber",
    "sendo",
    "serão",
    "seria",
    "será",
    "significa",
    "significar",
    "temos",
    "tendo",
    "tinham",
    "tinha",
    "trata",
    "tratar",
    "têm",
    "usar",
    "vamos",
    "vem",
    "vendo",
    "ver",
    "vindo",
    "vir",
    "vão",
    "estão",
    "estavam",
    "estava",
    "foram",
}


SUFIXOS_VERBAIS = (
    "ando",
    "endo",
    "indo",
    "aria",
    "eram",
    "iram",
    "avam",
    "asse",
    "esse",
    "isse",
)


def termo_relevante(palavra):
    if len(palavra) < 4:
        return False
    if palavra in STOPWORDS or palavra in PRONOMES or palavra in PALAVRAS_INFORMAIS or palavra in VERBOS_COMUNS:
        return False
    if palavra.isnumeric():
        return False
    if palavra.endswith(SUFIXOS_VERBAIS):
        return False
    return True


def gerar_termos_chave(conteudo_transcricao, arquivo_analisado, sufixo=None):
    RESULTADOS_DIR.mkdir(exist_ok=True)

    texto = limpar_texto(extrair_corpo_transcricao(conteudo_transcricao))
    palavras_filtradas = [
        palavra for palavra in texto.split() if termo_relevante(palavra)
    ]

    contagem = Counter(palavras_filtradas)
    total_palavras = len(palavras_filtradas)
    palavras_unicas = len(contagem)
    top_termos = contagem.most_common(12)

    agora = datetime.now()
    data = agora.strftime("%d/%m/%Y")
    hora = agora.strftime("%H:%M:%S")
    timestamp = agora.strftime("%Y%m%d_%H%M%S")

    sufixo_nome = f"{sufixo}_{timestamp}" if sufixo else timestamp

    if top_termos:
        palavras = [palavra for palavra, _ in top_termos]
        frequencias = [qtd for _, qtd in top_termos]

        plt.figure(figsize=(9, 5))
        plt.bar(palavras, frequencias, color="#2563eb")
        plt.title("Termos-chave mais frequentes")
        plt.xlabel("Termos")
        plt.ylabel("Frequência")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(RESULTADOS_DIR / f"grafico_palavras_{sufixo_nome}.png", dpi=140)
        plt.close()

    arquivo_saida = RESULTADOS_DIR / f"palavras_chave_{sufixo_nome}.txt"
    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - TERMOS-CHAVE\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {data}\n")
        arquivo.write(f"Hora: {hora}\n\n")
        arquivo.write(f"Arquivo analisado: {arquivo_analisado}\n\n")
        arquivo.write(f"Total de termos analisados: {total_palavras}\n")
        arquivo.write(f"Termos únicos: {palavras_unicas}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("TOP 12 TERMOS-CHAVE\n")
        arquivo.write("=" * 60 + "\n\n")

        for palavra, qtd in top_termos:
            arquivo.write(f"{palavra}: {qtd}\n")

    linhas = [f"{palavra}: {qtd}" for palavra, qtd in top_termos]
    return {
        "arquivo": arquivo_saida,
        "total": total_palavras,
        "unicos": palavras_unicas,
        "linhas": linhas,
    }
