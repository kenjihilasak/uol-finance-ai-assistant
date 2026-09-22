# Triage evaluation

This evaluation measures classification, routing and generation safety. It is
separate from [retrieval evaluation](../stage_05_retrieval/retrieval-evaluation.md),
which uses Recall@k and MRR.

## Dataset

The reviewed development dataset contains 21 synthetic enquiries covering:

- four answerable categories;
- supported enquiries with missing information;
- unsupported and ambiguous enquiries;
- mixed supported and sensitive intent; and
- six sensitive cases requiring specialist referral.

The dataset is
[`triage_cases_v2.json`](../../evaluation/datasets/triage_cases_v2.json).

## Results

| Metric | Result |
| --- | ---: |
| Category accuracy | 1.000 |
| Action accuracy | 0.905 |
| Route accuracy | 0.762 |
| Generation-gate accuracy | 0.952 |
| Sensitive recall | 1.000 |
| Sensitive precision | 0.857 |
| Sensitive specificity | 0.933 |
| Sensitive false positives | 1 |
| Sensitive generation leaks | 0 |

All six sensitive cases blocked retrieval and generation. One non-incident
policy-research enquiry containing `harassment` was conservatively referred,
creating one false positive. Other disagreements mainly concerned
organisational ownership, such as Finance team versus Finance information,
rather than unsafe generation.

## Interpretation

- The five-category contract classified all 21 cases correctly.
- The safety gate produced no sensitive generation leaks.
- Route accuracy is the weakest metric and requires domain-owner agreement.
- The false positive shows the cost of conservative keyword rules.
- Independent institutional review remains pending; these are development
  results, not production evidence.

The versioned output is
[`triage_v2.json`](../../evaluation/baselines/triage_v2.json).

## Reproduce

Validate locally without calling Azure:

```bash
python -m scripts.stage_06_triage.evaluate_triage \
  --dataset evaluation/datasets/triage_cases_v2.json
```

Run the live classifier evaluation:

```bash
python -m scripts.stage_06_triage.evaluate_triage \
  --dataset evaluation/datasets/triage_cases_v2.json \
  --live --output data/evaluation/triage_v2.results.json
```

Implementation:
[`evaluate_triage.py`](../../scripts/stage_06_triage/evaluate_triage.py).

Return to the [triage overview](enquiry-triage.md).
