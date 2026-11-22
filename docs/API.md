# Feature API

The local server exposes `POST /api/features` to extract curve descriptors using the same Python implementation as the batch pipeline. Start it with `echemdb-web --port 8765`; it binds to `127.0.0.1` and is intended for local research use, not public deployment.

## Request

Send a UTF-8 JSON object with a non-empty `rows` array. Each array element is one point. `E` and one signal column are required; the signal column is `j` for current density or `I` for current. If both `j` and `I` are present, `j` is used. Each curve must have at least 20 valid numeric points, at least two distinct potential values, and a nonzero signal. Nonnumeric or missing `E`/signal point values are dropped before these checks.

```json
{
  "rows": [
    {"id_entrada": "curve-1", "E": -0.5, "j": 0.02},
    {"id_entrada": "curve-1", "E": -0.4, "j": 0.03}
  ],
  "defaults": {
    "tipo_sinal": "current_density",
    "unidade_potencial_usada": "V",
    "unidade_sinal_usada": "mA/cm2",
    "grupo_origem": "10.1234/example"
  }
}
```

The example is abbreviated and needs at least 20 valid points per curve to execute successfully. `rows` is required. `defaults` is optional and must be an object when supplied. Rows are grouped by `id_entrada`; use a distinct ID for each curve. If IDs are omitted, every row is assigned to the same curve, `nova_curva`. Metadata may be placed on each row or supplied through `defaults`; non-empty values for a metadata field must agree within a curve.

Recognized metadata keys are `id_entrada`, `referencia`, `doi`, `material_eletrodo`, `eletrolito`, `tipo_sinal`, `unidade_potencial_usada`, `unidade_sinal_usada`, and `grupo_origem`. The `tipo_sinal` must be `current` or `current_density`; it has no valid inference default. Potential and signal units are required and are never guessed.

### Accepted units

Potential accepts `V` and `mV` (case-insensitive; whitespace is ignored) and is returned in V.

For `tipo_sinal: "current"`, accepted units are A, mA, µA/uA (also `microA`), and nA; output is in A.

For `tipo_sinal: "current_density"`, accepted current prefixes A, mA, µA/uA, and nA are supported per m² or cm². Both slash and inverse-area notation are accepted, for example `A/m2`, `mA/cm2`, `A m-2`, or `µA cm^-2`; output is in A/m². SI prefixes and area units are converted. Other or ambiguous units are rejected. No conversion between current and current density is performed.

An optional `Origin` header is accepted only when its network location matches the request `Host`. The request body must be larger than zero and no more than 20 MB. The service does not enable cross-origin access.

## Response

Success is `200 application/json`:

```json
{
  "rows": [
    {
      "id_entrada": "curve-1",
      "E_min": -0.5,
      "E_max": -0.4,
      "E_pico_anodico": null,
      "tipo_sinal": "current_density",
      "unidade_potencial_usada": "V",
      "unidade_sinal_usada": "A/m2",
      "status": "valido",
      "versao_atributos": "echemdb-features-v2",
      "hash_curva": "..."
    }
  ]
}
```

The abbreviated feature row contains the full feature-table schema: input/source metadata, point count, all 23 numeric descriptors, signal modality and canonical units, label where supplied by electrode metadata, validity status, feature version, curve hash, and source group. Undefined numeric descriptors are JSON `null` (and NaN in CSV output); they are not replaced by zero. The output `hash_curva` fingerprints the ordered, cleaned, unit-converted curve together with the signal modality.

## Errors

| HTTP status | Response | Typical causes |
| --- | --- | --- |
| `400` | JSON `{"error": "..."}` | Invalid JSON or body type; missing/empty `rows`; malformed rows; an explicitly blank ID or inconsistent metadata within a curve; missing or unsupported units; unsupported signal type; fewer than 20 valid points; fewer than two distinct potentials; all-zero signal. Bodies over 20 MB also currently return `400`. |
| `403` | Server-generated HTTP error page | An `Origin` header is present and its network location differs from `Host`. |
| `404` | Server-generated HTTP error page | The request path is not exactly `/api/features`. |

The endpoint does not currently define a separate `413` response. Error messages are intended to guide correction of local input, not to provide a stable machine-readable error code.

## Example call

```python
import json
from urllib.request import Request, urlopen

rows = [
    {"id_entrada": "synthetic", "E": -0.5 + i * 0.05, "j": 0.02 + i * 0.001}
    for i in range(21)
]
payload = {
    "rows": rows,
    "defaults": {
        "tipo_sinal": "current_density",
        "unidade_potencial_usada": "V",
        "unidade_sinal_usada": "mA/cm2",
        "grupo_origem": "10.1234/example",
    },
}
request = Request(
    "http://127.0.0.1:8765/api/features",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urlopen(request, timeout=10) as response:
    result = json.load(response)
print(result["rows"][0]["versao_atributos"])
```
