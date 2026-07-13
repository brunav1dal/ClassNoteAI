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
3. Se não tiver certeza de um termo técnico ou palavra, NÃO mude.
4. Responda APENAS com o texto corrigido. Sem introduções, sem notas, sem títulos.

Exemplo:
Texto original: "a gente vai focar nos gráfico de pitom pra criar o deste borde"
Texto corrigido: "A gente vai focar nos gráficos de Python pra criar o dashboard."

Texto original para corrigir:
"{texto}"
Texto corrigido:"""


def ajustar_pontuacao_basica(texto):
    if not texto:
        return ""
    texto = texto.strip()
    if texto:
        texto = texto[0].upper() + texto[1:]
    if texto and texto[-1] not in ".!?":
        texto += "."
    return texto


def corrigir_com_ia(texto, ia_provider="groq", medidor=None):
    """Corrige a transcrição em blocos usando a Groq."""
    if not texto:
        return None, "transcrição vazia"

    # Limitamos o texto caso ele passe do tamanho máximo configurado no sistema
    texto_limitado = limitar_texto(texto)

    # Dividir o texto em blocos menores (ex: por quebras de linha ou blocos de ~1000 caracteres)
    # Blocos menores mantêm a correção fiel e evitam respostas longas.
    linhas = [line.strip() for line in texto_limitado.split("\n") if line.strip()]

    texto_final_corrigido = []

    try:
        print("Corrigindo texto com Groq (processando blocos)...")
        for bloco in linhas:
            prompt = PROMPT_CORRECAO.format(texto=bloco)
            resposta, _ = chamar_groq(
                prompt,
                temperature=0.1,
                medidor=medidor,
                etapa="Groq - correção da transcrição",
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
