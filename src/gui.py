from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from scipy.io import wavfile

from audio_utils import preparar_audio as preparar_audio_ffmpeg
from correcao_texto import corrigir_transcricao
from fft_audio import gerar_fft
from resultados_utils import arquivo_mais_recente
from resumo_ia import gerar_material_estudo
from termos_chave_core import gerar_termos_chave
from transcricao import transcrever


BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
RESULTADOS_DIR = BASE_DIR / "resultados"
AUDIO_PROCESSADO = AUDIO_DIR / "aula.wav"


def preparar_audio(origem):
    return preparar_audio_ffmpeg(origem, AUDIO_PROCESSADO)


class Worker(QThread):
    progresso = Signal(int)
    mensagem = Signal(str)
    status = Signal(str)
    concluido = Signal()
    erro = Signal(str)

    def __init__(self, whisper_model, ia_provider):
        super().__init__()
        self.whisper_model = whisper_model
        self.ia_provider = ia_provider

    def run(self):
        try:
            self.status.emit("Analisando frequências do áudio e transcrevendo fala")
            self.mensagem.emit("FFT + Whisper: rodando em paralelo...")

            progresso_anterior = [22]

            def reportar_progresso_whisper(fracao):
                valor = 22 + int(fracao * (52 - 22))
                if valor != progresso_anterior[0]:
                    progresso_anterior[0] = valor
                    self.progresso.emit(valor)

            tarefas = {
                "FFT": lambda: gerar_fft(audio_path=AUDIO_PROCESSADO),
                "Whisper": lambda: transcrever(
                    audio_path=AUDIO_PROCESSADO,
                    whisper_model=self.whisper_model,
                    progress_callback=reportar_progresso_whisper,
                ),
            }
            with ThreadPoolExecutor(max_workers=2) as executor:
                futuros = {executor.submit(tarefa): nome for nome, tarefa in tarefas.items()}
                for futuro in as_completed(futuros):
                    nome = futuros[futuro]
                    futuro.result()
                    self.mensagem.emit(f"{nome} concluído.")
            self.progresso.emit(52)

            self.status.emit("Corrigindo transcrição")
            self.mensagem.emit("Correção: corrigindo transcrição...")
            corrigir_transcricao(ia_provider=self.ia_provider)
            self.progresso.emit(66)

            self.status.emit("Extraindo termos-chave")
            self.mensagem.emit("Termos: extraindo termos-chave...")
            arquivo_transcricao = arquivo_mais_recente("transcricao_corrigida_*.txt")
            if not arquivo_transcricao:
                raise RuntimeError("Nenhuma transcrição encontrada para extrair termos-chave.")
            conteudo = arquivo_transcricao.read_text(encoding="utf-8")
            gerar_termos_chave(conteudo, arquivo_transcricao.name)
            self.progresso.emit(80)

            self.status.emit("Gerando material de estudo")
            self.mensagem.emit("IA: gerando material de estudo...")
            gerar_material_estudo(ia_provider=self.ia_provider)
            self.progresso.emit(100)

            self.status.emit("Processamento concluído")
            self.mensagem.emit("Processamento concluído.")
            self.concluido.emit()
        except Exception as erro:
            self.erro.emit(str(erro))


