import json
import os
import urllib.error
import urllib.request


def chamar_openai(mensagens, temperature=0.35, timeout=180):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não foi configurada.")

    modelo = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": modelo,
        "messages": mensagens,
        "temperature": temperature,
    }

    requisicao = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro da OpenAI API: {erro.code} - {detalhe}") from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"Erro de conexão com a OpenAI API: {erro}") from erro

    return dados["choices"][0]["message"]["content"].strip(), f"OpenAI ({modelo})"


def chamar_ollama(prompt):
    try:
        from ollama import chat
    except Exception as erro:
        raise RuntimeError(f"Pacote ollama não disponível: {erro}") from erro

    modelo = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
    resposta = chat(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
    )
    return resposta["message"]["content"].strip(), f"Ollama ({modelo})"
