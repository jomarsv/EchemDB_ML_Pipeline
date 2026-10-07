"""The same physical preprocessing for uploaded curves and pipeline records."""
from __future__ import annotations

import pandas as pd

from .features import build_feature_outputs
from .schema import CurveRecord


def extract_uploaded_curves(rows: list[dict], defaults: dict | None = None) -> list[dict]:
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("CSV vazio")
    defaults = defaults or {}
    if not isinstance(defaults, dict):
        raise ValueError("Metadados devem ser um objeto")
    frame = pd.DataFrame(rows)
    if "id_entrada" not in frame:
        frame["id_entrada"] = "nova_curva"
    if frame["id_entrada"].isna().any() or frame["id_entrada"].eq("").any():
        raise ValueError("Identificador de curva ausente")
    records = []
    for identifier, group in frame.groupby("id_entrada", sort=False):
        def metadata(key: str):
            values = group[key].dropna().astype(str).str.strip() if key in group else pd.Series(dtype=str)
            values = values[values.ne("")].unique()
            if len(values) > 1:
                raise ValueError(f"Metadado inconsistente: {identifier}, {key}")
            return values[0] if len(values) else defaults.get(key)

        signal = "j" if "j" in group else "I" if "I" in group else None
        if "E" not in group or signal is None:
            raise ValueError("Curva requer colunas E e j (ou I)")
        records.append(CurveRecord(
            entry_id=str(identifier), reference=metadata("referencia"), doi=metadata("doi"),
            material_electrode=metadata("material_eletrodo"), electrolyte=metadata("eletrolito"),
            experiment_type="CV", frame=group.reset_index(drop=True),
            potential_col="E", signal_col=signal,
            signal_kind=metadata("tipo_sinal") or "unknown",
            units={"E": metadata("unidade_potencial_usada"), signal: metadata("unidade_sinal_usada")},
            raw_metadata={"grupo_origem": metadata("grupo_origem") or metadata("doi")},
        ))
    features, _, _, control = build_feature_outputs(records, min_points=20, n_points=256, normalization="max_abs")
    excluded = control[control.status != "valido"]
    if not excluded.empty:
        raise ValueError("; ".join(f"{row.id_entrada}: {row.motivo_exclusao}" for row in excluded.itertuples()))
    return features.astype(object).where(pd.notna(features), None).to_dict(orient="records")
