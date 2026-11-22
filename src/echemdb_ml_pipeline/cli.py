"""Command-line interface for the EchemDB ML Pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build feature tables and reports from local electrochemistry data."
    )
    parser.add_argument("--input", required=True, help="File or directory containing CSV/JSON data.")
    parser.add_argument("--output", default="outputs", help="Output directory (default: outputs).")
    parser.add_argument("--skip-models", action="store_true", help="Extract data without fitting exploratory models.")
    parser.add_argument("--n-points", type=int, default=256, help="Interpolated points per curve.")
    parser.add_argument("--min-points", type=int, default=20, help="Minimum numeric points per curve.")
    parser.add_argument(
        "--normalization",
        choices=["none", "max_abs", "zscore", "minmax", "area"],
        default="max_abs",
        help="Normalization for interpolated signal vectors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_pipeline(
        input_path=Path(args.input),
        output_dir=Path(args.output),
        n_points=args.n_points,
        min_points=args.min_points,
        normalization=args.normalization,
        skip_models=args.skip_models,
    )
    print("Pipeline finished.")
    print(f"Records loaded: {summary['records_loaded']}")
    print(f"Valid records: {summary['valid_records']}")
    print(f"Output directory: {summary['output_dir']}")
