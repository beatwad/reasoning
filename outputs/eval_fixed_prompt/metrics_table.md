| Variant | n | Strict acc | Soft acc | Format ok | Truncated | Mean len | Median len | 'wait' rate | Soft acc w/ wait | Soft acc w/o wait |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 1319 | 5.38% | 45.26% | 18.12% | 1.74% | 268.6 | 259.0 | 0.08% | 0.00% | 45.30% |
| B | 1319 | 0.00% | 43.67% | 0.00% | 1.67% | 266.4 | 247.0 | 0.30% | 50.00% | 43.65% |
| C | 1319 | 50.72% | 50.87% | 98.56% | 1.36% | 214.5 | 188.0 | 98.56% | 51.46% | 10.53% |

Soft acc C − A: +5.61 pp (main metric)
Soft acc C − B: +7.20 pp (mostly format effect)
Paired A/C soft correctness: {'both_correct': 448, 'only_A': 149, 'only_C': 223, 'both_wrong': 499}
