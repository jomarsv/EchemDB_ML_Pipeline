# Controlled Unit-Error Example

This author-prepared example demonstrates a narrow validation behavior; it is not an external-user study and does not use an experimental voltammogram.

The fixture `examples/impact/unit_error_curve.csv` contains 21 synthetic potential/current-density points. The accompanying metadata deliberately declares `tipo_sinal: current_density` but labels the signal unit as `mA`, which denotes current rather than current density. The shared Python feature validator rejects the curve. The example then changes only `unidade_sinal_usada` to `mA/cm2` and reruns extraction; the output is accepted as `A/m2` and saved with the feature version and curve hash.

Run it from the repository root in an installed environment:

```bash
python scripts/run_unit_error_impact_demo.py \
  --input examples/impact/unit_error_curve.csv \
  --metadata examples/impact/unit_error_metadata.json \
  --output outputs/impact_unit_demo
```

The output directory must not already exist. `impact_demo.json` records the input SHA-256, rejection message, corrected canonical units, selected descriptors, and curve hash. `corrected_features.csv` contains the complete extracted row. To run the automated check, use `python -m unittest tests.test_impact_unit_demo -v`.

The example shows that the software rejects a dimensionally incompatible label before returning a feature row. It does not detect plausible but incorrect declarations, such as confusing V with mV when both are valid potential units; it cannot infer the true units from the curve. It also does not establish external adoption, productivity gains, or scientific conclusions about an experimental record.
