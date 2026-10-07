from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np
import pandas as pd

from .schema import CurveRecord

FEATURE_VERSION = "echemdb-features-v2"

FEATURE_COLUMNS = [
    "id_entrada",
    "referencia",
    "doi",
    "material_eletrodo",
    "eletrolito",
    "numero_pontos",
    "E_min",
    "E_max",
    "j_min",
    "j_max",
    "j_media",
    "j_desvio_padrao",
    "area_absoluta",
    "area_liquida",
    "E_pico_anodico",
    "j_pico_anodico",
    "E_pico_catodico",
    "j_pico_catodico",
    "separacao_picos",
    "razao_picos",
    "largura_pico_anodico",
    "largura_pico_catodico",
    "cruzamentos_zero",
    "derivada1_media",
    "derivada1_desvio",
    "derivada1_min",
    "derivada1_max",
    "derivada2_media",
    "derivada2_desvio",
    "tipo_sinal",
    "unidade_potencial_usada",
    "unidade_sinal_usada",
    "normalizado",
    "classe_alvo",
    "status",
    "versao_atributos",
    "hash_curva",
    "grupo_origem",
]

NUMERIC_FEATURES = FEATURE_COLUMNS[6:29]


CONTROL_COLUMNS = [
    "id_entrada",
    "status",
    "motivo_exclusao",
    "numero_de_pontos",
    "material",
    "eletrolito",
    "referencia",
]


