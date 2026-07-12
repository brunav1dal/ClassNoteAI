from datetime import datetime
import os
from pathlib import Path

from ia_utils import chamar_openai, chamar_ollama
from resultados_utils import arquivo_mais_recente
from texto_utils import extrair_corpo_transcricao, limitar_texto


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"

PROMPT_CORRECAO = """Você corrige transcrições de aulas em português brasileiro geradas por reconhecimento de fala automático.

Regras obrigatórias:
- Corrija apenas erros óbvios de ortografia, pontuação e palavras trocadas por outras parecidas foneticamente.
- Não adicione nenhuma palavra, frase, exemplo, dado ou informação que não esteja no texto original.
- Não resuma, não parafraseie e não reescreva frases inteiras.
- Se não tiver certeza do que uma palavra deveria ser, mantenha a palavra original.
- Devolva somente o texto corrigido, sem comentários, títulos ou explicações.

Texto:
{texto}
"""


def ajustar_pontuacao_basica(texto):
    if texto:
        texto = texto[0].upper() + texto[1:]

    if texto and texto[-1] not in ".!?":
        texto += "."

    return texto


def _mensagens_correcao(prompt):
    return [
        {
            "role": "system",
            "content": (
                "Você corrige erros de reconhecimento de fala sem alterar o conteúdo, "
                "o sentido ou adicionar qualquer informação nova."
            ),
        },
        {"role": "user", "content": prompt},
    ]


def corrigir_com_ia(texto, ia_provider=None):
    """Retorna (texto_corrigido, metodo) em caso de sucesso, ou (None, motivo)
    quando a IA não pôde ser usada - o motivo real (chave ausente, chave
    inválida, erro de rede etc.) é sempre propagado, nunca substituído por uma
    mensagem genérica."""
    provedor = (ia_provider or os.environ.get("CLASSNOTE_IA_PROVIDER", "auto")).strip().lower()

    if provedor == "local":
        return None, "modo local selecionado"
    if not texto:
        return None, "transcrição vazia"

    prompt = PROMPT_CORRECAO.format(texto=limitar_texto(texto))

    if provedor == "openai":
        try:
            return chamar_openai(_mensagens_correcao(prompt), temperature=0.1)
        except Exception as erro:
            return None, f"OpenAI indisponível: {erro}"

    if provedor == "ollama":
        try:
            return chamar_ollama(prompt)
        except Exception as erro:
            return None, f"Ollama indisponível: {erro}"

    if provedor == "auto":
        erro_openai = None
        if os.environ.get("OPENAI_API_KEY"):
            try:
                return chamar_openai(_mensagens_correcao(prompt), temperature=0.1)
            except Exception as erro:
                erro_openai = erro

        try:
            return chamar_ollama(prompt)
        except Exception as erro_ollama:
            if erro_openai is not None:
                return None, f"OpenAI indisponível: {erro_openai}; Ollama indisponível: {erro_ollama}"
            return None, f"Ollama indisponível: {erro_ollama}"

    return None, f"provedor de IA desconhecido: {provedor}"


def corrigir_transcricao(sufixo=None, ia_provider=None):
    padrao = f"transcricao_{sufixo}_*.txt" if sufixo else "transcricao_*.txt"
    arquivo_transcricao = arquivo_mais_recente(padrao)
    if not arquivo_transcricao:
        print("Nenhuma transcrição encontrada.")
        raise SystemExit(1)

    conteudo = arquivo_transcricao.read_text(encoding="utf-8")
    texto_bruto = extrair_corpo_transcricao(conteudo)

    texto_corrigido, motivo_ou_metodo = corrigir_com_ia(texto_bruto, ia_provider=ia_provider)
    if texto_corrigido:
        texto = ajustar_pontuacao_basica(texto_corrigido)
        metodo = motivo_ou_metodo
    else:
        texto = ajustar_pontuacao_basica(texto_bruto)
        metodo = f"Ajuste básico ({motivo_ou_metodo})"

    agora = datetime.now()
    data = agora.strftime("%d/%m/%Y")
    hora = agora.strftime("%H:%M:%S")
    timestamp = agora.strftime("%Y%m%d_%H%M%S")

    RESULTADOS_DIR.mkdir(exist_ok=True)
    nome = (
        f"transcricao_corrigida_{sufixo}_{timestamp}.txt"
        if sufixo
        else f"transcricao_corrigida_{timestamp}.txt"
    )
    arquivo_saida = RESULTADOS_DIR / nome

    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - TRANSCRIÇÃO CORRIGIDA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {data}\n")
        arquivo.write(f"Hora: {hora}\n\n")
        arquivo.write(f"Arquivo analisado: {arquivo_transcricao.name}\n")
        arquivo.write(f"Método de correção: {metodo}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("TRANSCRIÇÃO CORRIGIDA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto)

    return texto, arquivo_saida


if __name__ == "__main__":
    texto, arquivo_saida = corrigir_transcricao()
    print("\nTRANSCRIÇÃO CORRIGIDA:\n")
    print(texto)
    print("\nArquivo salvo em:")
    print(arquivo_saida)
