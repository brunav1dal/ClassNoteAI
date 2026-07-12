from datetime import datetime
import os
from pathlib import Path
import re

from config_env import carregar_env
from ia_utils import chamar_openai, chamar_ollama
from resultados_utils import arquivo_mais_recente
from texto_utils import extrair_corpo_transcricao, limitar_texto


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"

carregar_env()


def montar_prompt(texto, num_palavras):
    if num_palavras < 50:
        return (
            "CURTO",
            f"""
Revise e interprete o texto abaixo em português brasileiro.

Regras:
- Não copie o texto literalmente, exceto se for necessário citar um termo técnico.
- Reescreva com suas próprias palavras.
- Seja claro, didático e objetivo.

Entregue no formato abaixo, com os títulos exatamente como estão escritos (sem numeração):

TEXTO CORRIGIDO
[texto corrigido aqui]

INTERPRETAÇÃO DA MENSAGEM
[interpretação aqui]

OBSERVAÇÕES ÚTEIS
[observações aqui]

Texto:
{texto}
""",
        )

    return (
        "AULA",
        f"""
Crie um material de estudo universitário em português brasileiro usando somente a transcrição.

Regras obrigatórias:
- Não copie e cole trechos longos da transcrição.
- Reescreva o conteúdo com suas próprias palavras.
- Explique de forma didática, como se estivesse ensinando o assunto a um aluno.
- Preserve o sentido da aula, mas organize as ideias em texto claro e coeso.
- Não invente autores, fórmulas, conceitos ou exemplos sem base na transcrição.
- Quando a transcrição estiver confusa, explique com cautela e sinalize que o trecho precisa de revisão.

Formato obrigatório:

RESUMO DA AULA
Escreva de 2 a 4 parágrafos com suas próprias palavras, explicando o assunto central da aula, a lógica da explicação e por que esses pontos são importantes. Não use frases copiadas da transcrição.

CONCEITOS IMPORTANTES
Liste os conceitos centrais e explique cada um de forma simples.

EXPLICAÇÃO DIDÁTICA
Explique o conteúdo passo a passo, com linguagem de professor.

FÓRMULAS E EQUAÇÕES MENCIONADAS
Liste somente fórmulas realmente mencionadas. Se nenhuma fórmula aparecer, diga isso.

EXEMPLOS PRÁTICOS
Crie exemplos simples diretamente relacionados ao que foi dito na aula.

PONTOS DE ATENÇÃO
Liste possíveis dúvidas, pegadinhas ou trechos que merecem revisão.

DICAS PARA PROVA
Destaque o que parece mais importante estudar.

FLASHCARDS
Crie de 4 a 6 flashcards. Para cada um, escreva a pergunta em uma linha e, na linha seguinte, a resposta começando exatamente com "Resposta:".

PERGUNTAS DE REVISÃO
Crie 5 questões discursivas.

RESUMO FINAL
Faça uma síntese curta, sem copiar a transcrição.

Transcrição:
{texto}
""",
    )


