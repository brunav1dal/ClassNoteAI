from pathlib import Path

from termos_chave_core import BASE_DIR, gerar_termos_chave


arquivos_transcricao = sorted(
    BASE_DIR.glob("resultados/transcricao_corrigida_*.txt"),
    key=lambda caminho: caminho.stat().st_mtime,
    reverse=True,
)

if not arquivos_transcricao:
    arquivos_transcricao = sorted(
        BASE_DIR.glob("resultados/transcricao_*.txt"),
        key=lambda caminho: caminho.stat().st_mtime,
        reverse=True,
    )

if not arquivos_transcricao:
    print("Nenhuma transcrição encontrada.")
    raise SystemExit(1)

arquivo_transcricao = arquivos_transcricao[0]
conteudo = Path(arquivo_transcricao).read_text(encoding="utf-8")
resultado = gerar_termos_chave(conteudo, arquivo_transcricao.name)

print("\nTOP 12 TERMOS-CHAVE\n")
for linha in resultado["linhas"]:
    print(linha)

print("\nTotal de termos analisados:", resultado["total"])
print("Termos únicos:", resultado["unicos"])
print("\nArquivo salvo em:")
print(resultado["arquivo"])
