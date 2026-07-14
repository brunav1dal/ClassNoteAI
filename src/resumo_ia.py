from datetime import datetime
from pathlib import Path
import time

from config_env import carregar_env
from ia_utils import chamar_groq
from resultados_utils import arquivo_mais_recente
from texto_utils import extrair_corpo_transcricao, limitar_texto


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = BASE_DIR / "resultados"

carregar_env()


def montar_contexto_aula(nome_aula):
    nome_aula = (nome_aula or "").strip()
    if not nome_aula:
        return ""

    return (
        f'Nome/assunto da aula informado pelo usuário: "{nome_aula}"\n'
        "Use esse nome como contexto principal para interpretar a transcrição: prefira leituras, "
        "termos e conceitos compatíveis com esse assunto quando a transcrição estiver ambígua ou "
        "tiver ruído de transcrição, mas NUNCA invente conteúdo que não esteja na transcrição só "
        "para encaixar no assunto informado.\n"
    )


def montar_prompt(texto, num_palavras, nome_aula=None):
    contexto_aula = montar_contexto_aula(nome_aula)

    if num_palavras < 50:
        return (
            "CURTO",
            f"""
Revise e interprete o texto abaixo em português brasileiro.
{contexto_aula}
Regras:
- Não copie o texto literalmente, exceto se for necessário citar um termo técnico.
- Reescreva com suas próprias palavras.
- Seja claro, didático e objetivo.
- Use somente informações presentes no texto; não crie contexto, causas, consequências ou dados não mencionados.
- Quando não houver informação suficiente, escreva "Não informado no texto.".

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
Você é um assistente de IA focado em gerar dados estruturados para uma interface de estudos. Use APENAS a transcrição fornecida no final para preencher o modelo.
{contexto_aula}
REGRAS OBRIGATÓRIAS:
1. Respeite rigorosamente a estrutura de blocos separada por "===".
2. Não adicione saudações, introduções ou conclusões (comece direto no primeiro bloco).
3. Reescreva tudo com suas próprias palavras de forma didática. Nunca invente dados.
4. Se algo não foi dito na transcrição, preencha a seção estritamente com: "Não informado na transcrição."

Gere a resposta exatamente neste formato:

=== RESUMO
[Escreva de 2 a 3 parágrafos explicando o assunto central da aula e a lógica do professor.]

=== CONCEITOS
[Liste os conceitos centrais e explicações passo a passo. Inclua aqui os exemplos práticos e fórmulas caso tenham sido citados.]

=== ATENÇÃO E PROVA
[Destaque possíveis dúvidas, pegadinhas, trechos confusos e o que é mais importante estudar para a prova.]

=== FLASHCARDS
[Gere de 2 a 4 flashcards estritamente com o formato abaixo, separando FRENTE e VERSO por uma barra vertical "|". Não use numeração ou bullet points.]
FRENTE: [Pergunta direta sobre a matéria] | VERSO: [Resposta curta e direta]
FRENTE: [Pergunta direta sobre a matéria] | VERSO: [Resposta curta e direta]

=== QUESTÕES
[Crie até 3 perguntas discursivas que sirvam para revisão do conteúdo.]

---
TEXTO DA TRANSCRIÇÃO:
[COLE SUA TRANSCRIÇÃO AQUI]



Transcrição:
{texto}
""",
    )


def gerar_material(prompt, texto=None, ia_provider=None, medidor=None):
    """Gera o material exclusivamente pela Groq."""
    try:
        return chamar_groq(
            prompt,
            temperature=0.1,
            medidor=medidor,
            etapa="Groq - material (resumo, questões e flashcards)",
            ia_provider=ia_provider,
        )
    except Exception as erro:
        raise RuntimeError(f"Não foi possível gerar o material com a IA: {erro}") from erro


def gerar_material_estudo(sufixo=None, ia_provider=None, medidor=None, nome_aula=None):
    padrao_corrigida = f"transcricao_corrigida_{sufixo}_*.txt" if sufixo else "transcricao_corrigida_*.txt"
    arquivo_transcricao = arquivo_mais_recente(padrao_corrigida)

    if not arquivo_transcricao:
        padrao_bruta = f"transcricao_{sufixo}_*.txt" if sufixo else "transcricao_*.txt"
        arquivo_transcricao = arquivo_mais_recente(padrao_bruta)

    if not arquivo_transcricao:
        raise RuntimeError("Nenhuma transcrição encontrada.")

    conteudo = arquivo_transcricao.read_text(encoding="utf-8")
    texto = limitar_texto(extrair_corpo_transcricao(conteudo))
    num_palavras = len(texto.split())
    modo, prompt = montar_prompt(texto, num_palavras, nome_aula=nome_aula)

    print(f"Modo {modo} ativado. Gerando material de estudo com Groq...")
    texto_gerado, provedor_usado = gerar_material(
        prompt, texto, ia_provider=ia_provider, medidor=medidor
    )

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    nome = f"material_estudo_{sufixo}_{timestamp}.txt" if sufixo else f"material_estudo_{timestamp}.txt"
    RESULTADOS_DIR.mkdir(exist_ok=True)
    arquivo_saida = RESULTADOS_DIR / nome

    inicio_escrita = time.perf_counter()
    with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("=" * 60 + "\n")
        arquivo.write("CLASSNOTE AI - MATERIAL DE ESTUDO\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(f"Data: {agora.strftime('%d/%m/%Y')}\n")
        arquivo.write(f"Hora: {agora.strftime('%H:%M:%S')}\n\n")
        arquivo.write(f"Transcrição utilizada: {arquivo_transcricao.name}\n")
        arquivo.write(f"Quantidade de palavras no prompt: {num_palavras}\n")
        arquivo.write(f"Modo utilizado: {modo}\n")
        arquivo.write(f"IA utilizada: {provedor_usado}\n\n")
        arquivo.write("=" * 60 + "\n")
        arquivo.write("MATERIAL GERADO PELA IA\n")
        arquivo.write("=" * 60 + "\n\n")
        arquivo.write(texto_gerado)
    if medidor:
        medidor.registrar("Disco - escrita do material de estudo", time.perf_counter() - inicio_escrita)

    print(f"Arquivo salvo em: {arquivo_saida}")
    return texto_gerado, arquivo_saida


if __name__ == "__main__":
    gerar_material_estudo()
