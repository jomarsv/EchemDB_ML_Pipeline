from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from echemdb_ml_pipeline.features import NUMERIC_FEATURES, _extract_features, _clean_curve
from echemdb_ml_pipeline.schema import CurveRecord


EXPECTED_ARCHIVE_MD5 = "18acef4c0208f18024aaf67ff63c4f90"
TOLERANCE = 1e-10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute cohort descriptors from the verified EchemDB 0.9.2 archive."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=REPO_ROOT / "outputs/upstream_echemdb_0_9_2/data-0.9.2.zip",
    )
    parser.add_argument(
        "--feature-table",
        action="append",
        type=Path,
        help="Local feature table; may be supplied more than once.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs/upstream_curve_descriptor_audit_v2",
    )
    args = parser.parse_args()

    archive_path = args.archive.resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_md5 = hashlib.md5(archive_path.read_bytes()).hexdigest()
    if archive_md5 != EXPECTED_ARCHIVE_MD5:
        raise ValueError(f"Unexpected EchemDB archive MD5: {archive_md5}")

    table_paths = args.feature_table or [
        REPO_ROOT / "outputs/scientific_v2/atributos_voltamogramas.csv",
        REPO_ROOT / "outputs/release_0_9_2_audit/atributos_voltamogramas.csv",
    ]
    tables = []
    for table_path in table_paths:
        resolved = table_path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        table = pd.read_csv(resolved).set_index("id_entrada", drop=False)
        tables.append((resolved, table))

    audit_rows = pd.read_csv(REPO_ROOT / "reproducibility_capsule/curve_id_audit.csv")
    provenance: dict[str, dict] = {}
    failures: list[dict[str, str]] = []
    with zipfile.ZipFile(archive_path) as archive:
        for audit_row in audit_rows.to_dict(orient="records"):
            curve_id = audit_row["curve_id"]
            source_key = audit_row["source_key"]
            prefix = f"data/generated/svgdigitizer/{source_key}/{curve_id}"
            csv_path, json_path = f"{prefix}.csv", f"{prefix}.json"
            try:
                csv_bytes = archive.read(csv_path)
                metadata = json.loads(archive.read(json_path))
                resource = metadata["resources"][0]
                fields = resource["schema"]["fields"]
                units = {field["name"]: field.get("unit") for field in fields}
                frame = pd.read_csv(io.BytesIO(csv_bytes))
                echemdb = resource["metadata"]["echemdb"]
                source = echemdb["source"]
                system = echemdb["system"]
                potential_field = next(
                    field for field in fields
                    if field["name"] in frame.columns
                    and field["name"].casefold() in {"e", "potential", "potential_v"}
                )
                time_field = next(
                    (field for field in fields if field["name"].casefold() in {"t", "time"}),
                    None,
                )
                signal_candidates = [
                    field for field in fields
                    if field["name"] in frame.columns
                    and field["name"] != potential_field["name"]
                    and (time_field is None or field["name"] != time_field["name"])
                ]
                signal_field = next(
                    (field for field in signal_candidates
                     if field["name"].casefold() in {"j", "i", "current", "current_density"}),
                    signal_candidates[0] if len(signal_candidates) == 1 else None,
                )
                if signal_field is None:
                    raise ValueError("could not identify a unique signal column")
                signal_unit = str(signal_field.get("unit", ""))
                normalized_signal_unit = signal_unit.casefold().replace(" ", "")
                signal_kind = (
                    "current_density"
                    if "/" in normalized_signal_unit or "-2" in normalized_signal_unit
                    else "current"
                )
                working = next(
                    (electrode for electrode in system.get("electrodes", [])
                     if electrode.get("function") == "working electrode"),
                    {},
                )
                reference = potential_field.get("reference")
                record = CurveRecord(
                    entry_id=curve_id,
                    reference=reference,
                    doi=source.get("url"),
                    material_electrode=working.get("material"),
                    electrolyte=None,
                    experiment_type="CV",
                    units=units,
                    frame=frame,
                    potential_col=potential_field["name"],
                    signal_col=signal_field["name"],
                    time_col=time_field["name"] if time_field else None,
                    signal_kind=signal_kind,
                    raw_metadata={"grupo_origem": source.get("url")},
                )
                clean, status, reason = _clean_curve(record, min_points=20)
                if clean is None:
                    raise ValueError(f"pipeline cleaning rejected record: {reason}")
                record_features = _extract_features(record, clean, status)
                figure_fields = echemdb.get("figureDescription", {}).get("fields", [])
                figure_signal = next(
                    (field.get("unit") for field in figure_fields
                     if field.get("orientation") == "vertical"),
                    None,
                )
                provenance[curve_id] = {
                    "archive_csv": csv_path,
                    "archive_json": json_path,
                    "source_key": source_key,
                    "points_in_csv": len(frame),
                    "points_after_pipeline_cleaning": len(clean),
                    "potential_column": potential_field["name"],
                    "signal_column": signal_field["name"],
                    "signal_kind": signal_kind,
                    "schema_units": units,
                    "figure_signal_unit": figure_signal,
                    "reference_electrode": reference,
                    "working_electrode": working.get("material"),
                    "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
                    "recomputed_features": record_features,
                }
            except Exception as exc:  # Keep failures explicit and audit remaining records.
                failures.append({"curve_id": curve_id, "archive_csv": csv_path, "error": str(exc)})

    comparison_rows: list[dict] = []
    mismatches = 0
    for table_path, table in tables:
        table_name = str(table_path)
        for curve_id in provenance:
            if curve_id not in table.index:
                failures.append({"curve_id": curve_id, "table": table_name, "error": "missing from local feature table"})
                continue
            local = table.loc[curve_id]
            recomputed = provenance[curve_id]["recomputed_features"]
            for column in NUMERIC_FEATURES:
                local_value = pd.to_numeric(pd.Series([local.get(column)]), errors="coerce").iloc[0]
                upstream_value = recomputed.get(column)
                if pd.isna(local_value) and pd.isna(upstream_value):
                    matches = True
                    difference = None
                elif pd.isna(local_value) or pd.isna(upstream_value):
                    matches = False
                    difference = None
                else:
                    difference = float(abs(float(local_value) - float(upstream_value)))
                    scale = max(1.0, abs(float(local_value)), abs(float(upstream_value)))
                    matches = difference <= TOLERANCE * scale
                mismatches += int(not matches)
                comparison_rows.append(
                    {
                        "table": table_name,
                        "curve_id": curve_id,
                        "feature": column,
                        "local_value": local_value,
                        "recomputed_from_archive": upstream_value,
                        "absolute_difference": difference,
                        "matches_tolerance": matches,
                    }
                )

    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit directory: {args.output}")
    args.output.mkdir(parents=True)
    pd.DataFrame(comparison_rows).to_csv(args.output / "descriptor_comparison.csv", index=False)
    mismatch_counts = {}
    if comparison_rows:
        mismatch_counts = (
            pd.DataFrame(comparison_rows)
            .query("matches_tolerance == False")
            .groupby("table")["feature"]
            .count()
            .to_dict()
        )
    report = {
        "protocol": "upstream-archive-descriptor-audit-v2",
        "archive": str(archive_path),
        "archive_md5": archive_md5,
        "archive_sha256": sha256(archive_path),
        "cohort_curve_ids": audit_rows["curve_id"].tolist(),
        "curves_recomputed": len(provenance),
        "curve_failures": failures,
        "descriptor_tolerance_relative": TOLERANCE,
        "metadata_and_recomputed_curves": provenance,
        "local_feature_tables": [
            {"path": str(path), "sha256": sha256(path)} for path, _ in tables
        ],
        "numeric_feature_values_compared": len(comparison_rows),
        "numeric_feature_value_mismatches": mismatches,
        "mismatches_by_local_table": mismatch_counts,
        "interpretation": "Recomputed descriptors use signal and potential units from each archive table schema; figure-axis units are recorded separately. Any curve that cannot be processed is listed in curve_failures.",
    }
    (args.output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"AUDIT_OUTPUT={args.output.resolve()}")
    print(f"CURVES_RECOMPUTED={len(provenance)}")
    print(f"CURVE_FAILURES={len(failures)}")
    print(f"NUMERIC_FEATURE_VALUES_COMPARED={len(comparison_rows)}")
    print(f"NUMERIC_FEATURE_VALUE_MISMATCHES={mismatches}")
    print(f"DETAILS={ (args.output / 'descriptor_comparison.csv').resolve() }")


if __name__ == "__main__":
    main()
