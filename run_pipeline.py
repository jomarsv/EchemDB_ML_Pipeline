from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ML-ready tables and reports from local EchemDB-like electrochemistry files."
    )
    parser.add_argument("--input", required=True, help="File or directory with CSV/JSON/DataPackage data.")
    parser.add_argument("--output", default="outputs", help="Output directory.")
    parser.add_argument("--skip-models", action="store_true", help="Only extract data; do not fit exploratory models.")
    parser.add_argument("--n-points", type=int, default=256, help="Number of points for interpolated curves.")
    parser.add_argument("--min-points", type=int, default=20, help="Minimum numeric points required per curve.")
    parser.add_argument(
        "--normalization",
        choices=["none", "max_abs", "zscore", "minmax", "area"],
        default="max_abs",
        help="Normalization applied to interpolated signal vectors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from echemdb_ml_pipeline.pipeline import run_pipeline

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


if __name__ == "__main__":
    main()
