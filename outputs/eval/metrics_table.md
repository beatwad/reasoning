| Variant | n | Strict acc | Soft acc | Format ok | Truncated | Mean len | Median len | 'wait' rate | Soft acc w/ wait | Soft acc w/o wait |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 1319 | 5.76% | 45.11% | 18.20% | 1.44% | 266.4 | 257.0 | 0.08% | 0.00% | 45.14% |
| B | 1319 | 0.00% | 45.34% | 0.00% | 1.90% | 268.1 | 251.0 | 0.15% | 50.00% | 45.33% |
| C | 1319 | 48.37% | 48.67% | 97.42% | 2.58% | 352.9 | 323.0 | 69.22% | 50.16% | 45.32% |

Soft acc C − A: +3.56 pp (main metric)
Soft acc C − B: +3.34 pp (mostly format effect)
Paired A/C soft correctness: {'both_correct': 448, 'only_A': 147, 'only_C': 194, 'both_wrong': 530}
