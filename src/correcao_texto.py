from datetime import datetime
from pathlib import Path
import time

from ia_utils import MODELO_GROQ, chamar_groq
from resultados_utils import arquivo_mais_recente
from texto_utils import extrair_corpo_transcricao, limitar_texto

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"

# Prompt estruturado para correção previsível pela Groq.
PROMPT_CORRECAO = """Você é um revisor de texto especializado em ajustar erros fonéticos de transcrições automáticas (áudio para texto) em português brasileiro.

Regras estritas:
1. Corrija apenas erros óbvios de ortografia, pontuação e palavras trocadas por sons parecidos.
2. Nunca adicione, mude o sentido, resuma ou parafraseie o texto. Mantenha as repetições e o estilo falado do aluno/professor.
3. Se uma palavra do texto soar parecida foneticamente com um dos "termos de referência" abaixo, mas estiver escrita de forma diferente ou estranha, corrija para o termo de referência — mesmo que a diferença pareça pequena.
4. Se não tiver certeza de um termo técnico ou palavra e ele não se relacionar com nenhum termo de referência, NÃO mude.
5. Responda APENAS com o texto corrigido. Sem introduções, sem notas, sem títulos.

Termos de referência já identificados nesta aula (nomes próprios e termos técnicos grafados corretamente em outros trechos; use-os para uniformizar palavras parecidas foneticamente):
{glossario}

Exemplo:
Texto original: "a gente vai focar nos gráfico de pitom pra criar o deste borde"
Texto corrigido: "A gente vai focar nos gráficos de Python pra criar o dashboard."

Texto original para corrigir:
"{texto}"
Texto corrigido:"""

# Prompt para levantar termos técnicos/nomes já grafados corretamente,
# usados como referência para uniformizar palavras foneticamente parecidas.
PROMPT_GLOSSARIO = """Leia a transcrição de aula abaixo e extraia os termos técnicos e nomes próprios que aparecem escritos de forma clara e consistente (ex: nomes de disciplinas, autores, ferramentas, siglas, conceitos específicos do assunto).

Regras:
1. Liste no máximo 20 termos, um por linha, sem numeração, marcadores ou explicações.
2. Ignore palavras comuns do português.
3. Se não houver termos técnicos ou nomes próprios claros, responda apenas "nenhum".

Texto:
"{texto}"

Lista de termos:"""


def ajustar_pontuacao_basica(texto):
    if not texto:
        return ""
    texto = texto.strip()
    if texto:
        texto = texto[0].upper() + texto[1:]
    if texto and texto[-1] not in ".!?":
        texto += "."
    return texto


def extrair_termos_conhecidos(texto, ia_provider=None, medidor=None):
    """Levanta termos técnicos e nomes próprios já grafados corretamente no texto.

    Serve de referência para a correção reconhecer que uma palavra desconhecida
    em um trecho é, na verdade, a mesma palavra já escrita corretamente em outro
    trecho da aula (ex.: um nome ou termo técnico distorcido pelo Whisper).
    """
    if not texto:
        return []

    prompt = PROMPT_GLOSSARIO.format(texto=texto)
    try:
        resposta, _ = chamar_groq(
            prompt,
            temperature=0.1,
            medidor=medidor,
            etapa="Groq - extração de glossário",
            ia_provider=ia_provider,
        )
    except Exception:
        return []

    if not resposta or resposta.strip().lower() == "nenhum":
        return []

    termos = [linha.strip(" -•*") for linha in resposta.splitlines()]
    return [termo for termo in termos if termo]


def corrigir_com_ia(texto, ia_provider=None, medidor=None):
    """Corrige a transcrição em blocos usando a Groq."""
    if not texto:
        return None, "transcrição vazia"

    # Limitamos o texto caso ele passe do tamanho máximo configurado no sistema
    texto_limitado = limitar_texto(texto)

    # Dividir o texto em blocos menores (ex: por quebras de linha ou blocos de ~1000 caracteres)
    # Blocos menores mantêm a correção fiel e evitam respostas longas.
    linhas = [line.strip() for line in texto_limitado.split("\n") if line.strip()]

    # Termos já corretos em algum ponto do texto servem de referência para todos
    # os blocos, para que uma palavra distorcida em um trecho seja corrigida com
    # base na mesma palavra grafada certa em outro trecho.
    print("Identificando termos técnicos e nomes para manter consistência...")
    termos = extrair_termos_conhecidos(texto_limitado, ia_provider=ia_provider, medidor=medidor)
    glossario = "\n".join(f"- {termo}" for termo in termos) if termos else "(nenhum termo identificado)"

    texto_final_corrigido = []

    try:
        print("Corrigindo texto com Groq (processando blocos)...")
        for bloco in linhas:
            prompt = PROMPT_CORRECAO.format(texto=bloco, glossario=glossario)
            resposta, _ = chamar_groq(
                prompt,
                temperature=0.1,
                medidor=medidor,
                etapa="Groq - correção da transcrição",
                ia_provider=ia_provider,
            )
            if resposta:
                texto_final_corrigido.append(resposta.strip())
            else:
                texto_final_corrigido.append(bloco)  # Se falhar, mantém o original daquele bloco.

        return " \n".join(texto_final_corrigido), f"Groq ({MODELO_GROQ})"

    except Exception as erro:
        # Retorna o texto original como fallback se a Groq falhar completamente.
        return None, f"Groq indisponível: {erro}"


def corrigir_transcricao(sufixo=None, ia_provider=None, medidor=None):
    padrao = f"transcricao_{sufixo}_*.txt" if sufixo else "transcricao_*.txt"
    arquivo_transcricao = arquivo_mais_recente(padrao)
    if not arquivo_transcricao:
        raise RuntimeError("Nenhuma transcrição encontrada.")

    conteudo = arquivo_transcricao.read_text(encoding="utf-8")
    texto_bruto = extrair_corpo_transcricao(conteudo)

    # Executa a correção inteligente
    texto_corrigido, motivo_ou_metodo = corrigir_com_ia(
        texto_bruto, ia_provider=ia_provider, medidor=medidor
    )

    if texto_corrigido:
        texto = ajustar_pontuacao_basica(texto_corrigido)
        metodo = motivo_ou_metodo
    else:
        texto = ajustar_pontuacao_basica(texto_bruto)
        metodo = f"Ajuste básico ({motivo_ou_metodo})"

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    RESULTADOS_DIR.mkdir(exist_ok=True)
    nome = f"transcricao_corrigida_{sufixo}_{timestamp}.txt" if sufixo else f"transcricao_corrigida_{timestamp}.txt"
    arquivo_saida = RESULTADOS_DIR / nome

    inicio_escrita = time.perf_counter()
    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - TRANSCRIÇÃO CORRIGIDA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {agora.strftime('%d/%m/%Y')}\n")
        arquivo.write(f"Hora: {agora.strftime('%H:%M:%S')}\n\n")
        arquivo.write(f"Arquivo analisado: {arquivo_transcricao.name}\n")
        arquivo.write(f"Método de correção: {metodo}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("TRANSCRIÇÃO CORRIGIDA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto)
    if medidor:
        medidor.registrar("Disco - escrita da transcrição corrigida", time.perf_counter() - inicio_escrita)

    return texto, arquivo_saida


if __name__ == "__main__":
    texto, arquivo_saida = corrigir_transcricao()
    print("\nTRANSCRIÇÃO CORRIGIDA:\n")
    print(texto)
    print("\nArquivo salvo em:")
    print(arquivo_saida)
