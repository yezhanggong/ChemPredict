# Contributing to ChemPredict

ChemPredict welcomes reproducibility reports, prospective validation, data corrections, reaction-specific extensions, and improvements to model structure or parameters.

## Before opening an issue

1. Confirm the exact release and model artifact used.
2. Separate literature observations from model predictions.
3. State whether the reaction is inside the registered NHP-ether cyanation system.
4. Remove confidential structures, personal information, and unpublished restricted data.
5. For experimental discrepancies, include the analytical method and distinguish isolated yield, assay yield, conversion, and trace/censored outcomes.

Use GitHub Discussions for open-ended method questions. Use Issues for reproducible defects, data corrections, validation records, or scoped feature proposals.

## Contributing experimental data

Start from `03_数据/整理数据/prospective_blind_test_template.csv`. A usable record should include:

- frozen ChemPredict version and artifact hash;
- substrate identity and machine-readable structure;
- precursor type, radical class, and reaction family;
- full protocol and every changed condition factor;
- isolated yield and ee with analytical method;
- replicate count, censoring status, and failure notes;
- permission to redistribute the submitted record.

New data are not merged directly into training. They first enter a dated, immutable validation set. Promotion to training requires provenance review, duplicate checks, and a documented split policy.

## Adding a reaction system

A new system must receive its own registry entry, mechanism statement, protocol identity, data schema, applicability rules, and validation report. Cross-system pooling is prohibited unless a preregistered transfer experiment demonstrates benefit on a held-out system.

## Model changes

Model or descriptor changes must report grouped nested validation, maximum absolute error, failure cases, and comparison with the frozen production champion. A candidate is not promoted solely because training error improves. The current minimum rule is at least 0.30 percentage-point MAE improvement per target with non-worse RMSE and maximum absolute error.

## Development workflow

```bash
python -m pip install -r requirements-ci.txt
corepack enable
pnpm install --frozen-lockfile
python -m unittest discover -s "04_模型源码/tests" -p "test_*.py" -v
```

Run the browser test when changing `05_网站`, serialized artifacts, registries, translations, or inference logic. Keep source publications and private laboratory records out of commits.

## Pull requests

Pull requests should explain the scientific rationale, changed data or behavior, applicability impact, and validation performed. Keep unrelated formatting or generated-file churn out of the same change. By contributing, you agree that your original contribution is licensed under Apache-2.0 and that you have the right to submit any included data.
