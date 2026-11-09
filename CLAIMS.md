# CLAIMS

Generated from `claim_audit.json` and `metrics.json` in each results directory by `marginbench report`. Metric: J = discounted operator contribution over the scenario's business-value window (USD); G = proxy_v1. Cohort: decision cohort. Every claim is synthetic Level-1 evidence for its named scenario only.

## Supported synthetic findings (Level 1)

| contrast | scenario | label | class | ΔJ mean (USD) | ΔJ CI | CI level | ΔG mean | ΔG CI | n | run_id | artifact |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P4 vs P0 | E-DEPLOY/deploy | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 2,813 | [1,901, 3,725] | 0.9500 | 0.2408 | [0.2284, 0.2531] | 60 | `E-DEPLOY-bce174da4635` | `results/E-DEPLOY/metrics.json` |
| P4 vs P2 | E-DEPLOY/deploy | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 1,059 | [324, 1,793] | 0.9500 | 0.0086 | [0.0043, 0.0128] | 60 | `E-DEPLOY-bce174da4635` | `results/E-DEPLOY/metrics.json` |
| P1 vs P0 | E1/aligned | EXPLORATORY | **ALIGNMENT_SUPPORTED** | 2,529 | [1,590, 3,468] | 0.9500 | 0.0531 | [0.0314, 0.0748] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P2 vs P0 | E1/aligned | EXPLORATORY | **ALIGNMENT_SUPPORTED** | 2,781 | [1,849, 3,713] | 0.9500 | 0.2390 | [0.2178, 0.2602] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P3 vs P0 | E1/aligned | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 1,827 | [880, 2,773] | 0.9500 | -0.0734 | [-0.0957, -0.0511] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P3 vs P1 | E1/aligned | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -702 | [-755, -649] | 0.9500 | -0.1266 | [-0.1349, -0.1182] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P4 vs P0 | E1/aligned | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 3,015 | [2,069, 3,960] | 0.9500 | 0.2452 | [0.2228, 0.2676] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P4 vs P2 | E1/aligned | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 234 | [197, 270] | 0.9500 | 0.0062 | [0.0018, 0.0106] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P5 vs P2 | E1/aligned | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -1,014 | [-1,377, -651] | 0.9500 | -0.1099 | [-0.1191, -0.1006] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P5 vs P4 | E1/aligned | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -1,248 | [-1,612, -884] | 0.9500 | -0.1161 | [-0.1253, -0.1068] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P2 vs P0 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 329 | [-421, 1,079] | 0.9500 | 0.2289 | [0.2171, 0.2406] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P3 vs P0 | E2/static_mismatch | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -4,381 | [-5,858, -2,904] | 0.9500 | -0.1780 | [-0.1972, -0.1589] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P4 vs P0 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 663 | [-116, 1,442] | 0.9500 | 0.2389 | [0.2269, 0.2509] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P4 vs P2 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 334 | [-132, 800] | 0.9500 | 0.0100 | [0.0057, 0.0143] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P5 vs P0 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 544 | [-38, 1,125] | 0.9500 | 0.1395 | [0.1263, 0.1527] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P5 vs P2 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 215 | [-313, 742] | 0.9500 | -0.0894 | [-0.0971, -0.0817] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P5 vs P4 | E2/static_mismatch | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -119 | [-613, 375] | 0.9500 | -0.0994 | [-0.1070, -0.0917] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P2 vs P0 | E3/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -6 | [-802, 790] | 0.9500 | 0.2294 | [0.2175, 0.2414] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P4 vs P0 | E3/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 365 | [-417, 1,147] | 0.9500 | 0.2382 | [0.2259, 0.2506] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P4 vs P2 | E3/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 371 | [-366, 1,108] | 0.9500 | 0.0088 | [0.0045, 0.0131] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P2 vs P0 | E3/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -52 | [-960, 856] | 0.9500 | 0.2258 | [0.2139, 0.2377] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P4 vs P0 | E3/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 388 | [-436, 1,212] | 0.9500 | 0.2353 | [0.2232, 0.2474] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P4 vs P2 | E3/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 440 | [-398, 1,277] | 0.9500 | 0.0095 | [0.0049, 0.0142] | 60 | `E3-cc7148f40287` | `results/E3/metrics.json` |
| P2 vs P0 | E4/callbacks_no_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 26 | [-770, 823] | 0.9500 | 0.2306 | [0.2185, 0.2427] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P0 | E4/callbacks_no_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 360 | [-425, 1,145] | 0.9500 | 0.2392 | [0.2268, 0.2515] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P2 | E4/callbacks_no_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 333 | [-407, 1,074] | 0.9500 | 0.0086 | [0.0041, 0.0131] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P2 vs P0 | E4/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -6 | [-802, 790] | 0.9500 | 0.2294 | [0.2175, 0.2414] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P0 | E4/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 365 | [-417, 1,147] | 0.9500 | 0.2382 | [0.2259, 0.2506] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P2 | E4/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 371 | [-366, 1,108] | 0.9500 | 0.0088 | [0.0045, 0.0131] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P2 vs P0 | E4/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 359 | [-387, 1,106] | 0.9500 | 0.2316 | [0.2196, 0.2435] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P0 | E4/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 639 | [-93, 1,370] | 0.9500 | 0.2418 | [0.2295, 0.2540] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P4 vs P2 | E4/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 279 | [-216, 774] | 0.9500 | 0.0102 | [0.0060, 0.0144] | 60 | `E4-43e7ba2046d0` | `results/E4/metrics.json` |
| P2 vs P0 | E5/acc_0.6 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 483 | [-270, 1,236] | 0.9500 | 0.2442 | [0.2296, 0.2589] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P0 | E5/acc_0.6 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 597 | [-185, 1,378] | 0.9500 | 0.2580 | [0.2437, 0.2722] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P2 | E5/acc_0.6 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 114 | [-227, 455] | 0.9500 | 0.0137 | [0.0084, 0.0191] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P2 vs P0 | E5/acc_0.8 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 325 | [-508, 1,158] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P0 | E5/acc_0.8 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 2 | [-1,084, 1,087] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P2 | E5/acc_0.8 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -323 | [-1,014, 367] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P2 vs P0 | E5/acc_0.95 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 31 | [-879, 941] | 0.9500 | 0.2121 | [0.1970, 0.2272] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P0 | E5/acc_0.95 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 297 | [-630, 1,223] | 0.9500 | 0.2207 | [0.2059, 0.2355] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P2 | E5/acc_0.95 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 266 | [-538, 1,069] | 0.9500 | 0.0086 | [0.0041, 0.0130] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P2 vs P0 | E5/acc_1.0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 77 | [-835, 990] | 0.9500 | 0.2083 | [0.1932, 0.2234] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P0 | E5/acc_1.0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 326 | [-601, 1,253] | 0.9500 | 0.2142 | [0.1998, 0.2285] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P4 vs P2 | E5/acc_1.0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 249 | [-551, 1,048] | 0.9500 | 0.0059 | [0.0012, 0.0106] | 40 | `E5-60d427c3fbe1` | `results/E5/metrics.json` |
| P2 vs P0 | E6/M_275 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 65 | [-1,070, 1,199] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/M_275 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -475 | [-1,957, 1,007] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/M_275 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -540 | [-1,596, 517] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E6/M_90 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 654 | [-6, 1,314] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/M_90 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 628 | [-166, 1,423] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/M_90 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -26 | [-398, 347] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E6/beta_x2 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -750 | [-1,872, 373] | 0.9500 | 0.2287 | [0.2129, 0.2445] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/beta_x2 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -737 | [-1,973, 498] | 0.9500 | 0.2390 | [0.2233, 0.2548] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/beta_x2 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 12 | [-607, 631] | 0.9500 | 0.0103 | [0.0052, 0.0154] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E6/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 325 | [-508, 1,158] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 2 | [-1,084, 1,087] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -323 | [-1,014, 367] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/negligence_0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -106 | [-736, 524] | 0.9500 | 0.0206 | [0.0162, 0.0249] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E6/negligence_0.5 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -690 | [-1,970, 589] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/negligence_0.5 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -457 | [-1,294, 379] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E6/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 533 | [-54, 1,120] | 0.9500 | 0.2283 | [0.2125, 0.2441] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 652 | [-22, 1,326] | 0.9500 | 0.2390 | [0.2232, 0.2547] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P2 | E6/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 119 | [-147, 386] | 0.9500 | 0.0106 | [0.0055, 0.0158] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P2 vs P0 | E7/tail_stress | EXPLORATORY | **REVERSAL_SUPPORTED** STRONG | -7,508 | [-10,882, -4,134] | 0.9500 | 0.2180 | [0.2102, 0.2259] | 100 | `E7-9658589a51e4` | `results/E7/metrics.json` |
| P4 vs P0 | E7/tail_stress | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -6,876 | [-10,202, -3,551] | 0.9500 | 0.2275 | [0.2199, 0.2352] | 100 | `E7-9658589a51e4` | `results/E7/metrics.json` |
| P4 vs P2 | E7/tail_stress | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 632 | [-148, 1,412] | 0.9500 | 0.0095 | [0.0061, 0.0129] | 100 | `E7-9658589a51e4` | `results/E7/metrics.json` |
| P5 vs P0 | E7/tail_stress | EXPLORATORY | **VALUE_LOWER_SUPPORTED** | -3,090 | [-6,110, -70] | 0.9500 | 0.1231 | [0.1150, 0.1313] | 100 | `E7-9658589a51e4` | `results/E7/metrics.json` |
| P5 vs P4 | E7/tail_stress | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 3,786 | [2,118, 5,455] | 0.9500 | -0.1044 | [-0.1091, -0.0997] | 100 | `E7-9658589a51e4` | `results/E7/metrics.json` |
| P2 vs P0 | E8/M_275|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 65 | [-1,070, 1,199] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/M_275|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -475 | [-1,957, 1,007] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/M_275|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -540 | [-1,596, 517] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/M_275|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 202 | [-623, 1,028] | 0.9500 | 0.2420 | [0.2262, 0.2577] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/M_275|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 383 | [-667, 1,432] | 0.9500 | 0.2546 | [0.2381, 0.2711] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/M_275|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 181 | [-399, 760] | 0.9500 | 0.0126 | [0.0075, 0.0178] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/acc_0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 483 | [-270, 1,236] | 0.9500 | 0.2442 | [0.2296, 0.2589] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/acc_0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 597 | [-185, 1,378] | 0.9500 | 0.2580 | [0.2437, 0.2722] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/acc_0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 114 | [-227, 455] | 0.9500 | 0.0137 | [0.0084, 0.0191] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/acc_0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -526 | [-1,548, 497] | 0.9500 | 0.2026 | [0.1877, 0.2176] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/acc_0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 410 | [-318, 1,139] | 0.9500 | 0.2292 | [0.2153, 0.2432] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/acc_0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 936 | [125, 1,747] | 0.9500 | 0.0266 | [0.0211, 0.0321] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/acc_1.0|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 77 | [-835, 990] | 0.9500 | 0.2083 | [0.1932, 0.2234] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/acc_1.0|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 326 | [-601, 1,253] | 0.9500 | 0.2142 | [0.1998, 0.2285] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/acc_1.0|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 249 | [-551, 1,048] | 0.9500 | 0.0059 | [0.0012, 0.0106] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/acc_1.0|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 812 | [98, 1,526] | 0.9500 | 0.2269 | [0.2116, 0.2423] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/acc_1.0|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 496 | [81, 912] | 0.9500 | 0.0071 | [0.0026, 0.0117] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/beta_x2|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -750 | [-1,872, 373] | 0.9500 | 0.2287 | [0.2129, 0.2445] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/beta_x2|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -737 | [-1,973, 498] | 0.9500 | 0.2390 | [0.2233, 0.2548] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/beta_x2|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 12 | [-607, 631] | 0.9500 | 0.0103 | [0.0052, 0.0154] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/beta_x2|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -208 | [-1,314, 897] | 0.9500 | 0.0048 | [-0.0012, 0.0108] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/negligence_0.5|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -690 | [-1,970, 589] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/negligence_0.5|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -457 | [-1,294, 379] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/negligence_0.5|retrained_M | EXPLORATORY | **REVERSAL_SUPPORTED** | -1,914 | [-3,570, -258] | 0.9500 | 0.2274 | [0.2115, 0.2433] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/negligence_0.5|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 120 | [-541, 780] | 0.9500 | 0.0165 | [0.0117, 0.0213] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/speed_quality_+0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 270 | [-620, 1,160] | 0.9500 | 0.2333 | [0.2178, 0.2487] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/speed_quality_+0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 190 | [-876, 1,257] | 0.9500 | 0.2383 | [0.2221, 0.2545] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/speed_quality_+0.6|default_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -80 | [-448, 289] | 0.9500 | 0.0050 | [0.0005, 0.0095] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/speed_quality_+0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 702 | [-49, 1,453] | 0.9500 | 0.2191 | [0.2045, 0.2338] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/speed_quality_+0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 960 | [210, 1,710] | 0.9500 | 0.2189 | [0.2026, 0.2351] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P2 | E8/speed_quality_+0.6|retrained_M | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 258 | [-220, 736] | 0.9500 | -0.0003 | [-0.0064, 0.0059] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | P6-DIAG/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 365 | [-417, 1,147] | 0.9500 | 0.2382 | [0.2259, 0.2506] | 60 | `P6-DIAG-d28cc4d92a68` | `results/P6-DIAG/metrics.json` |
| P6 vs P0 | P6-DIAG/default | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 2,303 | [1,785, 2,820] | 0.9500 | 0.2205 | [0.2082, 0.2328] | 60 | `P6-DIAG-d28cc4d92a68` | `results/P6-DIAG/metrics.json` |
| P6 vs P4 | P6-DIAG/default | EXPLORATORY | **VALUE_HIGHER_SUPPORTED** | 1,938 | [1,127, 2,749] | 0.9500 | -0.0177 | [-0.0242, -0.0113] | 60 | `P6-DIAG-d28cc4d92a68` | `results/P6-DIAG/metrics.json` |
| P2 vs P0 | ABLATIONS/callbacks_off | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -505 | [-1,563, 553] | 0.9500 | 0.2392 | [0.2220, 0.2565] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/callbacks_off | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -535 | [-1,847, 777] | 0.9500 | 0.2492 | [0.2316, 0.2668] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/callbacks_off | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -30 | [-476, 416] | 0.9500 | 0.0100 | [0.0052, 0.0148] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 325 | [-508, 1,158] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 2 | [-1,084, 1,087] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -323 | [-1,014, 367] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/discount_0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 296 | [-571, 1,163] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/discount_0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -51 | [-1,181, 1,078] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/discount_0 | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -347 | [-1,070, 376] | 0.9500 | 0.0104 | [0.0052, 0.0155] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/identical_price | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 41 | [-758, 841] | 0.9500 | 0.2231 | [0.2071, 0.2391] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/identical_price | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 121 | [-834, 1,077] | 0.9500 | 0.2227 | [0.2052, 0.2402] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/identical_price | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 80 | [-476, 636] | 0.9500 | -0.0004 | [-0.0087, 0.0078] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/identical_quality | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 637 | [-202, 1,475] | 0.9500 | 0.2353 | [0.2149, 0.2557] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/identical_quality | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 1,009 | [177, 1,840] | 0.9500 | 0.2471 | [0.2251, 0.2691] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/identical_quality | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 372 | [29, 715] | 0.9500 | 0.0118 | [0.0065, 0.0170] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/loss_off | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -40 | [-646, 566] | 0.9500 | 0.0103 | [0.0052, 0.0155] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 357 | [-537, 1,250] | 0.9500 | 0.2227 | [0.2071, 0.2382] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 59 | [-1,100, 1,217] | 0.9500 | 0.2340 | [0.2186, 0.2493] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/no_suppression | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -298 | [-995, 399] | 0.9500 | 0.0113 | [0.0055, 0.0171] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/obs_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 284 | [-571, 1,138] | 0.9500 | 0.2146 | [0.2009, 0.2284] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/obs_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 668 | [-67, 1,403] | 0.9500 | 0.2180 | [0.2050, 0.2311] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/obs_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 384 | [-137, 906] | 0.9500 | 0.0034 | [-0.0016, 0.0084] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/perfect_estimator | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 1,064 | [324, 1,804] | 0.9500 | 0.2378 | [0.2210, 0.2546] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/perfect_estimator | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 308 | [31, 585] | 0.9500 | -0.0198 | [-0.0267, -0.0128] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 533 | [-54, 1,120] | 0.9500 | 0.2283 | [0.2125, 0.2441] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 652 | [-22, 1,326] | 0.9500 | 0.2390 | [0.2232, 0.2547] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/retention_null | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 119 | [-147, 386] | 0.9500 | 0.0106 | [0.0055, 0.0158] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 409 | [-412, 1,229] | 0.9500 | 0.2298 | [0.2139, 0.2456] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 392 | [-619, 1,402] | 0.9500 | 0.2418 | [0.2258, 0.2577] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/unlimited_capacity | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -17 | [-380, 347] | 0.9500 | 0.0120 | [0.0072, 0.0167] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | ABLATIONS/verify_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 386 | [-563, 1,335] | 0.9500 | 0.2001 | [0.1842, 0.2160] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/verify_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 64 | [-1,124, 1,252] | 0.9500 | 0.2110 | [0.1955, 0.2264] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P2 | ABLATIONS/verify_perfect | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -322 | [-1,015, 372] | 0.9500 | 0.0109 | [0.0058, 0.0160] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P2 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 535 | [469, 600] | 0.9500 | 0.2466 | [0.2151, 0.2781] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| P3 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -189 | [-590, 212] | 0.9500 | -0.1489 | [-0.2193, -0.0785] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| P4 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 708 | [531, 884] | 0.9500 | 0.2651 | [0.2324, 0.2978] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| P5 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 383 | [184, 582] | 0.9500 | 0.1446 | [0.1137, 0.1755] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V01 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -1,061 | [-1,501, -622] | 0.9500 | -0.8875 | [-0.9930, -0.7820] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V02 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -1,061 | [-1,501, -622] | 0.9500 | -0.8875 | [-0.9930, -0.7820] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V03 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -445 | [-858, -33] | 0.9500 | -0.1873 | [-0.2520, -0.1225] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V04 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 536 | [475, 597] | 0.9500 | 0.2476 | [0.2164, 0.2789] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V05 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 536 | [475, 597] | 0.9500 | 0.2476 | [0.2164, 0.2789] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V06 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -345 | [-444, -246] | 0.9500 | -0.0419 | [-0.0771, -0.0066] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V07 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -593 | [-702, -484] | 0.9500 | -0.1050 | [-0.1405, -0.0696] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V08 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -549 | [-667, -431] | 0.9500 | -0.0944 | [-0.1303, -0.0586] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V09 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 506 | [443, 570] | 0.9500 | 0.2377 | [0.2092, 0.2661] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V10 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 457 | [394, 520] | 0.9500 | 0.2245 | [0.1954, 0.2536] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V11 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 616 | [516, 715] | 0.9500 | 0.2724 | [0.2414, 0.3035] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V12 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -161 | [-235, -87] | 0.9500 | -0.0584 | [-0.0906, -0.0262] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V13 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 605 | [508, 703] | 0.9500 | 0.2673 | [0.2384, 0.2963] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V14 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 587 | [491, 683] | 0.9500 | 0.2638 | [0.2349, 0.2926] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| V15 vs P0 | E9-pilot/pilot | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 630 | [563, 696] | 0.9500 | 0.2623 | [0.2312, 0.2934] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| P2 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -414 | [-1,090, 263] | 0.9500 | 0.2269 | [0.2182, 0.2355] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| P3 vs P0 | E9-truth/default | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -4,333 | [-5,330, -3,337] | 0.9500 | -0.1929 | [-0.2077, -0.1781] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| P4 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 12 | [-694, 718] | 0.9500 | 0.2351 | [0.2260, 0.2441] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| P5 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -2 | [-465, 461] | 0.9500 | 0.1278 | [0.1184, 0.1372] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V01 vs P0 | E9-truth/default | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -6,597 | [-7,494, -5,699] | 0.9500 | -0.9578 | [-0.9754, -0.9401] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V02 vs P0 | E9-truth/default | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -6,597 | [-7,494, -5,699] | 0.9500 | -0.9578 | [-0.9754, -0.9401] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V03 vs P0 | E9-truth/default | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -4,740 | [-5,787, -3,693] | 0.9500 | -0.2270 | [-0.2444, -0.2096] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V04 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -386 | [-1,056, 284] | 0.9500 | 0.2264 | [0.2179, 0.2349] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V05 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -386 | [-1,056, 284] | 0.9500 | 0.2264 | [0.2179, 0.2349] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V06 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -1,183 | [-1,537, -829] | 0.9500 | -0.0664 | [-0.0762, -0.0565] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V09 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -455 | [-1,137, 226] | 0.9500 | 0.2174 | [0.2087, 0.2260] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V10 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -462 | [-1,158, 234] | 0.9500 | 0.2072 | [0.1985, 0.2159] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V11 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 7 | [-718, 733] | 0.9500 | 0.2456 | [0.2365, 0.2546] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V12 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -506 | [-821, -192] | 0.9500 | -0.0941 | [-0.1042, -0.0840] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V13 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 195 | [-442, 833] | 0.9500 | 0.2390 | [0.2301, 0.2479] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V14 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 204 | [-425, 832] | 0.9500 | 0.2338 | [0.2248, 0.2427] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V15 vs P0 | E9-truth/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 317 | [-288, 922] | 0.9500 | 0.2371 | [0.2280, 0.2461] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| P2 vs P0 | PRIMARY/default | PRIMARY | **EQUIVALENCE_SUPPORTED** | -227 | [-660, 206] | 0.9500 | 0.2227 | [0.2169, 0.2285] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P3 vs P0 | PRIMARY/default | EXPLORATORY | **VALUE_LOWER_SUPPORTED** STRONG | -4,972 | [-5,746, -4,199] | 0.9500 | -0.2040 | [-0.2147, -0.1933] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P4 vs P0 | PRIMARY/default | CONFIRMATORY | **EQUIVALENCE_SUPPORTED** | 119 | [-342, 580] | 0.9500 | 0.2312 | [0.2251, 0.2372] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P4 vs P2 | PRIMARY/default | CONFIRMATORY | **EQUIVALENCE_SUPPORTED** | 346 | [-60, 752] | 0.9833 | 0.0085 | [0.0056, 0.0114] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P5 vs P0 | PRIMARY/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | -5 | [-342, 331] | 0.9500 | 0.1218 | [0.1147, 0.1289] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P5 vs P2 | PRIMARY/default | EXPLORATORY | **EQUIVALENCE_SUPPORTED** | 222 | [-136, 580] | 0.9500 | -0.1009 | [-0.1057, -0.0961] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P5 vs P4 | PRIMARY/default | CONFIRMATORY | **EQUIVALENCE_SUPPORTED** | -125 | [-514, 265] | 0.9750 | -0.1094 | [-0.1147, -0.1040] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |

