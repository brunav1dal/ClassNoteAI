# ClassNote AI Web

## Como iniciar

No PowerShell, dentro da pasta do projeto:

```powershell
.\iniciar_web.bat
```

Depois abra no navegador o endereço informado pelo servidor ao iniciar.

## Configurar a Groq

Crie um arquivo `.env` na raiz do projeto com sua chave da Groq, que começa com `gsk_`:

```text
GROQ_API_KEY=gsk_sua_chave_aqui
```

Alternativamente, configure a chave no PowerShell antes de iniciar:

```powershell
$env:GROQ_API_KEY="gsk_sua_chave_aqui"
.\iniciar_web.bat
```

Instale o cliente oficial se necessário:

```powershell
pip install groq
```

Não envie o arquivo `.env` para o GitHub. Ele está listado no `.gitignore`.

## Observação

O processamento de áudio exige que a interface e o backend sejam publicados no mesmo domínio ou que exista um proxy configurado para as rotas `/api`.
