import os
import time

from groq import Groq


# Configure a chave da Groq no arquivo local .env:
# GROQ_API_KEY=gsk_sua_chave_da_groq
MODELO_GROQ = "llama-3.1-8b-instant"


def chamar_groq(prompt, temperature=0.1, medidor=None, etapa="Groq - requisição + rede + inferência"):
    """Gera conteúdo exclusivamente pela API da Groq."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não foi configurada. Adicione a chave gsk_ no arquivo .env."
        )

    cliente_groq = Groq(api_key=api_key)
    inicio_requisicao = time.perf_counter()
    resposta = cliente_groq.chat.completions.create(
        model=MODELO_GROQ,
        messages=[{"role": "user", "content": prompt}],
        # Temperatura baixa deixa a estrutura dos cards mais estável.
        temperature=temperature,
    )
    if medidor:
        medidor.registrar(etapa, time.perf_counter() - inicio_requisicao)

    conteudo = resposta.choices[0].message.content
    if not conteudo:
        raise RuntimeError("A Groq retornou uma resposta sem conteúdo.")
    return conteudo.strip(), f"Groq ({MODELO_GROQ})"
