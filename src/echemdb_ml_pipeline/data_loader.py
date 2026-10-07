from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from .schema import CurveRecord


SUPPORTED_SUFFIXES = {".csv", ".tsv", ".txt", ".json", ".jsonld"}


def load_records(input_path: Path) -> list[CurveRecord]:
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_file():
        try:
            return _load_file(input_path)
        except Exception as exc:  # noqa: BLE001
            return [_error_record(input_path, {}, str(exc))]

    records: list[CurveRecord] = []
    seen: set[Path] = set()

    datapackage = input_path / "datapackage.json"
    if datapackage.exists():
        for record in _load_datapackage(datapackage):
            if record.source_path is not None:
                seen.add(record.source_path.resolve())
            records.append(record)

    for file_path in sorted(input_path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_SUFFIXES:
            resolved = file_path.resolve()
            if resolved in seen or file_path.name == "datapackage.json":
                continue
            if file_path.suffix.lower() in {".csv", ".tsv", ".txt"} and file_path.with_suffix(".json").exists():
                continue
            try:
                loaded = _load_file(file_path)
                for record in loaded:
                    if record.source_path is not None:
                        seen.add(record.source_path.resolve())
                records.extend(loaded)
            except Exception as exc:  # noqa: BLE001
                records.append(_error_record(file_path, {}, str(exc)))

    return records


def records_to_index_frame(records: list[CurveRecord]) -> pd.DataFrame:
    rows = []
    for record in records:
        rows.append(
            {
                "id_entrada": record.entry_id,
                "referencia": record.reference,
                "doi": record.doi,
                "material_eletrodo": record.material_electrode,
                "eletrolito": record.electrolyte,
                "tipo_experimento": record.experiment_type,
                "arquivo_origem": str(record.source_path) if record.source_path else None,
                "coluna_potencial": record.potential_col,
                "coluna_sinal": record.signal_col,
                "tipo_sinal": record.signal_kind,
                "coluna_tempo": record.time_col,
                "unidades": json.dumps(record.units, ensure_ascii=False, sort_keys=True),
                "colunas_numericas": ", ".join(_numeric_columns(record.frame)),
            }
        )
    return pd.DataFrame(rows)


def _load_file(file_path: Path) -> list[CurveRecord]:
    suffix = file_path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        frame = _read_table(file_path)
        return [_make_record(frame, file_path, {}, None)]
    if suffix in {".json", ".jsonld"}:
        return _load_json(file_path)
    return []


def _load_datapackage(datapackage_path: Path) -> list[CurveRecord]:
    with datapackage_path.open("r", encoding="utf-8") as handle:
        package = json.load(handle)

    package_metadata = {
        key: value
        for key, value in package.items()
        if key not in {"resources", "licenses", "contributors"}
    }
    records: list[CurveRecord] = []
    for resource in package.get("resources", []):
        resource_path = resource.get("path")
        if not resource_path:
            continue
        path = (datapackage_path.parent / resource_path).resolve()
        if not path.exists() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        metadata = {**package_metadata, **resource}
        try:
            if path.suffix.lower() in {".csv", ".tsv", ".txt"}:
                records.append(_make_record(_read_table(path), path, metadata, None))
            else:
                for record in _load_json(path, metadata):
                    records.append(record)
        except Exception as exc:  # noqa: BLE001
            records.append(_error_record(path, metadata, str(exc)))
    return records


def _read_table(file_path: Path) -> pd.DataFrame:
    if file_path.suffix.lower() == ".tsv":
        return pd.read_csv(file_path, sep="\t")
    return pd.read_csv(file_path, sep=None, engine="python")


def _load_json(file_path: Path, inherited_metadata: dict[str, Any] | None = None) -> list[CurveRecord]:
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    inherited_metadata = inherited_metadata or {}
    if _looks_like_datapackage(payload):
        return _load_datapackage_payload(file_path, payload, inherited_metadata)

    candidates = _json_table_candidates(payload)
    if not candidates:
        metadata = _extract_metadata(payload)
        return [_error_record(file_path, {**inherited_metadata, **metadata}, "no tabular curve data found")]

    records: list[CurveRecord] = []
    root_metadata = _extract_metadata(payload)
    for index, (frame, local_metadata) in enumerate(candidates):
        metadata = {**inherited_metadata, **root_metadata, **local_metadata}
        suffix = str(index + 1) if len(candidates) > 1 else None
        records.append(_make_record(frame, file_path, metadata, suffix))
    return records


def _looks_like_datapackage(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("resources"), list)


def _load_datapackage_payload(
    package_path: Path,
    package: dict[str, Any],
    inherited_metadata: dict[str, Any] | None = None,
) -> list[CurveRecord]:
    inherited_metadata = inherited_metadata or {}
    package_metadata = _extract_metadata(package)
    records: list[CurveRecord] = []

    for resource in package.get("resources", []):
        resource_path = resource.get("path")
        if not resource_path:
            continue
        path = (package_path.parent / resource_path).resolve()
        if not path.exists() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        metadata = {
            **inherited_metadata,
            **package_metadata,
            **_flatten_echemdb_metadata(resource.get("metadata")),
            **_flatten_schema_units(resource.get("schema")),
            **_extract_metadata(resource),
        }
        try:
            if path.suffix.lower() in {".csv", ".tsv", ".txt"}:
                records.append(_make_record(_read_table(path), path, metadata, None))
            else:
                records.extend(_load_json(path, metadata))
        except Exception as exc:  # noqa: BLE001
            records.append(_error_record(path, metadata, str(exc)))

    if not records:
        metadata = {**inherited_metadata, **package_metadata}
        records.append(_error_record(package_path, metadata, "datapackage has no readable resources"))
    return records


def _json_table_candidates(payload: Any) -> list[tuple[pd.DataFrame, dict[str, Any]]]:
    candidates: list[tuple[pd.DataFrame, dict[str, Any]]] = []

    def visit(obj: Any, metadata: dict[str, Any]) -> None:
        if isinstance(obj, list):
            if obj and all(isinstance(item, dict) for item in obj):
                frame = pd.DataFrame(obj)
                if len(frame) >= 2 and len(_numeric_columns(frame)) >= 2:
                    candidates.append((frame, metadata))
            for item in obj:
                if isinstance(item, (dict, list)):
                    visit(item, metadata)
        elif isinstance(obj, dict):
            local_metadata = {**metadata, **_extract_metadata(obj)}
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    visit(value, local_metadata)

    visit(payload, {})
    return candidates


def _make_record(
    frame: pd.DataFrame,
    source_path: Path,
    metadata: dict[str, Any],
    suffix: str | None,
) -> CurveRecord:
    metadata = metadata or {}
    potential_col = _find_potential_col(frame)
    signal_col, signal_kind = _find_signal_col(frame)
    time_col = _find_time_col(frame)
    units = _extract_units(frame, metadata)

    entry_id = _first_metadata_value(metadata, ["id", "identifier", "name", "title"])
    if not entry_id:
        entry_id = source_path.stem
    if suffix:
        entry_id = f"{entry_id}_{suffix}"

    return CurveRecord(
        entry_id=str(entry_id),
        reference=_first_metadata_value(metadata, ["reference", "references", "citation", "title", "article"]),
        doi=_extract_doi(metadata),
        material_electrode=_first_metadata_value(
            metadata,
            [
                "working_electrode_material",
                "working_electrode",
                "electrode_material",
                "material_electrodo",
                "material",
            ],
        ),
        electrolyte=_first_metadata_value(metadata, ["electrolyte", "solution", "electrolito", "eletrolito"]),
        experiment_type=_first_metadata_value(metadata, ["technique", "method", "experiment_type", "type"]),
        units=units,
        frame=frame,
        source_path=source_path,
        potential_col=potential_col,
        signal_col=signal_col,
        time_col=time_col,
        signal_kind=signal_kind,
        raw_metadata=metadata,
    )


def _error_record(source_path: Path, metadata: dict[str, Any], reason: str) -> CurveRecord:
    record = _make_record(pd.DataFrame(), source_path, metadata, None)
    record.raw_metadata = {**record.raw_metadata, "loader_error": reason}
    return record


def _find_potential_col(frame: pd.DataFrame) -> str | None:
    numeric = _numeric_columns(frame)
    for column in numeric:
        name = _clean_name(column)
        if name in {"e", "u", "v", "potential", "potencial", "voltage", "ewe"}:
            return column
        if "potential" in name or "potencial" in name or "voltage" in name or name.startswith("e_"):
            return column
    return numeric[0] if numeric else None


def _find_signal_col(frame: pd.DataFrame) -> tuple[str | None, str]:
    numeric = _numeric_columns(frame)
    density_candidates: list[str] = []
    current_candidates: list[str] = []
    for column in numeric:
        name = _clean_name(column)
        if "density" in name or "densidade" in name or name == "j" or name.startswith("j_"):
            density_candidates.append(column)
        if name in {"i", "current", "corrente"} or "current" in name or "corrente" in name:
            current_candidates.append(column)

    if density_candidates:
        return density_candidates[0], "current_density"
    if current_candidates:
        return current_candidates[0], "current"
    return (numeric[1], "unknown") if len(numeric) > 1 else (None, "unknown")


def _find_time_col(frame: pd.DataFrame) -> str | None:
    for column in _numeric_columns(frame):
        name = _clean_name(column)
        if name in {"t", "time", "tempo"} or "time" in name or "tempo" in name:
            return column
    return None


def _extract_units(frame: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, str]:
    units: dict[str, str] = {}
    for column in frame.columns:
        match = re.search(r"[\[(]([^)\]]+)[)\]]", str(column))
        if match:
            units[str(column)] = match.group(1).strip()
    for key, value in metadata.items():
        if isinstance(value, str) and "unit" in _clean_name(key):
            units[str(key)] = value
        elif isinstance(value, dict) and "unit" in _clean_name(key):
            units[str(key)] = json.dumps(value, ensure_ascii=False)
    return units


def _flatten_schema_units(schema: Any) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    flattened: dict[str, Any] = {}
    for field in schema.get("fields", []):
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        unit = field.get("unit")
        if name and unit:
            flattened[str(name)] = str(unit)
            flattened[f"{name}_unit"] = str(unit)
    return flattened


def _flatten_echemdb_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    echemdb = metadata.get("echemdb", metadata)
    if not isinstance(echemdb, dict):
        return {}
    system = echemdb.get("system", {})
    if not isinstance(system, dict):
        system = {}

    flattened: dict[str, Any] = {}
    electrodes = system.get("electrodes", [])
    if isinstance(electrodes, list):
        for electrode in electrodes:
            if not isinstance(electrode, dict):
                continue
            function = str(electrode.get("function", "")).lower()
            name = str(electrode.get("name", "")).lower()
            if "working" in function or name == "we":
                flattened["working_electrode_material"] = electrode.get("material")
                flattened["working_electrode_type"] = electrode.get("type")
                flattened["working_electrode_orientation"] = electrode.get("crystallographicOrientation")
            elif "reference" in function or name == "ref":
                flattened["reference_electrode"] = electrode.get("type") or electrode.get("material")

    electrolyte = system.get("electrolyte")
    if isinstance(electrolyte, dict):
        components = electrolyte.get("components", [])
        if isinstance(components, list):
            names = [str(component.get("name")) for component in components if isinstance(component, dict) and component.get("name")]
            flattened["electrolyte"] = "; ".join(names) if names else None
        elif electrolyte.get("name"):
            flattened["electrolyte"] = electrolyte.get("name")

    source = echemdb.get("source", {})
    if isinstance(source, dict):
        flattened["doi"] = source.get("doi") or source.get("url")
        flattened["citation"] = source.get("citation") or source.get("bibdata")

    if system.get("type"):
        flattened["experiment_type"] = system.get("type")
    return {key: value for key, value in flattened.items() if value not in {"", None}}


def _extract_metadata(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    metadata: dict[str, Any] = {}
    for key, value in obj.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            metadata[key] = value
        elif isinstance(value, dict) and any(token in _clean_name(key) for token in ["meta", "electrode", "electrolyte"]):
            for child_key, child_value in value.items():
                if isinstance(child_value, (str, int, float, bool)) or child_value is None:
                    metadata[f"{key}.{child_key}"] = child_value
    return metadata


def _extract_doi(metadata: dict[str, Any]) -> str | None:
    direct = _first_metadata_value(metadata, ["doi", "DOI"])
    if direct:
        return str(direct)
    text = " ".join(str(value) for value in metadata.values())
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _first_metadata_value(metadata: dict[str, Any], keys: list[str]) -> str | None:
    cleaned = {_clean_name(key): value for key, value in metadata.items()}
    for key in keys:
        wanted = _clean_name(key)
        if wanted in cleaned and cleaned[wanted] not in {"", None}:
            return _stringify_metadata_value(cleaned[wanted])
    for key, value in metadata.items():
        cleaned_key = _clean_name(key)
        if any(_clean_name(wanted) in cleaned_key for wanted in keys) and value not in {"", None}:
            return _stringify_metadata_value(value)
    return None


def _stringify_metadata_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _numeric_columns(frame: pd.DataFrame) -> list[str]:
    if frame is None or frame.empty:
        return []
    numeric: list[str] = []
    for column in frame.columns:
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().sum() >= max(2, int(0.5 * len(frame))):
            numeric.append(str(column))
    return numeric


def _clean_name(value: Any) -> str:
    text = str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text