def gerar_com_openai(prompt):
    return chamar_openai(
        [
            {
                "role": "system",
                "content": (
                    "Você cria materiais de estudo claros, didáticos e fiéis ao texto enviado. "
                    "Você deve parafrasear e organizar as ideias, não copiar a transcrição."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
    )


def gerar_com_ollama(prompt):
    return chamar_ollama(prompt)


def primeiras_frases(texto, limite):
    frases = [
        frase.strip()
        for frase in re.split(r"(?<=[.!?])\s+", texto)
        if frase.strip()
    ]
    return frases[:limite]


def topicos_locais(texto):
    frases = primeiras_frases(texto, 8)
    if not frases and texto:
        frases = [texto[:500]]
    return frases


def resumo_didatico_local(texto):
    pontos = topicos_locais(texto)
    if not pontos:
        return "A transcrição não contém conteúdo suficiente para gerar um resumo didático."

    return (
        "A aula apresenta um conjunto de ideias que precisam ser organizadas para estudo. "
        "Pelos trechos identificados na transcrição, o conteúdo gira em torno dos conceitos "
        "mais recorrentes da fala e da relação entre eles. Em vez de repetir a transcrição, "
        "o objetivo deste resumo é transformar a fala em uma explicação mais estruturada.\n\n"
        "De forma didática, o estudante deve observar primeiro quais termos aparecem com mais "
        "frequência, depois identificar como esses termos se conectam ao tema central da aula. "
        "A partir disso, é possível revisar o conteúdo como uma sequência de ideias: definição "
        "dos conceitos, explicação do funcionamento, exemplos e pontos que exigem atenção.\n\n"
        "Como este resumo foi gerado localmente, sem uma IA externa, ele deve ser entendido como "
        "uma organização inicial do material. Para uma versão mais elaborada e escrita com maior "
        "qualidade didática, use a opção OpenAI GPT ou revise manualmente os tópicos abaixo."
    )


def gerar_material_local(texto, motivo="Modo local selecionado."):
    pontos = topicos_locais(texto)
    pontos_formatados = "\n".join(f"- {ponto}" for ponto in pontos if ponto)

    texto_gerado = f"""RESUMO DA AULA
{resumo_didatico_local(texto)}

CONCEITOS IMPORTANTES
{pontos_formatados}

EXPLICAÇÃO DIDÁTICA
O conteúdo deve ser estudado procurando transformar a fala em uma sequência lógica. Primeiro, identifique o tema central. Depois, observe os termos que se repetem e tente explicar cada um com suas próprias palavras. Por fim, relacione esses conceitos com exemplos, aplicações e possíveis perguntas de prova.

FÓRMULAS E EQUAÇÕES MENCIONADAS
Não foram identificadas automaticamente nesta versão local.

EXEMPLOS PRÁTICOS
Use os conceitos destacados para criar exemplos relacionados ao tema da aula.

PONTOS DE ATENÇÃO
- Revise possíveis erros de transcrição.
- Confira nomes próprios, termos técnicos e fórmulas.
- Valide os trechos importantes comparando com o áudio original.
- Evite estudar apenas frases copiadas; transforme cada trecho em explicação.

DICAS PARA PROVA
- Priorize os termos-chave extraídos pelo sistema.
- Revise os tópicos que aparecem repetidamente na fala.
- Transforme cada conceito importante em uma pergunta de revisão.

FLASHCARDS
1. Qual foi o tema central da aula?
Resposta: identifique a ideia principal que conecta os conceitos destacados.

2. Quais conceitos apareceram com mais destaque?
Resposta: consulte a seção de conceitos importantes e os termos-chave.

3. Como explicar o assunto com suas próprias palavras?
Resposta: organize definição, funcionamento e exemplo.

PERGUNTAS DE REVISÃO
1. Quais foram os principais tópicos abordados?
2. Como os conceitos destacados se relacionam?
3. Que exemplos poderiam representar esses conceitos?
4. Quais trechos exigem revisão no áudio original?
5. O que pode ser cobrado em uma avaliação sobre essa aula?

RESUMO FINAL
Este material reorganiza a transcrição em formato de estudo. O resumo foi escrito em linguagem didática e evita copiar a fala literalmente, mas deve ser revisado para aprofundar conceitos específicos.

Motivo técnico:
{motivo}
"""

    return texto_gerado, "Gerador local"


def gerar_material(prompt, texto, ia_provider=None):
    provedor = (ia_provider or os.environ.get("CLASSNOTE_IA_PROVIDER", "auto")).strip().lower()

    if provedor == "local":
        return gerar_material_local(texto)

    if provedor == "openai":
        try:
            return gerar_com_openai(prompt)
        except Exception as erro:
            return gerar_material_local(texto, f"OpenAI indisponível: {erro}")

    if provedor == "ollama":
        try:
            return gerar_com_ollama(prompt)
        except Exception as erro:
            return gerar_material_local(texto, f"Ollama indisponível: {erro}")

    erro_openai = None
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return gerar_com_openai(prompt)
        except Exception as erro:
            print(f"OpenAI indisponível: {erro}")
            erro_openai = erro

    try:
        return gerar_com_ollama(prompt)
    except Exception as erro_ollama:
        motivo = (
            f"OpenAI indisponível: {erro_openai}; Ollama indisponível: {erro_ollama}"
            if erro_openai is not None
            else f"Ollama indisponível: {erro_ollama}"
        )

    return gerar_material_local(
        texto,
        f"Modo automático sem IA disponível ({motivo}).",
    )


def gerar_material_estudo(sufixo=None, ia_provider=None):
    padrao_corrigida = f"transcricao_corrigida_{sufixo}_*.txt" if sufixo else "transcricao_corrigida_*.txt"
    arquivo_transcricao = arquivo_mais_recente(padrao_corrigida)

    if not arquivo_transcricao:
        padrao_bruta = f"transcricao_{sufixo}_*.txt" if sufixo else "transcricao_*.txt"
        arquivo_transcricao = arquivo_mais_recente(padrao_bruta)

    if not arquivo_transcricao:
        print("Nenhuma transcrição encontrada.")
        raise SystemExit(1)

    conteudo = arquivo_transcricao.read_text(encoding="utf-8")

    print("Transcrição encontrada:")
    print(arquivo_transcricao.name)

    texto = limitar_texto(extrair_corpo_transcricao(conteudo))
    num_palavras = len(texto.split())
    print(f"\nPalavras usadas no prompt: {num_palavras}")

    modo, prompt = montar_prompt(texto, num_palavras)
    print(f"\nModo {modo} ativado.")
    print("\nGerando material de estudo...")

    texto_gerado, provedor_usado = gerar_material(prompt, texto, ia_provider=ia_provider)
    print(f"\nResposta recebida de {provedor_usado}.")

    agora = datetime.now()
    data = agora.strftime("%d/%m/%Y")
    hora = agora.strftime("%H:%M:%S")
    timestamp = agora.strftime("%Y%m%d_%H%M%S")

    nome = f"material_estudo_{sufixo}_{timestamp}.txt" if sufixo else f"material_estudo_{timestamp}.txt"
    RESULTADOS_DIR.mkdir(exist_ok=True)
    arquivo_saida = RESULTADOS_DIR / nome

    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - MATERIAL DE ESTUDO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {data}\n")
        arquivo.write(f"Hora: {hora}\n\n")
        arquivo.write(f"Transcrição utilizada: {arquivo_transcricao.name}\n")
        arquivo.write(f"Quantidade de palavras no prompt: {num_palavras}\n")
        arquivo.write(f"Modo utilizado: {modo}\n")
        arquivo.write(f"IA utilizada: {provedor_usado}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("MATERIAL GERADO PELA IA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto_gerado)

    print("\nArquivo salvo em:")
    print(arquivo_saida)

    return texto_gerado, arquivo_saida


if __name__ == "__main__":
    gerar_material_estudo()
