from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import json
import threading
import time


class MedidorDesempenho:
    """Coleta durações de um processamento sem alterar seu comportamento."""

    def __init__(self):
        self.inicio = time.perf_counter()
        self._amostras = defaultdict(list)
        self._lock = threading.Lock()

    def registrar(self, etapa, segundos):
        with self._lock:
            self._amostras[etapa].append(segundos)

    @contextmanager
    def etapa(self, nome):
        inicio = time.perf_counter()
        try:
            yield
        finally:
            self.registrar(nome, time.perf_counter() - inicio)

    def total(self):
        return time.perf_counter() - self.inicio

    def dados(self):
        total = self.total()
        etapas = []
        for nome, amostras in self._amostras.items():
            segundos = sum(amostras)
            etapas.append({
                "etapa": nome,
                "segundos": round(segundos, 3),
                "chamadas": len(amostras),
                "percentual_total": round((segundos / total * 100) if total else 0, 1),
            })
        return {"tempo_total_segundos": round(total, 3), "etapas": sorted(etapas, key=lambda item: item["segundos"], reverse=True)}

    def texto(self):
        dados = self.dados()
        linhas = [
            "=" * 56,
            "RELATORIO DE DESEMPENHO",
            "=" * 56,
            "",
        ]
        for item in dados["etapas"]:
            sufixo = f" ({item['chamadas']} chamadas)" if item["chamadas"] > 1 else ""
            linhas.append(f"{item['etapa']}{sufixo:.<43} {item['segundos']:>7.2f} s  {item['percentual_total']:>5.1f}%")
        linhas.extend(["", "-" * 56, f"Tempo total de parede{'':.<29} {dados['tempo_total_segundos']:>7.2f} s"])
        return "\n".join(linhas)

    def salvar(self, diretorio, sufixo=None):
        diretorio = Path(diretorio)
        diretorio.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"desempenho_{sufixo}_{timestamp}" if sufixo else f"desempenho_{timestamp}"
        arquivo_txt = diretorio / f"{base}.txt"
        arquivo_json = diretorio / f"{base}.json"
        arquivo_txt.write_text(self.texto(), encoding="utf-8")
        arquivo_json.write_text(json.dumps(self.dados(), ensure_ascii=False, indent=2), encoding="utf-8")
        return arquivo_txt, arquivo_json
