# ChemPredict Roadmap

ChemPredict will continue to optimize model structure, descriptors, parameters, applicability-domain logic, and uncertainty calibration. Priorities are ordered by scientific value rather than interface novelty.

## Near term

- Collect preregistered, same-protocol prospective tests that were not used for tuning.
- Add immutable artifact hashes and data-snapshot identifiers to every exported prediction.
- Expand automated checks for transcription provenance, duplicate structures, unit consistency, and label censoring.
- Improve English documentation and machine-readable reaction-system metadata.
- Package the browser workspace as an optional Android application only after the web model is independently validated.

## Model development

- Re-evaluate production promotion after at least 20 new same-protocol records are available.
- Replace product-scaffold steric proxies with verified ligand/substrate 3D descriptors when the L1 structure and relevant conformational assumptions are available.
- Compare hierarchical and multitask transfer only with reaction-system-level holdout, never random pooled validation.
- Evaluate calibrated ensembles and conformal methods on a permanent prospective test set.
- Introduce active-learning acquisition functions that optimize information gain while retaining chemist review and safety constraints.

## Reaction coverage

- Add reaction-specific evidence workspaces before adding any new numerical head.
- Require a minimum data and protocol standard for solvent/catalyst response surfaces.
- Preserve explicit refusal for different precursor classes, radical classes, and product-forming mechanisms until external transfer is demonstrated.

## Community participation

Discussion is especially welcome on blind-test design, descriptor semantics, uncertainty calibration, negative-result reporting, and interoperable reaction schemas. Use GitHub Discussions for proposals and open an Issue when a proposal has a testable acceptance criterion.
