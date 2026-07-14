import os
import time

from groq import Groq, AuthenticationError, PermissionDeniedError, RateLimitError


# Configure a chave da Groq no arquivo local .env:
# GROQ_API_KEY=gsk_sua_chave_da_groq
# Opcionalmente, configure uma chave reserva usada automaticamente quando a
# chave principal ficar sem créditos ou atingir o limite de uso:
# GROQ_API_KEY_FALLBACK=gsk_sua_chave_reserva
MODELO_GROQ = "llama-3.1-8b-instant"

# Erros que indicam problema com a própria chave (sem créditos, limite atingido
# ou chave inválida) — nesses casos vale a pena tentar a outra chave.
ERROS_CHAVE_INDISPONIVEL = (AuthenticationError, PermissionDeniedError, RateLimitError)

# "Groq 1" e "Groq 2" na interface correspondem a estas variáveis do .env.
VARIAVEIS_CHAVE_GROQ = {
    "groq1": "GROQ_API_KEY",
    "groq2": "GROQ_API_KEY_FALLBACK",
}


def _chaves_groq_disponiveis(ia_provider=None):
    """Monta a ordem de tentativa das chaves, priorizando a escolhida pelo usuário.

    A chave escolhida (Groq 1 ou Groq 2) é tentada primeiro; a outra continua
    disponível como fallback automático caso a escolhida falhe.
    """
    variavel_preferida = VARIAVEIS_CHAVE_GROQ.get(ia_provider)
    ordem = [variavel_preferida] if variavel_preferida else []
    ordem += [v for v in VARIAVEIS_CHAVE_GROQ.values() if v not in ordem]

    chaves = []
    for variavel in ordem:
        valor = os.environ.get(variavel)
        if valor and valor not in chaves:
            chaves.append(valor)

    return chaves


def chamar_groq(prompt, temperature=0.1, medidor=None, etapa="Groq - requisição + rede + inferência", ia_provider=None):
    """Gera conteúdo pela API da Groq, com fallback para a outra chave configurada.

    ``ia_provider`` pode ser "groq1" ou "groq2" para escolher qual chave (GROQ_API_KEY
    ou GROQ_API_KEY_FALLBACK) tentar primeiro. Se a chave escolhida ficar sem créditos,
    atingir o limite de uso ou for inválida, a outra chave é tentada automaticamente.
    """
    chaves = _chaves_groq_disponiveis(ia_provider)
    if not chaves:
        raise RuntimeError(
            "GROQ_API_KEY não foi configurada. Adicione a chave gsk_ no arquivo .env."
        )

    inicio_requisicao = time.perf_counter()
    ultimo_erro = None
    for indice, api_key in enumerate(chaves):
        cliente_groq = Groq(api_key=api_key)
        try:
            resposta = cliente_groq.chat.completions.create(
                model=MODELO_GROQ,
                messages=[{"role": "user", "content": prompt}],
                # Temperatura baixa deixa a estrutura dos cards mais estável.
                temperature=temperature,
            )
            break
        except ERROS_CHAVE_INDISPONIVEL as erro:
            ultimo_erro = erro
            continue
    else:
        raise RuntimeError(
            f"Nenhuma chave da Groq disponível funcionou (última falha: {ultimo_erro})."
        ) from ultimo_erro

    if medidor:
        medidor.registrar(etapa, time.perf_counter() - inicio_requisicao)

    conteudo = resposta.choices[0].message.content
    if not conteudo:
        raise RuntimeError("A Groq retornou uma resposta sem conteúdo.")
    return conteudo.strip(), f"Groq ({MODELO_GROQ})"