## Supported model-family findings (Level 2)

Sensitivity design: 48 tested design points. Shares of tested points by class for P2 vs P0: ALIGNMENT_SUPPORTED 13/48, EQUIVALENCE_SUPPORTED 5/48, INCONCLUSIVE 10/48, REVERSAL_SUPPORTED 20/48.
A Level-2 claim needs one class across the declared design and the structural ablations. The design points are not all in one class, so no Level-2 claim is made for P2 vs P0.

## Unsupported or inconclusive

| contrast | scenario | label | class | ΔJ mean (USD) | ΔJ CI | CI level | ΔG mean | ΔG CI | n | run_id | artifact |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 vs P0 | E-DEPLOY/deploy | EXPLORATORY | **INCONCLUSIVE** | 1,754 | [871, 2,638] | 0.9500 | 0.2322 | [0.2201, 0.2443] | 60 | `E-DEPLOY-bce174da4635` | `results/E-DEPLOY/metrics.json` |
| P5 vs P0 | E1/aligned | EXPLORATORY | **INCONCLUSIVE** | 1,767 | [873, 2,661] | 0.9500 | 0.1291 | [0.1084, 0.1498] | 60 | `E1-5914c3228812` | `results/E1/metrics.json` |
| P1 vs P0 | E2/static_mismatch | EXPLORATORY | **PROXY_NOT_IMPROVED** | -5,695 | [-7,328, -4,062] | 0.9500 | -0.0562 | [-0.0734, -0.0389] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P3 vs P1 | E2/static_mismatch | EXPLORATORY | **INCONCLUSIVE** | 1,314 | [408, 2,220] | 0.9500 | -0.1219 | [-0.1301, -0.1136] | 60 | `E2-2aff2d905310` | `results/E2/metrics.json` |
| P2 vs P0 | E6/negligence_0 | EXPLORATORY | **INCONCLUSIVE** | 1,340 | [764, 1,917] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/negligence_0 | EXPLORATORY | **INCONCLUSIVE** | 1,234 | [492, 1,976] | 0.9500 | 0.2491 | [0.2338, 0.2644] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E6/negligence_0.5 | EXPLORATORY | **INCONCLUSIVE** | -1,148 | [-2,762, 467] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E6-3c1b1f5b85c0` | `results/E6/metrics.json` |
| P4 vs P0 | E8/acc_1.0|retrained_M | EXPLORATORY | **INCONCLUSIVE** | 1,308 | [722, 1,895] | 0.9500 | 0.2341 | [0.2193, 0.2488] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | E8/beta_x2|retrained_M | EXPLORATORY | **INCONCLUSIVE** | -1,188 | [-2,486, 109] | 0.9500 | 0.2258 | [0.2096, 0.2420] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/beta_x2|retrained_M | EXPLORATORY | **INCONCLUSIVE** | -1,397 | [-2,772, -22] | 0.9500 | 0.2306 | [0.2150, 0.2462] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/negligence_0.5|default_M | EXPLORATORY | **INCONCLUSIVE** | -1,148 | [-2,762, 467] | 0.9500 | 0.2389 | [0.2231, 0.2547] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P4 vs P0 | E8/negligence_0.5|retrained_M | EXPLORATORY | **INCONCLUSIVE** | -1,794 | [-3,720, 132] | 0.9500 | 0.2439 | [0.2274, 0.2604] | 40 | `E8-d49a5b25f3bd` | `results/E8/run/metrics.json` |
| P2 vs P0 | ABLATIONS/loss_off | EXPLORATORY | **INCONCLUSIVE** | 1,623 | [1,140, 2,105] | 0.9500 | 0.2285 | [0.2127, 0.2443] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/loss_off | EXPLORATORY | **INCONCLUSIVE** | 1,583 | [988, 2,178] | 0.9500 | 0.2388 | [0.2231, 0.2546] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P4 vs P0 | ABLATIONS/perfect_estimator | EXPLORATORY | **INCONCLUSIVE** | 1,373 | [661, 2,084] | 0.9500 | 0.2180 | [0.1995, 0.2366] | 40 | `ABLATIONS-79ed94f00314` | `results/ablations/metrics.json` |
| P1 vs P0 | E9-pilot/pilot | EXPLORATORY | **PROXY_NOT_IMPROVED** | -182 | [-588, 225] | 0.9500 | -0.0078 | [-0.0526, 0.0371] | 20 | `E9-pilot-8800ef314bfe` | `results/e9/pilot/metrics.json` |
| P1 vs P0 | E9-truth/default | EXPLORATORY | **PROXY_NOT_IMPROVED** | -5,915 | [-7,114, -4,716] | 0.9500 | -0.0551 | [-0.0674, -0.0428] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V07 vs P0 | E9-truth/default | EXPLORATORY | **INCONCLUSIVE** | -1,728 | [-2,148, -1,308] | 0.9500 | -0.1285 | [-0.1385, -0.1185] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| V08 vs P0 | E9-truth/default | EXPLORATORY | **INCONCLUSIVE** | -1,547 | [-1,972, -1,123] | 0.9500 | -0.1183 | [-0.1272, -0.1095] | 100 | `E9-truth-33b6afe44a5f` | `results/e9/truth/metrics.json` |
| P1 vs P0 | PRIMARY/default | CONFIRMATORY | **PROXY_NOT_IMPROVED** | -6,591 | [-7,744, -5,438] | 0.9900 | -0.0655 | [-0.0771, -0.0539] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |
| P3 vs P1 | PRIMARY/default | CONFIRMATORY | **INCONCLUSIVE** | 1,619 | [1,026, 2,212] | 0.9875 | -0.1385 | [-0.1450, -0.1320] | 200 | `PRIMARY-e85fc6d05ce0` | `results/primary/metrics.json` |

## Required external validation

- Level 3 (external validation) is out of scope. No result here says anything about real property-management operators.
- Every parameter is a synthetic engineering fixture. Calibrating arrival rates, contractor quality, tenant reporting, verification accuracy, retention hazards and loss sizes to real data would be required before any external claim.
- The proxy (proxy_v1) is one dashboard definition; other proxies may behave differently.
