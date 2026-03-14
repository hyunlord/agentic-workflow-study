# Failure Analysis Report

- Total failure instances: 160

## Failure Distribution
- `incomplete_synthesis` (minor, stage: `synthesize_answer`): 28 - The answer captured part of the evidence but omitted key details.
- `insufficient_evidence_not_detected` (critical, stage: `fallback_or_finalize`): 13 - The workflow should have abstained but answered anyway.
- `missing_decomposition` (major, stage: `make_plan`): 19 - A multi-step question was handled without enough explicit reasoning steps.
- `query_misclassification` (major, stage: `classify_query`): 43 - The workflow selected the wrong question type for the query.
- `synthesis_quality_gap` (major, stage: `synthesize_answer`): 57 - The workflow retrieved enough evidence but failed to form a strong answer.

## Stage Distribution
- `classify_query`: 43
- `fallback_or_finalize`: 13
- `make_plan`: 19
- `synthesize_answer`: 85

## Severity Distribution
- `critical`: 13
- `major`: 119
- `minor`: 28

## Top Improvement Actions
- Tighten answer templates or add a post-synthesis rewrite step. (57)
- Expand classifier rules or replace them with a learned classifier. (43)
- Increase synthesis coverage requirements and summarize multiple evidence spans explicitly. (28)
- Force decomposition for complex queries and expose intermediate sub-goals. (19)
- Raise verifier and fallback thresholds so unsupported answers abstain earlier. (13)
