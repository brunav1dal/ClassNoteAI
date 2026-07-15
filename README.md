# ClassNote AI

Transforma a gravação de uma aula em material de estudo pronto para usar: transcrição revisada, gráfico do espectro de frequência, lista de palavras-chave e um material de estudo estruturado (resumo, conceitos, pontos de atenção, flashcards e questões de revisão).

Disponível como site (`docs/index.html`) e como programa de desktop (`src/gui.py`), que compartilham o mesmo motor de processamento em Python.

## Funcionalidades

- Upload de áudio/vídeo **ou** gravação ao vivo pelo navegador.
- Padronização do áudio com FFmpeg (mono, 16 kHz, remoção de silêncio, normalização de volume).
- Transcrição local em português com **faster-whisper**, sem depender de GPU.
- Correção da transcrição via API da **Groq**.
- Extração das palavras-chave mais frequentes, com gráfico de barras.
- Análise espectral do áudio (FFT).
- Geração de material de estudo (resumo, conceitos, flashcards e questões), com exportação em PDF.
- Progresso em tempo real, com resultados parciais aparecendo assim que ficam prontos.

## Estrutura do projeto

```
classnote-ai/
├── src/            # Motor de processamento (Python) + backend web + app desktop
├── docs/           # Interface web (HTML/CSS/JS estático)
├── audio/          # Áudios recebidos/convertidos (gerado em tempo de execução)
├── resultados/     # Transcrições, gráficos e material de estudo gerados
└── requirements.txt
```

Veja a Tabela de módulos no [relatório técnico](RELATORIO_CLASSNOTE_AI.tex) para o que cada arquivo em `src/` faz.

## Pré-requisitos

- **Python 3.10+**
- **[FFmpeg](https://ffmpeg.org/download.html)** instalado e no `PATH` (ou configurado via `CLASSNOTE_FFMPEG_PATH`)
- Uma **chave de API da Groq** (grátis em [console.groq.com](https://console.groq.com)) — necessária para a correção de texto e a geração do material de estudo

## Instalação

```powershell
git clone https://github.com/brunav1dal/ClassNoteAI.git
cd ClassNoteAI
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto com sua chave da Groq:

```text
GROQ_API_KEY=gsk_sua_chave_aqui
```

(veja `.env.example`; o `.env` nunca é enviado ao GitHub — está no `.gitignore`)

## Como usar

### Site (local)

```powershell
.\iniciar_web.bat
```

Isso inicia o backend em `http://127.0.0.1:8000` e abre o navegador automaticamente. Host e porta podem ser trocados com as variáveis `CLASSNOTE_WEB_HOST` e `CLASSNOTE_WEB_PORT`.

### Programa de desktop

```powershell
python src\gui.py
```

## Publicando a interface no GitHub Pages

O GitHub Pages só serve **arquivos estáticos** — ele consegue publicar a página em `docs/index.html`, mas **não roda o backend Python** (`web_api.py`). Ou seja: dá para publicar a interface visualmente, mas os botões que processam áudio só vão funcionar se o backend estiver acessível em algum endereço público.

**1. Ativar o Pages para a pasta `docs/`:**

1. No GitHub, abra o repositório → **Settings** → **Pages**.
2. Em **Build and deployment**, escolha **Deploy from a branch**.
3. Em **Branch**, selecione `main` e a pasta `/docs`, depois **Save**.
4. Em alguns minutos a página fica em `https://brunav1dal.github.io/ClassNoteAI/`.

**2. Decidir o que fazer com o backend:**

- **Só mostrar a interface (sem processar áudio de verdade):** não precisa fazer mais nada — a página abre, mas as chamadas a `/api/...` vão falhar, pois não existe backend nesse domínio.
- **Deixar funcional de verdade:** o backend (`src/web_api.py`) precisa estar rodando em algum servidor com HTTPS público (ex.: Render, Railway, Fly.io, PythonAnywhere). Depois disso:
  1. Abra `docs/index.html` e troque a função `apiBase()` (por volta da linha 708) — hoje ela retorna `""` (mesmo domínio) — para retornar a URL do backend, por exemplo `return "https://seu-backend.onrender.com";`.
  2. O CORS do backend já está liberado (`Access-Control-Allow-Origin: *`), então não precisa mexer nisso.
  3. Rodar o Whisper (transcrição) em um plano gratuito desses serviços costuma ser lento ou limitado por CPU/RAM — vale considerar isso antes de publicar como "produção".

Para uso pessoal, a forma mais simples continua sendo rodar `iniciar_web.bat` localmente e acessar `http://127.0.0.1:8000` — o GitHub Pages é útil principalmente para mostrar a interface a alguém sem precisar rodar nada.

## Relatório técnico

Uma descrição detalhada da arquitetura, do pipeline de processamento e das escolhas técnicas está em [`RELATORIO_CLASSNOTE_AI.tex`](RELATORIO_CLASSNOTE_AI.tex).
