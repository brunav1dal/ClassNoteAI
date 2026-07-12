# ClassNote AI Web

## Como iniciar

No PowerShell, dentro da pasta do projeto:

```powershell
.\iniciar_web.bat
```

Depois abra no navegador:

```text
http://127.0.0.1:8000
```

## Como usar GPT

Se quiser usar OpenAI GPT na geração do material, crie um arquivo chamado `.env` na raiz do projeto:

```text
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gpt-4.1-mini
```

Depois inicie normalmente:

```powershell
.\iniciar_web.bat
```

Alternativamente, configure a chave no PowerShell antes de iniciar:

```powershell
$env:OPENAI_API_KEY="sua_chave_aqui"
$env:OPENAI_MODEL="gpt-4.1-mini"
.\iniciar_web.bat
```

Se não houver `OPENAI_API_KEY`, o modo automático usa o Ollama local.

Não envie o arquivo `.env` para o GitHub. Ele está listado no `.gitignore`.

## Observação

O GitHub Pages pode hospedar a interface, mas o processamento real precisa desta API local ou de um backend publicado em algum servidor.
