# ChemPredict v4.4.0

English | [中文](README.md)

ChemPredict is an offline evidence-retrieval, applicability-domain, and candidate-ranking tool for asymmetric radical cyanation research. Version 4.4.0 supports quantitative output for one reaction system only: the deoxygenative asymmetric cyanation of secondary benzylic NHP ethers reported by Yu et al. in *Organic Letters* (2026). Eight related systems are registered for evidence or refusal logic and are never pooled numerically.

> This repository is an auditable research prototype, not a universal predictor for asymmetric reactions. Predictions do not replace prospective experiments, risk assessment, or analytical characterization.

## Use the tool

- Live workspace: [https://yezhanggong.github.io/ChemPredict/](https://yezhanggong.github.io/ChemPredict/)
- Offline: open `05_网站/index.html`
- Local server on Windows: `./05_网站/run-local.ps1 -Port 8788`

The web app runs entirely in the browser. It does not call a remote inference API or upload structures and experiment plans.

## Supported evidence levels

| Layer | Evidence | Output | Boundary |
| --- | ---: | --- | --- |
| Target NHP-ether cyanation | 26 same-protocol training records | Yield, ee, empirical intervals, applicability grade | Fixed protocol and secondary benzylic NHP ethers only |
| Condition evidence | 33 single-factor/control records | Reported solvent, photocatalyst, copper, ligand, and temperature observations | No additive extrapolation across multiple changes |
| Related systems | 8 registry entries | Evidence summary or refusal reason | No cross-system numerical prediction |
| Virtual library | Precomputed structures | Candidate ranking and plan export | Priority signal, not reaction-success probability |

## Model status

Version 4.4.0 uses a predeclared champion-challenger policy. Challengers integrating qmdesc, DBSTEP, differentiating structural descriptors, and XGBoost did not meet the joint promotion rule. Production therefore retains the v4.3 champion models.

| Target | Nested grouped MAE | RMSE | Maximum AE | R2 | Spearman |
| --- | ---: | ---: | ---: | ---: | ---: |
| Yield | 8.029 | 10.948 | 30.275 | -0.343 | 0.015 |
| ee | 6.180 | 10.993 | 45.207 | 0.065 | 0.620 |

The negative yield R2 and near-zero yield rank correlation mean that yield predictions are weak prioritization signals only. See the [model card](08_说明文档/模型卡_v4.4.0.md) for failure cases, interval calibration, and gate definitions.

## Minimal reproduction

```bash
python -m venv .venv
python -m pip install -r requirements-ci.txt
corepack enable
pnpm install --frozen-lockfile
python -m unittest discover -s "04_模型源码/tests" -p "test_*.py" -v
```

For browser acceptance tests, run `pnpm exec playwright install chromium`, serve `05_网站` on port 8788, and run `pnpm test:ui`. The complete descriptor and training workflow is documented in `08_说明文档/工具搭建流程_v4.4.0.md`.

## Data and provenance

Quantitative labels are transcribed from the article and Supporting Information for DOI [`10.1021/acs.orglett.5c05116`](https://doi.org/10.1021/acs.orglett.5c05116). Other publications inform methodology, mechanistic boundaries, or refusal tests only. Publisher PDFs are not redistributed. See [DATA_CARD.md](DATA_CARD.md) and `03_数据/整理数据/literature_registry.csv`.

## Contributing and roadmap

The model architecture, descriptors, parameters, applicability domain, and uncertainty calibration will continue to evolve as independently registered data become available. Reproduction reports, prospective blind tests, corrected records, and reaction-specific extensions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), [ROADMAP.md](ROADMAP.md), or [GitHub Discussions](https://github.com/yezhanggong/ChemPredict/discussions).

## License and safety

Original code and documentation are released under the [Apache License 2.0](LICENSE). Publications, literature-derived records, and third-party software remain subject to their original terms; see `08_说明文档/THIRD_PARTY_NOTICES.md`.

Experiments involving cyanide reagents or TMSCN require institutional SOPs, risk assessment, ventilation controls, and appropriate waste handling. This repository does not provide scale-up or operational safety instructions.
