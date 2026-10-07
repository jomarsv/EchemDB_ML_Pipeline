from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_report(
    input_path: Path,
    output_dir: Path,
    index: pd.DataFrame,
    features: pd.DataFrame,
    control: pd.DataFrame,
    model_report: pd.DataFrame,
) -> Path:
    valid = control[control["status"] == "valido"] if not control.empty else pd.DataFrame()
    excluded = control[control["status"] != "valido"] if not control.empty else pd.DataFrame()
    materials = _top_values(features, "material_eletrodo")
    electrolytes = _top_values(features, "eletrolito")

    lines = [
        "# Relatorio tecnico - EchemDB ML Pipeline",
        "",
        "## Fonte dos dados",
        "",
        f"- Entrada analisada: `{input_path}`",
        "- Os dados foram lidos de arquivos locais CSV, TSV, TXT, JSON, JSON-LD ou DataPackage.",
        "- O pipeline nao inventa metadados ausentes; campos nao encontrados permanecem vazios.",
        "",
        "## Resumo de carregamento",
        "",
        f"- Entradas carregadas: {len(index)}",
        f"- Entradas validas: {len(valid)}",
        f"- Entradas excluidas: {len(excluded)}",
        "",
        "## Controle de qualidade",
        "",
        _markdown_table(_status_counts(control)),
        "",
        "## Materiais encontrados",
        "",
        _markdown_table(materials),
        "",
        "## Eletrolitos encontrados",
        "",
        _markdown_table(electrolytes),
        "",
        "## Atributos extraidos",
        "",
        "Foram extraidos atributos de faixa de potencial, estatisticas do sinal, areas sob a curva, picos anódico/catódico quando detectaveis, separacao entre picos, razao de picos, largura aproximada de picos, cruzamentos com zero e estatisticas das derivadas.",
        "",
        "## Modelos testados",
        "",
        _markdown_table(model_report) if not model_report.empty else "Nenhum modelo foi executado.",
        "",
        "## Interpretacao",
        "",
        "A interpretacao cientifica deve considerar o tamanho da base, o balanceamento das classes e a consistencia das unidades. Resultados supervisionados so devem ser tratados como evidência exploratória se houver poucas amostras por material.",
        "",
        "## Limitacoes",
        "",
        "- A deteccao de colunas depende dos nomes presentes nos arquivos.",
        "- Conversoes de unidade so ocorrem para unidades reconhecidas de forma simples.",
        "- A identificacao de picos e heuristica; curvas ruidosas ou incompletas podem gerar valores ausentes.",
        "- A classificacao supervisionada e ignorada quando nao ha amostras suficientes por classe.",
        "- A interpolacao por ordem de aquisicao preserva a sequencia do ciclo, mas nao substitui uma segmentacao eletroquimica completa dos ramos anódico e catódico.",
        "",
        "## Sugestoes de expansao",
        "",
        "- Fixar uma versao dos dados do EchemDB para reprodutibilidade.",
        "- Criar mapeamento manual dos metadados mais importantes do repositório usado.",
        "- Separar ramos anódico e catódico antes da interpolacao.",
        "- Validar atributos de pico com critérios eletroquimicos especificos por sistema.",
        "- Comparar modelos com validação cruzada estratificada quando houver volume suficiente.",
        "",
    ]

    report_path = output_dir / "relatorio_tecnico.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _status_counts(control: pd.DataFrame) -> pd.DataFrame:
    if control.empty:
        return pd.DataFrame({"status": [], "quantidade": []})
    return control["status"].value_counts(dropna=False).rename_axis("status").reset_index(name="quantidade")


def _top_values(frame: pd.DataFrame, column: str, limit: int = 20) -> pd.DataFrame:
    if frame.empty or column not in frame:
        return pd.DataFrame({column: [], "quantidade": []})
    values = frame[column].fillna("desconhecido")
    values = values.replace("", "desconhecido")
    return values.value_counts().head(limit).rename_axis(column).reset_index(name="quantidade")


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "Sem dados."
    columns = [str(column) for column in frame.columns]
    rows = []
    rows.append("| " + " | ".join(_escape_cell(column) for column in columns) + " |")
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(_escape_cell(row[column]) for column in frame.columns) + " |")
    return "\n".join(rows)


def _escape_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")
