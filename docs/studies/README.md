# Studies

Bounded empirical reports belong here, with code in `src/eda/`, artifacts in `data/studies/<study_name>/`, and relevant tests in `test/<study_name>/`. Record question, dataset/version, method, results, limitations, and decision status. A study result is not a production decision.

| Study | What it covers |
|---|---|
| [Public data dump](public_data_dump/README.md) | Acquisition run of the public tennis sources (2010+, recency emphasised): what was retrieved, what was not, how it is organised, coverage by source and tier, and the [proposed target structure](public_data_dump/structure-plan.md) for the cleaning/merge phase |
| [Merge feasibility](merge_feasibility/README.md) | How the staged sources join (overlap, player identity, link rates of odds, markets, charts and points, date precision, statistics), at what scale versus the UFC project, and a proposed layered database structure with identity-first merging and running-state features |
| [Career coverage](career_coverage/README.md) | Ten randomly drawn Challenger players' whole careers checked match by match against the official ATP record: share in the dump by player, level and season, why matches are missing, depth of in-match data, and source defects found on the way; with an HTML [report](career_coverage/report.html) for non-specialist readers |