def build_feature_outputs(
    records: list[CurveRecord],
    min_points: int,
    n_points: int,
    normalization: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feature_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    clean_frames: list[pd.DataFrame] = []
    curve_rows: list[dict[str, Any]] = []

    for record in records:
        clean_frame, status, reason = _clean_curve(record, min_points)
        feature_rows.append(_extract_features(record, clean_frame, status))
        control_rows.append(
            {
                "id_entrada": record.entry_id,
                "status": status,
                "motivo_exclusao": reason,
                "numero_de_pontos": 0 if clean_frame is None else len(clean_frame),
                "material": record.material_electrode,
                "eletrolito": record.electrolyte,
                "referencia": record.reference,
            }
        )

        if clean_frame is None:
            continue

        clean_frames.append(clean_frame)
        curve_rows.append(_interpolate_curve(record, clean_frame, n_points, normalization))

    features = pd.DataFrame(feature_rows)
    for column in FEATURE_COLUMNS:
        if column not in features.columns:
            features[column] = np.nan
    features = features[FEATURE_COLUMNS]

    control = pd.DataFrame(control_rows)
    for column in CONTROL_COLUMNS:
        if column not in control.columns:
            control[column] = np.nan
    control = control[CONTROL_COLUMNS]

    clean = pd.concat(clean_frames, ignore_index=True) if clean_frames else pd.DataFrame()
    curves = pd.DataFrame(curve_rows)
    return features, clean, curves, control


def _clean_curve(
    record: CurveRecord,
    min_points: int,
) -> tuple[pd.DataFrame | None, str, str | None]:
    if record.frame is None or record.frame.empty:
        reason = record.raw_metadata.get("loader_error", "empty frame")
        return None, "excluido", str(reason)
    if not record.potential_col or not record.signal_col:
        return None, "excluido", "missing potential or signal column"

    potential = pd.to_numeric(record.frame[record.potential_col], errors="coerce")
    signal = pd.to_numeric(record.frame[record.signal_col], errors="coerce")
    data = pd.DataFrame({"E": potential, "j": signal})
    if record.time_col:
        data["t"] = pd.to_numeric(record.frame[record.time_col], errors="coerce")
    data = data.dropna(subset=["E", "j"]).reset_index(drop=True)

    if len(data) < min_points:
        return None, "excluido", f"too few numeric points: {len(data)} < {min_points}"
    if data["E"].nunique() < 2:
        return None, "excluido", "potential column has fewer than two unique values"
    if data["j"].abs().sum() == 0:
        return None, "excluido", "signal is all zero"

    potential_unit = _unit_for_column(record, record.potential_col)
    signal_unit = _unit_for_column(record, record.signal_col)
    try:
        data["E"], used_potential = _convert_potential(data["E"], potential_unit)
        data["j"], used_signal = _convert_signal(data["j"], signal_unit, record.signal_kind)
    except ValueError as exc:
        return None, "excluido", str(exc)

    if not np.isfinite(data["E"]).all() or not np.isfinite(data["j"]).all():
        return None, "excluido", "non-finite numeric values after conversion"

    data.insert(0, "id_entrada", record.entry_id)
    data["material_eletrodo"] = record.material_electrode
    data["eletrolito"] = record.electrolyte
    data["referencia"] = record.reference
    data["doi"] = record.doi
    data["grupo_origem"] = record.raw_metadata.get("grupo_origem", record.doi)
    data["tipo_sinal"] = record.signal_kind
    data["unidade_potencial_usada"] = used_potential
    data["unidade_sinal_usada"] = used_signal
    data["versao_atributos"] = FEATURE_VERSION
    return data, "valido", None


def _extract_features(record: CurveRecord, clean_frame: pd.DataFrame | None, status: str) -> dict[str, Any]:
    row = {
        "id_entrada": record.entry_id,
        "referencia": record.reference,
        "doi": record.doi,
        "material_eletrodo": record.material_electrode,
        "eletrolito": record.electrolyte,
        "tipo_sinal": record.signal_kind,
        "classe_alvo": record.material_electrode,
        "status": status,
        "normalizado": "nao",
        "versao_atributos": FEATURE_VERSION,
        "grupo_origem": record.raw_metadata.get("grupo_origem", record.doi),
    }

    if clean_frame is None:
        row["numero_pontos"] = 0
        return row

    x = clean_frame["E"].to_numpy(dtype=float)
    y = clean_frame["j"].to_numpy(dtype=float)
    fingerprint = np.column_stack((x, y)).astype("<f8").tobytes()
    row["hash_curva"] = hashlib.sha256(record.signal_kind.encode() + fingerprint).hexdigest()
    row.update(
        {
            "numero_pontos": len(clean_frame),
            "E_min": float(np.nanmin(x)),
            "E_max": float(np.nanmax(x)),
            "j_min": float(np.nanmin(y)),
            "j_max": float(np.nanmax(y)),
            "j_media": float(np.nanmean(y)),
            "j_desvio_padrao": float(np.nanstd(y, ddof=1)) if len(y) > 1 else 0.0,
            "area_absoluta": _absolute_area(x, y),
            "area_liquida": _signed_area(x, y),
            "cruzamentos_zero": _zero_crossings(y),
            "unidade_potencial_usada": clean_frame["unidade_potencial_usada"].iloc[0],
            "unidade_sinal_usada": clean_frame["unidade_sinal_usada"].iloc[0],
        }
    )

    row.update(_peak_features(x, y))
    row.update(_derivative_features(x, y))
    return row


def _interpolate_curve(
    record: CurveRecord,
    clean_frame: pd.DataFrame,
    n_points: int,
    normalization: str,
) -> dict[str, Any]:
    y = clean_frame["j"].to_numpy(dtype=float)
    source_axis = np.linspace(0.0, 1.0, len(y))
    target_axis = np.linspace(0.0, 1.0, n_points)
    interpolated = np.interp(target_axis, source_axis, y)
    normalized = _normalize(interpolated, normalization)

    row: dict[str, Any] = {
        "id_entrada": record.entry_id,
        "material_eletrodo": record.material_electrode,
        "eletrolito": record.electrolyte,
        "referencia": record.reference,
        "tipo_sinal": record.signal_kind,
        "normalizacao": normalization,
        "eixo_interpolacao": "ordem_aquisicao_0_1",
    }
    for index, value in enumerate(normalized):
        row[f"f{index:04d}"] = float(value)
    return row


def _peak_features(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    result: dict[str, Any] = {
        "E_pico_anodico": np.nan,
        "j_pico_anodico": np.nan,
        "E_pico_catodico": np.nan,
        "j_pico_catodico": np.nan,
        "separacao_picos": np.nan,
        "razao_picos": np.nan,
        "largura_pico_anodico": np.nan,
        "largura_pico_catodico": np.nan,
    }
    branches = _branches(x, y)
    peaks = {}
    for bx, by in branches:
        mode = "max" if bx[-1] > bx[0] else "min"
        smooth = _moving_average(by, max(5, min(21, len(by) // 25 * 2 + 1)))
        maxima, minima = _turning_points(smooth)
        idx = _select_peak(maxima if mode == "max" else minima, by, mode, max(float(np.std(by)) * 0.15, 1e-15))
        if idx is None:
            continue
        name = "anodico" if mode == "max" else "catodico"
        score = by[idx] if mode == "max" else -by[idx]
        if name not in peaks or score > peaks[name][0]:
            peaks[name] = (score, float(bx[idx]), float(by[idx]), _half_width(bx, by, idx, mode))
    for name, (_, potential, signal, width) in peaks.items():
        result[f"E_pico_{name}"] = potential
        result[f"j_pico_{name}"] = signal
        result[f"largura_pico_{name}"] = width
    # Only a single two-branch cycle supports this geometric peak-pair descriptor.
    if len(branches) == 2 and len(peaks) == 2:
        result["separacao_picos"] = abs(peaks["anodico"][1] - peaks["catodico"][1])
        denominator = abs(peaks["catodico"][2])
        result["razao_picos"] = abs(peaks["anodico"][2]) / denominator if denominator else np.nan
    return result


def _branches(x: np.ndarray, y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    branches = []
    start, direction = 0, 0
    for index, delta in enumerate(np.diff(x)):
        sign = int(np.sign(delta))
        if not sign or (direction and sign != direction):
            if index - start >= 1:
                branches.append((x[start:index + 1], y[start:index + 1]))
            start = index + 1 if not sign else index
        direction = sign
    if len(x) - start >= 2:
        branches.append((x[start:], y[start:]))
    return branches


def _derivative_features(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    slopes, curvature = [], []
    for bx, by in _branches(x, y):
        dx = np.diff(bx)
        d1 = np.diff(by) / dx
        slopes.extend(d1)
        if len(d1) >= 2:
            midpoint = (bx[1:] + bx[:-1]) / 2
            curvature.extend(np.diff(d1) / np.diff(midpoint))
    d1, d2 = np.asarray(slopes), np.asarray(curvature)
    if not len(d1):
        return {
            "derivada1_media": np.nan,
            "derivada1_desvio": np.nan,
            "derivada1_min": np.nan,
            "derivada1_max": np.nan,
            "derivada2_media": np.nan,
            "derivada2_desvio": np.nan,
        }
    return {
        "derivada1_media": float(np.nanmean(d1)),
        "derivada1_desvio": float(np.nanstd(d1, ddof=1)) if len(d1) > 1 else 0.0,
        "derivada1_min": float(np.nanmin(d1)),
        "derivada1_max": float(np.nanmax(d1)),
        "derivada2_media": float(np.nanmean(d2)) if len(d2) else np.nan,
        "derivada2_desvio": float(np.nanstd(d2, ddof=1)) if len(d2) > 1 else 0.0,
    }


def _normalize(values: np.ndarray, method: str) -> np.ndarray:
    values = values.astype(float)
    if method == "none":
        return values
    if method == "max_abs":
        scale = np.nanmax(np.abs(values))
        return values / scale if scale > 0 else values
    if method == "zscore":
        std = np.nanstd(values)
        return (values - np.nanmean(values)) / std if std > 0 else values - np.nanmean(values)
    if method == "minmax":
        min_value = np.nanmin(values)
        max_value = np.nanmax(values)
        span = max_value - min_value
        return (values - min_value) / span if span > 0 else values * 0.0
    if method == "area":
        area = np.nansum(np.abs(values))
        return values / area if area > 0 else values
    raise ValueError(f"Unsupported normalization: {method}")


def _absolute_area(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return np.nan
    return float(np.nansum(0.5 * (np.abs(y[:-1]) + np.abs(y[1:])) * np.abs(np.diff(x))))


def _signed_area(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return np.nan
    return float(np.nansum(0.5 * (y[:-1] + y[1:]) * np.diff(x)))


def _zero_crossings(y: np.ndarray) -> int:
    signs = np.signbit(y)
    return int(np.count_nonzero(signs[:-1] != signs[1:]))


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window < 3 or len(values) < window:
        return values
    if window % 2 == 0:
        window += 1
    kernel = np.ones(window) / window
    pad = window // 2
    padded = np.pad(values, pad_width=pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def _turning_points(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    derivative = np.diff(values)
    signs = np.sign(derivative)
    for index in range(1, len(signs)):
        if signs[index] == 0:
            signs[index] = signs[index - 1]
    maxima = np.where((signs[:-1] > 0) & (signs[1:] < 0))[0] + 1
    minima = np.where((signs[:-1] < 0) & (signs[1:] > 0))[0] + 1
    return maxima, minima


def _select_peak(candidates: np.ndarray, y: np.ndarray, mode: str, threshold: float) -> int | None:
    if len(candidates) == 0:
        return None
    baseline = float(np.nanmedian(y))
    if mode == "max":
        candidates = np.array([idx for idx in candidates if y[idx] - baseline >= threshold])
        return int(candidates[np.argmax(y[candidates])]) if len(candidates) else None
    candidates = np.array([idx for idx in candidates if baseline - y[idx] >= threshold])
    return int(candidates[np.argmin(y[candidates])]) if len(candidates) else None


def _half_width(x: np.ndarray, y: np.ndarray, peak_index: int, mode: str) -> float:
    baseline = float(np.nanmedian(y))
    peak_value = float(y[peak_index])
    half = baseline + (peak_value - baseline) / 2.0
    mask = y >= half if mode == "max" else y <= half
    left = right = peak_index
    while left > 0 and mask[left - 1]:
        left -= 1
    while right < len(y) - 1 and mask[right + 1]:
        right += 1
    if left == 0 or right == len(y) - 1:
        return np.nan
    def crossing(a: int, b: int) -> float:
        return float(x[a] + (half - y[a]) * (x[b] - x[a]) / (y[b] - y[a]))
    return abs(crossing(right, right + 1) - crossing(left - 1, left))


def _unit_for_column(record: CurveRecord, column: str | None) -> str | None:
    if not column:
        return None
    clean_column = column.casefold()
    for key, value in record.units.items():
        if str(key).casefold() in {clean_column, f"{clean_column}_unit"}:
            return value
    return None


def _convert_potential(values: pd.Series, unit: str | None) -> tuple[pd.Series, str]:
    if not unit:
        raise ValueError("Unidade de potencial ausente")
    normalized = _clean_unit(unit)
    if normalized == "mv":
        return values / 1000.0, "V"
    if normalized == "v":
        return values, "V"
    raise ValueError(f"Unidade de potencial nao reconhecida: {unit}")


def _convert_signal(values: pd.Series, unit: str | None, signal_kind: str) -> tuple[pd.Series, str]:
    if not unit:
        raise ValueError("Unidade de sinal ausente")
    normalized = _clean_unit(unit)
    if signal_kind == "current_density":
        dimension = unit.strip().lower().replace("\u00b5", "u").replace("\u03bc", "u")
        dimension = dimension.replace("\u00b2", "2").replace("\u2212", "-").replace("^", "")
        dimension = re.sub(r"[\s\u00b7*]", "", dimension)
        match = re.fullmatch(r"(a|ma|ua|na)(?:/(m2|cm2)|(m|cm)-2)", dimension)
        if match:
            current = {"a": 1.0, "ma": 1e-3, "ua": 1e-6, "na": 1e-9}[match[1]]
            area = 1 if (match[2] or match[3]) in {"m2", "m"} else 1e-4
            return values * current / area, "A/m2"
    if signal_kind == "current":
        if normalized == "a":
            return values, "A"
        if normalized == "ma":
            return values / 1000.0, "A"
        if normalized in {"ua", "microa"}:
            return values / 1_000_000.0, "A"
        if normalized == "na":
            return values * 1e-9, "A"
    raise ValueError(f"Unidade incompativel com {signal_kind}: {unit}")


def _clean_unit(unit: str) -> str:
    cleaned = unit.strip().lower()
    cleaned = cleaned.replace("µ", "u").replace("μ", "u")
    cleaned = cleaned.replace("^", "")
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace("per", "/")
    cleaned = cleaned.replace("-", "").replace("−", "")
    cleaned = cleaned.replace("²", "2")
    cleaned = cleaned.replace("*", "").replace(".", "").replace("_", "").replace("·", "")
    return cleaned