class Janela(QWidget):
    def __init__(self):
        super().__init__()

        self.arquivo_audio = None
        self.worker = None

        self.setWindowTitle("ClassNote AI")
        self.resize(1120, 760)
        self.setObjectName("janela")

        self.titulo = QLabel("ClassNote AI")
        self.titulo.setObjectName("titulo")
        self.subtitulo = QLabel("Transforme aulas em transcrição, termos-chave e material de estudo.")
        self.subtitulo.setObjectName("subtitulo")

        self.label_arquivo = QLabel("Nenhum arquivo selecionado")
        self.label_arquivo.setObjectName("arquivo")
        self.label_status = QLabel("Pronto para processar")
        self.label_status.setObjectName("status")

        self.botao_audio = QPushButton("Selecionar áudio")
        self.botao_audio.setObjectName("secundario")
        self.botao_processar = QPushButton("Processar")
        self.botao_processar.setObjectName("primario")
        self.botao_salvar = QPushButton("Salvar transcrição")
        self.botao_pdf = QPushButton("Emitir PDF")

        self.combo_whisper = QComboBox()
        self.combo_whisper.addItem("CPU otimizada - base (int8)", "base")

        self.combo_ia = QComboBox()
        self.combo_ia.addItem("Groq API", "groq")

        self.progresso = QProgressBar()
        self.progresso.setValue(0)
        self.progresso.setTextVisible(True)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        self.log.setPlaceholderText("O status do processamento aparecerá aqui.")

        self.abas = QTabWidget()
        self.aba_sinal = QTextEdit()
        self.aba_fft = QLabel("O gráfico da FFT aparecerá aqui.")
        self.aba_palavras = QLabel("O gráfico dos termos-chave aparecerá aqui.")
        self.aba_transcricao = QTextEdit()
        self.aba_material = QTextEdit()
        self.aba_matematica = QTextEdit()

        for imagem in (self.aba_fft, self.aba_palavras):
            imagem.setAlignment(Qt.AlignCenter)
            imagem.setScaledContents(True)
            imagem.setMinimumHeight(360)
            imagem.setObjectName("imagem")

        self.aba_sinal.setReadOnly(True)
        self.aba_matematica.setReadOnly(True)

        self.abas.addTab(self.aba_sinal, "Sinal")
        self.abas.addTab(self.aba_fft, "FFT")
        self.abas.addTab(self.aba_palavras, "Termos-chave")
        self.abas.addTab(self.aba_transcricao, "Transcrição")
        self.abas.addTab(self.aba_material, "Material")
        self.abas.addTab(self.aba_matematica, "Matemática")

        self.montar_layout()
        self.conectar_eventos()
        self.aplicar_estilo()
        self.carregar_textos_iniciais()

    def montar_layout(self):
        topo = QVBoxLayout()
        topo.addWidget(self.titulo)
        topo.addWidget(self.subtitulo)

        painel = QFrame()
        painel.setObjectName("painel")
        painel_layout = QGridLayout()
        painel_layout.addWidget(QLabel("Arquivo"), 0, 0)
        painel_layout.addWidget(self.label_arquivo, 0, 1, 1, 3)
        painel_layout.addWidget(QLabel("Whisper"), 1, 0)
        painel_layout.addWidget(self.combo_whisper, 1, 1)
        painel_layout.addWidget(QLabel("IA"), 1, 2)
        painel_layout.addWidget(self.combo_ia, 1, 3)
        painel_layout.addWidget(self.botao_audio, 2, 0)
        painel_layout.addWidget(self.botao_processar, 2, 1)
        painel_layout.addWidget(self.botao_salvar, 2, 2)
        painel_layout.addWidget(self.botao_pdf, 2, 3)
        painel.setLayout(painel_layout)

        linha_status = QHBoxLayout()
        linha_status.addWidget(self.label_status)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(14)
        layout.addLayout(topo)
        layout.addWidget(painel)
        layout.addLayout(linha_status)
        layout.addWidget(self.progresso)
        layout.addWidget(self.log)
        layout.addWidget(self.abas)
        self.setLayout(layout)

    def conectar_eventos(self):
        self.botao_audio.clicked.connect(self.selecionar_audio)
        self.botao_processar.clicked.connect(self.processar_audio)
        self.botao_salvar.clicked.connect(self.salvar_transcricao)
        self.botao_pdf.clicked.connect(self.emitir_pdf)

    def aplicar_estilo(self):
        self.setStyleSheet(
            """
            QWidget#janela {
                background: #ffffff;
                color: #111827;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 14px;
            }
            QLabel#titulo {
                font-size: 30px;
                font-weight: 700;
                color: #111827;
            }
            QLabel#subtitulo {
                color: #6b7280;
                font-size: 14px;
            }
            QLabel#arquivo {
                color: #374151;
                padding: 8px 10px;
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
            QLabel#status {
                color: #2563eb;
                font-weight: 600;
            }
            QFrame#painel {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton {
                min-height: 36px;
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid #d1d5db;
                background: #ffffff;
                color: #111827;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f3f4f6;
            }
            QPushButton#primario {
                background: #2563eb;
                border-color: #2563eb;
                color: #ffffff;
            }
            QPushButton#primario:hover {
                background: #1d4ed8;
            }
            QPushButton:disabled {
                background: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
            QComboBox {
                min-height: 34px;
                padding: 6px 10px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background: #ffffff;
            }
            QProgressBar {
                height: 14px;
                border: 1px solid #dbeafe;
                border-radius: 7px;
                background: #eff6ff;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: #2563eb;
            }
            QTextEdit, QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #ffffff;
            }
            QTextEdit {
                padding: 10px;
                selection-background-color: #bfdbfe;
            }
            QTabBar::tab {
                padding: 9px 14px;
                margin-right: 4px;
                border: 1px solid #e5e7eb;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                background: #f9fafb;
                color: #4b5563;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #111827;
                font-weight: 600;
            }
            QLabel#imagem {
                background: #f9fafb;
                border: 1px dashed #d1d5db;
                border-radius: 8px;
                color: #6b7280;
            }
            """
        )

    def carregar_textos_iniciais(self):
        self.aba_sinal.setText(
            """CLASSNOTE AI

Selecione um áudio e clique em Processar.

O áudio será preparado automaticamente para:
- WAV
- mono
- 16 kHz
- amostra de 16 bits

Dica de desempenho:
O faster-whisper usa o modelo "base" com quantização int8, otimizado para CPU.
"""
        )

        self.aba_matematica.setText(
            """PROCESSAMENTO DE VOZ

1. Sinal no domínio do tempo
x[n]

2. Transformada Discreta de Fourier
X[k] = Σ x[n] e^(-j2πkn/N)

3. FFT
DFT: O(N²)
FFT: O(N log N)

4. Reconhecimento de fala
Whisper converte áudio em texto.

5. Termos-chave
O sistema remove conectores, preposições e vícios de fala para manter termos úteis.

6. Geração de conteúdo
Groq API gera a correção e o material de estudo.
"""
        )

    def selecionar_audio(self):
        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar áudio",
            "",
            "Áudio e vídeo (*.wav *.mp3 *.mp4 *.m4a *.flac *.ogg);;Todos os arquivos (*)",
        )

        if not arquivo:
            return

        self.arquivo_audio = arquivo
        self.label_arquivo.setText(arquivo)
        self.label_status.setText("Arquivo selecionado")
        self.log.append("Áudio selecionado.")

    def processar_audio(self):
        if not self.arquivo_audio:
            self.log.append("Selecione um áudio antes de processar.")
            self.label_status.setText("Aguardando seleção de áudio")
            return

        try:
            self.definir_processando(True)
            self.progresso.setValue(0)
            self.label_status.setText("Preparando áudio")
            self.log.append("Preparando áudio...")
            mensagem = preparar_audio(self.arquivo_audio)
            self.log.append(mensagem)
            self.progresso.setValue(10)
        except Exception as erro:
            self.definir_processando(False)
            self.label_status.setText("Erro ao preparar áudio")
            self.log.append(f"Erro ao preparar áudio: {erro}")
            return

        whisper_model = self.combo_whisper.currentData()
        ia_provider = self.combo_ia.currentData()

        self.log.append(
            f"Iniciando pipeline com Whisper '{whisper_model}' e IA '{ia_provider}'."
        )
        self.worker = Worker(whisper_model, ia_provider)
        self.worker.progresso.connect(self.progresso.setValue)
        self.worker.mensagem.connect(self.log.append)
        self.worker.status.connect(self.label_status.setText)
        self.worker.erro.connect(self.exibir_erro)
        self.worker.concluido.connect(self.carregar_resultados)
        self.worker.concluido.connect(lambda: self.definir_processando(False))
        self.worker.start()

    def definir_processando(self, processando):
        for widget in (
            self.botao_audio,
            self.botao_processar,
            self.botao_salvar,
            self.botao_pdf,
            self.combo_whisper,
            self.combo_ia,
        ):
            widget.setEnabled(not processando)

    def exibir_erro(self, mensagem):
        self.definir_processando(False)
        self.label_status.setText("Erro no processamento")
        self.log.append(f"Erro: {mensagem}")

    def carregar_resultados(self):
        RESULTADOS_DIR.mkdir(exist_ok=True)
        self.label_status.setText("Carregando resultados")
        self.log.append("Carregando resultados...")
        self.carregar_info_audio()
        self.carregar_imagem("espectro_*.png", self.aba_fft)
        self.carregar_imagem("grafico_palavras_*.png", self.aba_palavras)
        self.carregar_texto("transcricao_corrigida_*.txt", self.aba_transcricao)
        self.carregar_texto("material_estudo_*.txt", self.aba_material)
        self.label_status.setText("Pipeline finalizado")
        self.log.append("Pipeline finalizado.")

    def carregar_info_audio(self):
        try:
            fs, audio = wavfile.read(str(AUDIO_PROCESSADO))
            duracao = len(audio) / fs
            canais = 1 if len(audio.shape) == 1 else audio.shape[1]

            self.aba_sinal.setText(
                f"""INFORMAÇÕES DO ÁUDIO

Arquivo original:
{Path(self.arquivo_audio).name}

Arquivo processado:
{AUDIO_PROCESSADO}

Taxa de amostragem:
{fs} Hz

Canais:
{canais}

Número de amostras:
{len(audio)}

Duração:
{duracao:.2f} segundos

Status:
Processamento concluído
"""
            )
        except Exception as erro:
            self.aba_sinal.setText(
                f"""INFORMAÇÕES DO ÁUDIO

Arquivo original:
{Path(self.arquivo_audio).name}

Status:
Processamento concluído, mas não foi possível ler detalhes do WAV.

Erro:
{erro}
"""
            )

    def carregar_imagem(self, padrao, destino):
        arquivo = arquivo_mais_recente(padrao)
        if arquivo:
            destino.setPixmap(QPixmap(str(arquivo)))

    def carregar_texto(self, padrao, destino):
        arquivo = arquivo_mais_recente(padrao)
        if not arquivo:
            return

        destino.setText(arquivo.read_text(encoding="utf-8"))

    def salvar_transcricao(self):
        RESULTADOS_DIR.mkdir(exist_ok=True)
        arquivo_saida = RESULTADOS_DIR / "transcricao_editada.txt"

        with open(arquivo_saida, "w", encoding="utf-8") as arquivo:
            arquivo.write(self.aba_transcricao.toPlainText())

        self.log.append(f"Transcrição editada salva: {arquivo_saida.name}")

    def emitir_pdf(self):
        texto = self.aba_material.toPlainText().strip()
        if not texto:
            QMessageBox.warning(
                self,
                "Material vazio",
                "Gere ou escreva um material de estudo antes de emitir o PDF.",
            )
            return

        try:
            RESULTADOS_DIR.mkdir(exist_ok=True)
            agora = datetime.now()
            timestamp = agora.strftime("%Y%m%d_%H%M%S")
            arquivo_pdf = RESULTADOS_DIR / f"material_estudo_{timestamp}.pdf"

            pdf = SimpleDocTemplate(str(arquivo_pdf))
            estilos = getSampleStyleSheet()
            elementos = [
                Paragraph("CLASSNOTE AI", estilos["Title"]),
                Paragraph(f"Data: {agora.strftime('%d/%m/%Y')}", estilos["Normal"]),
                Paragraph(f"Hora: {agora.strftime('%H:%M:%S')}", estilos["Normal"]),
            ]

            if self.arquivo_audio:
                elementos.append(
                    Paragraph(
                        f"Áudio analisado: {Path(self.arquivo_audio).name}",
                        estilos["Normal"],
                    )
                )

            elementos.append(Spacer(1, 12))

            titulos = {
                "RESUMO",
                "CONCEITOS",
                "EXPLICAÇÃO",
                "FÓRMULAS",
                "EXEMPLOS",
                "PONTOS DE ATENÇÃO",
                "DICAS",
                "FLASHCARDS",
                "PERGUNTAS",
                "MAPA MENTAL",
            }

            for linha in texto.splitlines():
                linha = linha.strip()
                if not linha:
                    continue

                estilo = (
                    estilos["Heading1"]
                    if any(titulo in linha.upper() for titulo in titulos)
                    else estilos["BodyText"]
                )
                elementos.append(Paragraph(linha, estilo))
                elementos.append(Spacer(1, 4))

            pdf.build(elementos)
            self.log.append(f"PDF gerado: {arquivo_pdf.name}")
        except Exception as erro:
            self.log.append(f"Erro ao gerar PDF: {erro}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = Janela()
    janela.show()
    sys.exit(app.exec())
