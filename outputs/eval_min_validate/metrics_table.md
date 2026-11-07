| Variant | n | Strict acc | Soft acc | Format ok | Truncated | Mean len | Median len | 'wait' rate | Soft acc w/ wait | Soft acc w/o wait |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 1319 | 5.69% | 44.96% | 18.65% | 1.52% | 269.5 | 258.0 | 0.08% | 0.00% | 44.99% |
| B | 1319 | 0.00% | 45.56% | 0.00% | 1.82% | 263.7 | 245.0 | 0.23% | 33.33% | 45.59% |
| C | 1319 | 50.04% | 50.72% | 97.12% | 1.82% | 311.2 | 288.0 | 0.38% | 60.00% | 50.68% |

Soft acc C − A: +5.76 pp (main metric)
Soft acc C − B: +5.16 pp (mostly format effect)
Paired A/C soft correctness: {'both_correct': 466, 'only_A': 127, 'only_C': 203, 'both_wrong': 523}
