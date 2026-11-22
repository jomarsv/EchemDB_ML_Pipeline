# EchemDB ML Pipeline

- **Version:** 0.1.2
- **License:** MIT ([LICENSE](LICENSE))
- **Python:** 3.10 or later
- **Platforms:** Linux, macOS, and Windows

EchemDB ML Pipeline imports cyclic-voltammetry records from CSV, JSON, or EchemDB-style data packages; checks declared units and signal modality; computes versioned descriptors; and supports interactive review and exploratory analysis. It includes a Python command-line pipeline, a local browser application, a feature-extraction API, and a separate source-grouped nested-validation workflow.

The software does not download or invent input data. Users provide local files or an exported EchemDB data package. Current and current density remain distinct, potential references are not silently harmonized, and unknown units are rejected rather than guessed. Browser classifiers are exploratory and do not establish generalization; see the limitations and validation notes below.

## Install

Install from a source checkout with Python 3.10 or later:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Linux or macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the application and test tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The project is also configured for standard wheel/sdist builds with setuptools. The `echemdb-ml-pipeline` and `echemdb-web` commands are installed by this package.

## Run the pipeline

Use a local directory or file containing CSV/JSON records:

```bash
echemdb-ml-pipeline --input /path/to/echemdb-export --output outputs --skip-models
```

On Windows, use a quoted path such as `--input "D:\data\echemdb-export"`. Omit `--skip-models` to run the available exploratory analyses. Optional settings include:

```bash
echemdb-ml-pipeline --input data --output outputs --n-points 256 --min-points 20 --normalization max_abs
```

The pipeline writes indexed and cleaned data, quality-control results, feature tables, interpolated curves, reports, and (when enough data are available) exploratory model summaries and plots. Output paths are relative to the current working directory unless an absolute path is provided.

## Run the local browser application

```bash
echemdb-web --port 8765
```

Open <http://127.0.0.1:8765/>. The server binds to loopback only and is intended for local use; it is not an authenticated or production web service. Keep it off public network interfaces. Curve uploads use the local `/api/features` endpoint so the browser and batch pipeline share the Python feature extractor. Opening `app/index.html` directly does not provide this API.

The request/response schema, required and optional metadata, unit spellings, limits, and error behavior are specified in [docs/API.md](docs/API.md).

The deliberate unit-metadata fault-injection example, its limitations, and reproduction steps are described in [docs/impact-example.md](docs/impact-example.md).

Import pipeline outputs such as `outputs/atributos_voltamogramas.csv`, `outputs/dados_limpos.csv`, and `outputs/controle_qualidade.csv`. Browser models include weighted k-nearest neighbors, nearest centroid, Gaussian naive Bayes, decision tree, random forest, and a weighted ensemble. Their displayed validation is an exploratory, source-disjoint development split; it is not the DOI-grouped nested Python pilot and must not be interpreted as confirmatory evidence.

## Tests and continuous integration

The Python test suite uses `pytest`; browser integrity tests use the Node.js built-in test runner (Node 20 or later):

```bash
python -m pytest -q
node --test tests/scientific-integrity.test.cjs
```

GitHub Actions runs both suites on Linux, macOS, and Windows with Python 3.10 and 3.12. Tests that require generated local pilot outputs are skipped when those optional artifacts are absent.

## Reproducibility and scope

The DOI-grouped Ag/Au case study is a small exploratory pilot, not a confirmatory estimate of performance on new materials or publications. It uses a separately documented environment and source-grouped nested validation. Its inputs, manifests, fold assignments, model selections, and predictions are archived in Supplementary Material S1 v3 at <https://doi.org/10.5281/zenodo.24438074>. The software release and source tag are cited below; check the manuscript's reproduction table for exact commands and dependencies.

The descriptor contract is versioned as `echemdb-features-v2`. Descriptor definitions, units, missing-value rules, and synthetic peak-sensitivity tests are described in the manuscript and `tests/test_descriptor_reference_traces.py`.

## Citation

Jomar Sales Vasconcelos, Nazaré do Socorro L. S. Vasconcelos, Arthur Aprígio de Melo, and Antonio Marcus N. Lima. *EchemDB ML Pipeline: A reproducible workflow for cyclic voltammetry data curation and machine-learning analysis*, version 0.1.2, Zenodo (2026). The version-specific DOI will be added after the Zenodo archive is published. Concept DOI: <https://doi.org/10.5281/zenodo.23264071>.
