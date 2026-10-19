# Consolidado de backtests contemporáneos GEFS

> Generado: 2026-10-17T09:39:17.624475+00:00. Casos: 23/23. Integridad global: **aprobada**.

Los reinicios de un mismo incendio están correlacionados. Este informe es descriptivo: presenta primero medianas por incendio y no trata los reinicios como incendios independientes ni fabrica significancia estadística.

## Gate técnico

- Casos con `integrity_passed=true`: 23/23.
- Umbrales congelados: `0,10`, `0,50`, `0,80`.
- El acuerdo es fracción de miembros válidos; no es probabilidad calibrada.

## Costo, latencia y almacenamiento observados

- Pared acumulada registrada por los clientes seriales: 9.20 h.
- Almacenamiento lógico retenido en los casos: 44.68 GiB.
- Intentos de infraestructura documentados: 3.
- CPU/RSS remotos y costo monetario del solver: no expuestos por el runner; no se infiere costo facturable a partir de pared de cliente.

## Resultados por reinicio

| Reinicio | Horizonte | Producto | Δ IoU | Δ Dice | Δ recall | Δ precisión | Δ sesgo área | FP ha | Área predicha ha | Cobertura cicatriz | Cobertura FIRMS |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| epuyen-2025-w05 | 12 h | agreement_ge_10 | -0.0029 | -0.0053 | 0.0034 | -0.0029 | 1.2224 | 1003.95 | 1054.89 | 0.9759 | — |
| epuyen-2025-w05 | 12 h | agreement_ge_50 | -0.0005 | -0.0009 | 0.0000 | -0.0005 | 0.1966 | 950.58 | 1001.34 | 0.9724 | — |
| epuyen-2025-w05 | 12 h | agreement_ge_80 | 0.0012 | 0.0022 | -0.0034 | 0.0012 | -0.5155 | 913.59 | 964.17 | 0.9690 | — |
| epuyen-2025-w05 | 24 h | agreement_ge_10 | -0.0091 | -0.0144 | 0.0371 | -0.0101 | 0.8647 | 2165.22 | 2461.05 | 0.8969 | 0.9558 |
| epuyen-2025-w05 | 24 h | agreement_ge_50 | -0.0022 | -0.0034 | 0.0025 | -0.0023 | 0.1389 | 1937.25 | 2221.65 | 0.8622 | 0.9387 |
| epuyen-2025-w05 | 24 h | agreement_ge_80 | 0.0010 | 0.0016 | -0.0289 | 0.0018 | -0.3075 | 1800.36 | 2074.41 | 0.8308 | 0.9232 |
| epuyen-2025-w06 | 12 h | agreement_ge_10 | -0.0155 | -0.0267 | 0.0086 | -0.0157 | 2.5655 | 657.00 | 706.77 | 0.9534 | — |
| epuyen-2025-w06 | 12 h | agreement_ge_50 | -0.0119 | -0.0204 | 0.0052 | -0.0120 | 1.8534 | 620.01 | 669.60 | 0.9500 | — |
| epuyen-2025-w06 | 12 h | agreement_ge_80 | -0.0088 | -0.0151 | 0.0034 | -0.0089 | 1.3121 | 591.84 | 641.34 | 0.9483 | — |
| epuyen-2025-w06 | 24 h | agreement_ge_10 | -0.0019 | -0.0030 | 0.1222 | -0.0064 | 1.2090 | 1995.03 | 2283.48 | 0.7516 | 0.8273 |
| epuyen-2025-w06 | 24 h | agreement_ge_50 | 0.0033 | 0.0052 | 0.0809 | 0.0006 | 0.5870 | 1772.19 | 2044.80 | 0.7104 | 0.7876 |
| epuyen-2025-w06 | 24 h | agreement_ge_80 | 0.0070 | 0.0110 | 0.0593 | 0.0055 | 0.2411 | 1647.72 | 1912.05 | 0.6888 | 0.7740 |
| puerto-patriada-2026-w01 | 12 h | agreement_ge_10 | 0.0084 | 0.0111 | 0.0100 | 0.0002 | 0.0135 | 217.17 | 826.74 | 0.2606 | 0.2177 |
| puerto-patriada-2026-w01 | 12 h | agreement_ge_50 | 0.0003 | 0.0005 | 0.0005 | -0.0005 | 0.0008 | 209.97 | 797.22 | 0.2510 | 0.2099 |
| puerto-patriada-2026-w01 | 12 h | agreement_ge_80 | -0.0030 | -0.0039 | -0.0035 | 0.0001 | -0.0048 | 206.01 | 783.90 | 0.2470 | 0.2064 |
| puerto-patriada-2026-w01 | 24 h | agreement_ge_10 | 0.0049 | 0.0059 | 0.0073 | -0.0036 | 0.0129 | 394.47 | 1285.92 | 0.3376 | 0.3053 |
| puerto-patriada-2026-w01 | 24 h | agreement_ge_50 | -0.0017 | -0.0021 | -0.0021 | -0.0007 | -0.0026 | 378.27 | 1244.97 | 0.3282 | 0.2976 |
| puerto-patriada-2026-w01 | 24 h | agreement_ge_80 | -0.0058 | -0.0070 | -0.0078 | 0.0013 | -0.0121 | 368.28 | 1219.86 | 0.3225 | 0.2926 |
| puerto-patriada-2026-w02 | 12 h | agreement_ge_10 | -0.0059 | -0.0084 | 0.0035 | -0.0086 | 0.1180 | 581.67 | 740.43 | 0.5685 | 0.5728 |
| puerto-patriada-2026-w02 | 12 h | agreement_ge_50 | -0.0068 | -0.0097 | -0.0174 | -0.0067 | -0.0023 | 553.95 | 706.86 | 0.5475 | 0.5482 |
| puerto-patriada-2026-w02 | 12 h | agreement_ge_80 | -0.0116 | -0.0165 | -0.0496 | -0.0081 | -0.1350 | 525.87 | 669.78 | 0.5153 | 0.5161 |
| puerto-patriada-2026-w02 | 24 h | agreement_ge_10 | -0.0005 | -0.0007 | 0.0015 | -0.0036 | 0.0213 | 1421.46 | 1814.94 | 0.1911 | 0.1921 |
| puerto-patriada-2026-w02 | 24 h | agreement_ge_50 | -0.0035 | -0.0056 | -0.0058 | -0.0053 | -0.0057 | 1380.87 | 1759.41 | 0.1838 | 0.1866 |
| puerto-patriada-2026-w02 | 24 h | agreement_ge_80 | -0.0061 | -0.0099 | -0.0122 | -0.0065 | -0.0309 | 1342.26 | 1707.48 | 0.1773 | 0.1822 |
| puerto-patriada-2026-w03 | 12 h | agreement_ge_10 | 0.0025 | 0.0036 | 0.0064 | -0.0040 | 0.0244 | 731.07 | 1146.51 | 0.2318 | 0.1869 |
| puerto-patriada-2026-w03 | 12 h | agreement_ge_50 | -0.0008 | -0.0012 | -0.0015 | -0.0004 | -0.0033 | 695.52 | 1096.92 | 0.2239 | 0.1783 |
| puerto-patriada-2026-w03 | 12 h | agreement_ge_80 | -0.0026 | -0.0039 | -0.0058 | 0.0021 | -0.0194 | 674.46 | 1068.03 | 0.2196 | 0.1744 |
| puerto-patriada-2026-w03 | 24 h | agreement_ge_10 | 0.0075 | 0.0107 | 0.0210 | 0.0032 | 0.0595 | 1535.40 | 2169.18 | 0.3527 | 0.2899 |
| puerto-patriada-2026-w03 | 24 h | agreement_ge_50 | -0.0040 | -0.0057 | -0.0079 | -0.0040 | -0.0114 | 1459.80 | 2041.65 | 0.3238 | 0.2673 |
| puerto-patriada-2026-w03 | 24 h | agreement_ge_80 | -0.0086 | -0.0124 | -0.0199 | -0.0064 | -0.0443 | 1422.36 | 1982.61 | 0.3117 | 0.2595 |
| puerto-patriada-2026-w04 | 12 h | agreement_ge_10 | -0.0030 | -0.0056 | 0.0073 | -0.0031 | 1.6459 | 1540.62 | 1608.39 | 0.9194 | — |
| puerto-patriada-2026-w04 | 12 h | agreement_ge_50 | -0.0002 | -0.0003 | 0.0000 | -0.0002 | 0.0781 | 1425.60 | 1492.83 | 0.9121 | — |
| puerto-patriada-2026-w04 | 12 h | agreement_ge_80 | 0.0015 | 0.0027 | -0.0037 | 0.0015 | -0.7302 | 1366.29 | 1433.25 | 0.9084 | — |
| puerto-patriada-2026-w04 | 24 h | agreement_ge_10 | -0.0026 | -0.0049 | 0.0009 | -0.0026 | 3.3942 | 3537.45 | 3632.85 | 0.9833 | 0.8842 |
| puerto-patriada-2026-w04 | 24 h | agreement_ge_50 | 0.0004 | 0.0008 | 0.0000 | 0.0004 | -0.4712 | 3162.51 | 3257.82 | 0.9824 | 0.8842 |
| puerto-patriada-2026-w04 | 24 h | agreement_ge_80 | 0.0019 | 0.0036 | -0.0009 | 0.0019 | -2.1494 | 2999.79 | 3095.01 | 0.9814 | 0.8842 |
| puerto-patriada-2026-w05 | 12 h | agreement_ge_10 | -0.0026 | -0.0046 | 0.0111 | -0.0026 | 1.0399 | 1623.78 | 1713.96 | 0.9304 | 0.8826 |
| puerto-patriada-2026-w05 | 12 h | agreement_ge_50 | 0.0009 | 0.0016 | 0.0074 | 0.0009 | -0.1346 | 1510.29 | 1600.11 | 0.9266 | 0.8826 |
| puerto-patriada-2026-w05 | 12 h | agreement_ge_80 | 0.0034 | 0.0062 | -0.0074 | 0.0035 | -1.1179 | 1416.42 | 1504.80 | 0.9118 | 0.8826 |
| puerto-patriada-2026-w05 | 24 h | agreement_ge_10 | -0.0016 | -0.0029 | 0.0044 | -0.0016 | 0.8549 | 3698.46 | 3866.04 | 0.9065 | 0.9171 |
| puerto-patriada-2026-w05 | 24 h | agreement_ge_50 | 0.0002 | 0.0003 | -0.0054 | 0.0002 | -0.2084 | 3503.70 | 3669.48 | 0.8968 | 0.9133 |
| puerto-patriada-2026-w05 | 24 h | agreement_ge_80 | 0.0018 | 0.0032 | -0.0083 | 0.0018 | -0.9460 | 3367.89 | 3533.13 | 0.8939 | 0.9114 |
| puerto-patriada-2026-w06 | 12 h | agreement_ge_10 | -0.0027 | -0.0050 | 0.0057 | -0.0027 | 1.8073 | 1848.78 | 1920.96 | 0.9197 | 1.0000 |
| puerto-patriada-2026-w06 | 12 h | agreement_ge_50 | -0.0002 | -0.0004 | -0.0011 | -0.0002 | 0.0803 | 1713.78 | 1785.42 | 0.9128 | 1.0000 |
| puerto-patriada-2026-w06 | 12 h | agreement_ge_80 | 0.0010 | 0.0019 | -0.0069 | 0.0011 | -0.7454 | 1649.43 | 1720.62 | 0.9071 | 1.0000 |
| puerto-patriada-2026-w06 | 24 h | agreement_ge_10 | -0.0002 | -0.0004 | 0.0272 | -0.0017 | 0.1869 | 4182.84 | 5129.37 | 0.8206 | 0.8412 |
| puerto-patriada-2026-w06 | 24 h | agreement_ge_50 | 0.0005 | 0.0007 | -0.0048 | 0.0008 | -0.0449 | 3952.44 | 4861.98 | 0.7885 | 0.8174 |
| puerto-patriada-2026-w06 | 24 h | agreement_ge_80 | -0.0001 | -0.0002 | -0.0265 | 0.0014 | -0.1719 | 3830.94 | 4715.55 | 0.7669 | 0.8013 |
| los-alerces-2024-w01 | 12 h | agreement_ge_10 | 0.0088 | 0.0102 | 0.0135 | -0.0010 | 0.0222 | 46.35 | 126.81 | 0.3885 | 0.4011 |
| los-alerces-2024-w01 | 12 h | agreement_ge_50 | 0.0010 | 0.0011 | 0.0013 | 0.0003 | 0.0017 | 44.64 | 122.58 | 0.3764 | 0.3864 |
| los-alerces-2024-w01 | 12 h | agreement_ge_80 | -0.0045 | -0.0053 | -0.0083 | 0.0049 | -0.0174 | 42.66 | 118.62 | 0.3668 | 0.3703 |
| los-alerces-2024-w01 | 24 h | agreement_ge_10 | 0.0201 | 0.0262 | 0.0235 | 0.0042 | 0.0301 | 108.72 | 410.85 | 0.2713 | 0.2509 |
| los-alerces-2024-w01 | 24 h | agreement_ge_50 | 0.0007 | 0.0009 | 0.0010 | -0.0013 | 0.0019 | 102.51 | 379.53 | 0.2488 | 0.2288 |
| los-alerces-2024-w01 | 24 h | agreement_ge_80 | -0.0071 | -0.0095 | -0.0082 | -0.0027 | -0.0099 | 99.45 | 366.30 | 0.2397 | 0.2202 |
| los-alerces-2024-w02 | 12 h | agreement_ge_10 | 0.0085 | 0.0091 | 0.0238 | -0.0088 | 0.0561 | 160.20 | 365.31 | 0.5258 | 0.6156 |
| los-alerces-2024-w02 | 12 h | agreement_ge_50 | 0.0004 | 0.0004 | 0.0016 | -0.0011 | 0.0046 | 148.77 | 345.24 | 0.5037 | 0.5921 |
| los-alerces-2024-w02 | 12 h | agreement_ge_80 | -0.0030 | -0.0032 | -0.0092 | 0.0047 | -0.0233 | 142.11 | 334.35 | 0.4928 | 0.5821 |
| los-alerces-2024-w02 | 24 h | agreement_ge_10 | -0.0070 | -0.0066 | 0.0119 | -0.0164 | 0.0622 | 351.45 | 765.00 | 0.7504 | 0.7429 |
| los-alerces-2024-w02 | 24 h | agreement_ge_50 | -0.0029 | -0.0027 | 0.0052 | -0.0070 | 0.0265 | 335.43 | 745.29 | 0.7438 | 0.7373 |
| los-alerces-2024-w02 | 24 h | agreement_ge_80 | -0.0012 | -0.0011 | -0.0003 | -0.0015 | 0.0029 | 325.53 | 732.33 | 0.7382 | 0.7339 |
| los-alerces-2024-w03 | 12 h | agreement_ge_10 | -0.0054 | -0.0054 | 0.0337 | -0.0282 | 0.1395 | 162.54 | 320.22 | 0.6788 | 0.5493 |
| los-alerces-2024-w03 | 12 h | agreement_ge_50 | -0.0011 | -0.0011 | 0.0074 | -0.0064 | 0.0298 | 143.19 | 294.75 | 0.6525 | 0.4980 |
| los-alerces-2024-w03 | 12 h | agreement_ge_80 | -0.0009 | -0.0009 | -0.0027 | 0.0003 | -0.0058 | 137.25 | 286.47 | 0.6424 | 0.4804 |
| los-alerces-2024-w03 | 24 h | agreement_ge_10 | -0.0123 | -0.0127 | 0.0101 | -0.0162 | 0.1062 | 445.95 | 750.15 | 0.8714 | 0.9248 |
| los-alerces-2024-w03 | 24 h | agreement_ge_50 | -0.0026 | -0.0027 | 0.0023 | -0.0035 | 0.0227 | 419.49 | 720.99 | 0.8636 | 0.9118 |
| los-alerces-2024-w03 | 24 h | agreement_ge_80 | 0.0021 | 0.0022 | -0.0013 | 0.0027 | -0.0162 | 407.16 | 707.40 | 0.8600 | 0.9073 |
| los-alerces-2024-w04 | 12 h | agreement_ge_10 | -0.0041 | -0.0044 | 0.0031 | -0.0054 | 0.0385 | 234.63 | 380.25 | 0.8410 | 0.7345 |
| los-alerces-2024-w04 | 12 h | agreement_ge_50 | 0.0026 | 0.0028 | -0.0026 | 0.0036 | -0.0265 | 224.37 | 369.00 | 0.8352 | 0.7320 |
| los-alerces-2024-w04 | 12 h | agreement_ge_80 | 0.0052 | 0.0056 | -0.0073 | 0.0077 | -0.0603 | 219.33 | 363.15 | 0.8306 | 0.7270 |
| los-alerces-2024-w04 | 24 h | agreement_ge_10 | -0.0028 | -0.0030 | 0.0052 | -0.0039 | 0.0398 | 633.69 | 1002.87 | 0.8966 | 0.8363 |
| los-alerces-2024-w04 | 24 h | agreement_ge_50 | 0.0015 | 0.0016 | -0.0039 | 0.0023 | -0.0251 | 610.74 | 976.14 | 0.8874 | 0.8276 |
| los-alerces-2024-w04 | 24 h | agreement_ge_80 | 0.0050 | 0.0055 | -0.0085 | 0.0071 | -0.0671 | 595.35 | 958.86 | 0.8828 | 0.8227 |
| epuyen-2025-w02 | 12 h | agreement_ge_10 | -0.0115 | -0.0160 | 0.0275 | -0.0133 | 0.4382 | 711.36 | 882.09 | 0.9164 | 0.9086 |
| epuyen-2025-w02 | 12 h | agreement_ge_50 | -0.0030 | -0.0042 | 0.0043 | -0.0034 | 0.0937 | 651.51 | 817.92 | 0.8932 | 0.8732 |
| epuyen-2025-w02 | 12 h | agreement_ge_80 | 0.0013 | 0.0018 | -0.0063 | 0.0017 | -0.0652 | 623.88 | 788.31 | 0.8826 | 0.8579 |
| epuyen-2025-w02 | 24 h | agreement_ge_10 | -0.0098 | -0.0163 | 0.0000 | -0.0098 | 1.0840 | 2307.24 | 2536.11 | 0.9980 | 0.9655 |
| epuyen-2025-w02 | 24 h | agreement_ge_50 | -0.0027 | -0.0045 | 0.0000 | -0.0027 | 0.2814 | 2123.19 | 2352.06 | 0.9980 | 0.9651 |
| epuyen-2025-w02 | 24 h | agreement_ge_80 | 0.0015 | 0.0025 | -0.0008 | 0.0015 | -0.1586 | 2022.48 | 2251.17 | 0.9973 | 0.9651 |
| epuyen-2025-w03 | 12 h | agreement_ge_10 | -0.0034 | -0.0059 | 0.0038 | -0.0034 | 0.6882 | 910.71 | 980.10 | 0.9772 | 0.9756 |
| epuyen-2025-w03 | 12 h | agreement_ge_50 | 0.0001 | 0.0001 | 0.0000 | 0.0001 | -0.0152 | 861.03 | 930.15 | 0.9734 | 0.9756 |
| epuyen-2025-w03 | 12 h | agreement_ge_80 | 0.0021 | 0.0036 | -0.0013 | 0.0021 | -0.3764 | 835.47 | 904.50 | 0.9721 | 0.9756 |
| epuyen-2025-w03 | 24 h | agreement_ge_10 | -0.0035 | -0.0064 | 0.0000 | -0.0035 | 2.2059 | 2442.69 | 2538.36 | 0.9861 | 0.9662 |
| epuyen-2025-w03 | 24 h | agreement_ge_50 | -0.0005 | -0.0008 | 0.0000 | -0.0005 | 0.2662 | 2254.50 | 2350.17 | 0.9861 | 0.9662 |
| epuyen-2025-w03 | 24 h | agreement_ge_80 | 0.0022 | 0.0041 | -0.0009 | 0.0022 | -1.2514 | 2107.35 | 2202.93 | 0.9852 | 0.9662 |
| epuyen-2025-w04 | 12 h | agreement_ge_10 | -0.0038 | -0.0065 | 0.0023 | -0.0039 | 0.5846 | 880.29 | 956.70 | 0.9637 | 0.9699 |
| epuyen-2025-w04 | 12 h | agreement_ge_50 | 0.0003 | 0.0006 | 0.0000 | 0.0003 | -0.0465 | 830.43 | 906.66 | 0.9614 | 0.9699 |
| epuyen-2025-w04 | 12 h | agreement_ge_80 | 0.0036 | 0.0061 | -0.0011 | 0.0036 | -0.4869 | 795.60 | 871.74 | 0.9603 | 0.9699 |
| epuyen-2025-w04 | 24 h | agreement_ge_10 | -0.0019 | -0.0036 | 0.0011 | -0.0019 | 2.6769 | 2954.79 | 3033.09 | 0.9864 | 0.9485 |
| epuyen-2025-w04 | 24 h | agreement_ge_50 | 0.0001 | 0.0002 | 0.0000 | 0.0001 | -0.1020 | 2734.29 | 2812.50 | 0.9853 | 0.9485 |
| epuyen-2025-w04 | 24 h | agreement_ge_80 | 0.0013 | 0.0025 | 0.0000 | 0.0013 | -1.6417 | 2612.07 | 2690.28 | 0.9853 | 0.9485 |
| epuyen-2025-w01 | 12 h | agreement_ge_10 | 0.0044 | 0.0051 | 0.0303 | -0.0081 | 0.1005 | 542.52 | 918.72 | 0.5916 | 0.3818 |
| epuyen-2025-w01 | 12 h | agreement_ge_50 | -0.0002 | -0.0003 | -0.0014 | 0.0004 | -0.0045 | 495.90 | 851.94 | 0.5599 | 0.3533 |
| epuyen-2025-w01 | 12 h | agreement_ge_80 | -0.0051 | -0.0060 | -0.0201 | 0.0024 | -0.0555 | 475.38 | 819.54 | 0.5412 | 0.3397 |
| epuyen-2025-w01 | 24 h | agreement_ge_10 | -0.0107 | -0.0113 | 0.0254 | -0.0164 | 0.1622 | 1139.67 | 1844.37 | 0.9139 | 0.8391 |
| epuyen-2025-w01 | 24 h | agreement_ge_50 | -0.0004 | -0.0005 | 0.0018 | -0.0008 | 0.0091 | 1039.86 | 1726.29 | 0.8902 | 0.8125 |
| epuyen-2025-w01 | 24 h | agreement_ge_80 | 0.0022 | 0.0023 | -0.0147 | 0.0055 | -0.0668 | 994.05 | 1667.79 | 0.8737 | 0.8014 |
| los-alerces-2024-w05 | 12 h | agreement_ge_10 | -0.0017 | -0.0018 | 0.0099 | -0.0044 | 0.0463 | 254.16 | 426.06 | 0.8190 | 0.6453 |
| los-alerces-2024-w05 | 12 h | agreement_ge_50 | 0.0012 | 0.0013 | -0.0030 | 0.0022 | -0.0180 | 243.36 | 412.56 | 0.8062 | 0.6397 |
| los-alerces-2024-w05 | 12 h | agreement_ge_80 | 0.0049 | 0.0051 | -0.0077 | 0.0079 | -0.0562 | 236.34 | 404.55 | 0.8015 | 0.6369 |
| los-alerces-2024-w05 | 24 h | agreement_ge_10 | -0.0016 | -0.0017 | 0.0017 | -0.0031 | 0.0140 | 656.55 | 1194.93 | 0.6792 | 0.6359 |
| los-alerces-2024-w05 | 24 h | agreement_ge_50 | -0.0004 | -0.0005 | -0.0039 | 0.0011 | -0.0121 | 640.26 | 1174.23 | 0.6737 | 0.6297 |
| los-alerces-2024-w05 | 24 h | agreement_ge_80 | 0.0013 | 0.0014 | -0.0102 | 0.0067 | -0.0441 | 620.01 | 1148.94 | 0.6673 | 0.6234 |
| los-alerces-2024-w06 | 12 h | agreement_ge_10 | 0.0019 | 0.0024 | 0.0086 | -0.0034 | 0.0287 | 358.11 | 619.20 | 0.4470 | 0.3874 |
| los-alerces-2024-w06 | 12 h | agreement_ge_50 | 0.0004 | 0.0005 | 0.0008 | 0.0003 | 0.0011 | 346.59 | 603.09 | 0.4391 | 0.3816 |
| los-alerces-2024-w06 | 12 h | agreement_ge_80 | -0.0032 | -0.0040 | -0.0122 | 0.0040 | -0.0381 | 331.29 | 580.23 | 0.4262 | 0.3724 |
| los-alerces-2024-w06 | 24 h | agreement_ge_10 | 0.0024 | 0.0027 | 0.0169 | -0.0031 | 0.0526 | 744.12 | 1272.15 | 0.6714 | 0.5879 |
| los-alerces-2024-w06 | 24 h | agreement_ge_50 | -0.0015 | -0.0017 | -0.0039 | -0.0007 | -0.0066 | 713.88 | 1225.53 | 0.6506 | 0.5713 |
| los-alerces-2024-w06 | 24 h | agreement_ge_80 | -0.0048 | -0.0054 | -0.0181 | 0.0003 | -0.0444 | 695.34 | 1195.83 | 0.6364 | 0.5616 |
| los-alerces-2024-w07 | 12 h | agreement_ge_10 | -0.0047 | -0.0067 | 0.0017 | -0.0049 | 0.1323 | 422.55 | 522.90 | 0.9514 | 0.8451 |
| los-alerces-2024-w07 | 12 h | agreement_ge_50 | -0.0001 | -0.0002 | -0.0026 | -0.0000 | -0.0128 | 407.70 | 507.60 | 0.9471 | 0.8345 |
| los-alerces-2024-w07 | 12 h | agreement_ge_80 | 0.0036 | 0.0051 | -0.0085 | 0.0041 | -0.1408 | 394.83 | 494.10 | 0.9411 | 0.8239 |
| los-alerces-2024-w07 | 24 h | agreement_ge_10 | -0.0020 | -0.0026 | 0.0043 | -0.0026 | 0.0483 | 906.66 | 1226.34 | 0.8407 | 0.8066 |
| los-alerces-2024-w07 | 24 h | agreement_ge_50 | 0.0002 | 0.0002 | -0.0012 | 0.0003 | -0.0083 | 887.22 | 1204.83 | 0.8353 | 0.7978 |
| los-alerces-2024-w07 | 24 h | agreement_ge_80 | 0.0022 | 0.0028 | -0.0097 | 0.0034 | -0.0774 | 864.18 | 1178.55 | 0.8267 | 0.7867 |
| los-alerces-2024-w08 | 12 h | agreement_ge_10 | -0.0010 | -0.0014 | 0.0047 | -0.0017 | 0.0433 | 504.27 | 653.49 | 0.7040 | 0.6355 |
| los-alerces-2024-w08 | 12 h | agreement_ge_50 | 0.0001 | 0.0002 | -0.0017 | 0.0003 | -0.0119 | 493.92 | 641.79 | 0.6977 | 0.6288 |
| los-alerces-2024-w08 | 12 h | agreement_ge_80 | 0.0001 | 0.0001 | -0.0119 | 0.0014 | -0.0701 | 483.75 | 629.46 | 0.6875 | 0.6227 |
| los-alerces-2024-w08 | 24 h | agreement_ge_10 | -0.0027 | -0.0039 | 0.0031 | -0.0030 | 0.0882 | 1061.64 | 1309.86 | 0.8659 | 0.8855 |
| los-alerces-2024-w08 | 24 h | agreement_ge_50 | 0.0006 | 0.0008 | -0.0003 | 0.0006 | -0.0160 | 1032.75 | 1279.98 | 0.8625 | 0.8816 |
| los-alerces-2024-w08 | 24 h | agreement_ge_80 | 0.0028 | 0.0040 | -0.0047 | 0.0033 | -0.0989 | 1010.25 | 1256.22 | 0.8581 | 0.8766 |
| los-alerces-2023-w01 | 12 h | agreement_ge_10 | -0.0019 | -0.0025 | 0.0102 | -0.0119 | 0.0728 | 114.66 | 169.83 | 0.3912 | 0.1825 |
| los-alerces-2023-w01 | 12 h | agreement_ge_50 | 0.0003 | 0.0003 | 0.0013 | -0.0004 | 0.0051 | 106.38 | 160.29 | 0.3823 | 0.1743 |
| los-alerces-2023-w01 | 12 h | agreement_ge_80 | 0.0030 | 0.0040 | -0.0013 | 0.0082 | -0.0306 | 101.70 | 155.25 | 0.3797 | 0.1708 |
| los-alerces-2023-w01 | 24 h | agreement_ge_10 | 0.0052 | 0.0059 | 0.0419 | -0.0137 | 0.1424 | 466.83 | 803.34 | 0.6028 | 0.4850 |
| los-alerces-2023-w01 | 24 h | agreement_ge_50 | -0.0015 | -0.0017 | 0.0029 | -0.0044 | 0.0202 | 420.39 | 735.12 | 0.5638 | 0.4574 |
| los-alerces-2023-w01 | 24 h | agreement_ge_80 | -0.0012 | -0.0013 | -0.0123 | 0.0054 | -0.0440 | 393.03 | 699.30 | 0.5486 | 0.4442 |
| los-alerces-2023-w02 | 12 h | agreement_ge_10 | -0.0098 | -0.0112 | 0.0246 | -0.0142 | 0.1869 | 298.08 | 441.63 | 0.8901 | 0.7964 |
| los-alerces-2023-w02 | 12 h | agreement_ge_50 | 0.0006 | 0.0007 | 0.0033 | 0.0001 | 0.0089 | 272.79 | 412.92 | 0.8689 | 0.7792 |
| los-alerces-2023-w02 | 12 h | agreement_ge_80 | 0.0104 | 0.0118 | -0.0151 | 0.0140 | -0.1440 | 251.10 | 388.26 | 0.8504 | 0.7495 |
| los-alerces-2023-w02 | 24 h | agreement_ge_10 | -0.0098 | -0.0155 | 0.0000 | -0.0098 | 0.6601 | 1342.35 | 1519.29 | 0.9914 | 0.9191 |
| los-alerces-2023-w02 | 24 h | agreement_ge_50 | 0.0004 | 0.0006 | 0.0000 | 0.0004 | -0.0252 | 1220.04 | 1396.98 | 0.9914 | 0.9177 |
| los-alerces-2023-w02 | 24 h | agreement_ge_80 | 0.0099 | 0.0155 | 0.0000 | 0.0099 | -0.5734 | 1122.21 | 1299.15 | 0.9914 | 0.9149 |
| los-alerces-2023-w03 | 12 h | agreement_ge_10 | -0.0013 | -0.0024 | 0.0000 | -0.0013 | 0.9792 | 471.33 | 488.61 | 1.0000 | 1.0000 |
| los-alerces-2023-w03 | 12 h | agreement_ge_50 | 0.0001 | 0.0002 | 0.0000 | 0.0001 | -0.0938 | 452.79 | 470.07 | 1.0000 | 1.0000 |
| los-alerces-2023-w03 | 12 h | agreement_ge_80 | 0.0013 | 0.0025 | 0.0000 | 0.0013 | -0.9688 | 437.67 | 454.95 | 1.0000 | 1.0000 |
| los-alerces-2023-w03 | 24 h | agreement_ge_10 | 0.0012 | 0.0018 | 0.0251 | -0.0003 | 0.1547 | 1525.77 | 1838.25 | 0.6665 | 0.6815 |
| los-alerces-2023-w03 | 24 h | agreement_ge_50 | 0.0021 | 0.0031 | 0.0004 | 0.0025 | -0.0516 | 1440.63 | 1741.50 | 0.6418 | 0.6618 |
| los-alerces-2023-w03 | 24 h | agreement_ge_80 | 0.0022 | 0.0033 | -0.0198 | 0.0042 | -0.2037 | 1378.80 | 1670.22 | 0.6216 | 0.6452 |

## Medianas por incendio

| Incendio | Horizonte | Producto | n | Δ IoU mediana | Δ Dice mediana | Δ recall mediana | Δ precisión mediana | Δ sesgo área mediana |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| epuyen-2025 | 12 h | agreement_ge_10 | 6 | -0.0036 | -0.0062 | 0.0062 | -0.0060 | 0.6364 |
| epuyen-2025 | 12 h | agreement_ge_50 | 6 | -0.0004 | -0.0006 | 0.0000 | -0.0002 | 0.0446 |
| epuyen-2025 | 12 h | agreement_ge_80 | 6 | 0.0013 | 0.0020 | -0.0024 | 0.0019 | -0.2208 |
| epuyen-2025 | 24 h | agreement_ge_10 | 6 | -0.0063 | -0.0089 | 0.0133 | -0.0081 | 1.1465 |
| epuyen-2025 | 24 h | agreement_ge_50 | 6 | -0.0004 | -0.0006 | 0.0009 | -0.0006 | 0.2026 |
| epuyen-2025 | 24 h | agreement_ge_80 | 6 | 0.0019 | 0.0025 | -0.0009 | 0.0020 | -0.2330 |
| los-alerces-2023 | 12 h | agreement_ge_10 | 3 | -0.0019 | -0.0025 | 0.0102 | -0.0119 | 0.1869 |
| los-alerces-2023 | 12 h | agreement_ge_50 | 3 | 0.0003 | 0.0003 | 0.0013 | 0.0001 | 0.0051 |
| los-alerces-2023 | 12 h | agreement_ge_80 | 3 | 0.0030 | 0.0040 | -0.0013 | 0.0082 | -0.1440 |
| los-alerces-2023 | 24 h | agreement_ge_10 | 3 | 0.0012 | 0.0018 | 0.0251 | -0.0098 | 0.1547 |
| los-alerces-2023 | 24 h | agreement_ge_50 | 3 | 0.0004 | 0.0006 | 0.0004 | 0.0004 | -0.0252 |
| los-alerces-2023 | 24 h | agreement_ge_80 | 3 | 0.0022 | 0.0033 | -0.0123 | 0.0054 | -0.2037 |
| los-alerces-2024 | 12 h | agreement_ge_10 | 8 | -0.0013 | -0.0016 | 0.0092 | -0.0047 | 0.0448 |
| los-alerces-2024 | 12 h | agreement_ge_50 | 8 | 0.0004 | 0.0005 | -0.0005 | 0.0003 | -0.0054 |
| los-alerces-2024 | 12 h | agreement_ge_80 | 8 | -0.0004 | -0.0004 | -0.0084 | 0.0044 | -0.0471 |
| los-alerces-2024 | 24 h | agreement_ge_10 | 8 | -0.0024 | -0.0028 | 0.0077 | -0.0031 | 0.0505 |
| los-alerces-2024 | 24 h | agreement_ge_50 | 8 | -0.0001 | -0.0001 | -0.0007 | -0.0002 | -0.0075 |
| los-alerces-2024 | 24 h | agreement_ge_80 | 8 | 0.0017 | 0.0018 | -0.0083 | 0.0030 | -0.0442 |
| puerto-patriada-2026 | 12 h | agreement_ge_10 | 6 | -0.0026 | -0.0048 | 0.0069 | -0.0029 | 0.5789 |
| puerto-patriada-2026 | 12 h | agreement_ge_50 | 6 | -0.0002 | -0.0003 | -0.0006 | -0.0003 | -0.0007 |
| puerto-patriada-2026 | 12 h | agreement_ge_80 | 6 | -0.0008 | -0.0010 | -0.0064 | 0.0013 | -0.4326 |
| puerto-patriada-2026 | 24 h | agreement_ge_10 | 6 | -0.0003 | -0.0005 | 0.0058 | -0.0021 | 0.1232 |
| puerto-patriada-2026 | 24 h | agreement_ge_50 | 6 | -0.0008 | -0.0009 | -0.0051 | -0.0002 | -0.0282 |
| puerto-patriada-2026 | 24 h | agreement_ge_80 | 6 | -0.0030 | -0.0036 | -0.0103 | 0.0013 | -0.1081 |

## Consistencia entre incendios

Unidad de análisis: incendio. Se cuenta en cuántos incendios la mediana de sus reinicios favorece a la banda frente a c00.

| Horizonte | Producto | Incendios | IoU: incendios con mediana > 0 | Mediana de medianas Δ IoU | Dice: incendios con mediana > 0 | Recall: incendios con mediana > 0 | Precisión: incendios con mediana > 0 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 12 h | agreement_ge_10 | 4 | 0/4 | -0.0023 | 0/4 | 4/4 | 0/4 |
| 12 h | agreement_ge_50 | 4 | 2/4 | 0.0000 | 2/4 | 1/4 | 2/4 |
| 12 h | agreement_ge_80 | 4 | 2/4 | 0.0004 | 2/4 | 0/4 | 4/4 |
| 24 h | agreement_ge_10 | 4 | 1/4 | -0.0014 | 1/4 | 4/4 | 0/4 |
| 24 h | agreement_ge_50 | 4 | 1/4 | -0.0003 | 1/4 | 2/4 | 1/4 |
| 24 h | agreement_ge_80 | 4 | 3/4 | 0.0018 | 3/4 | 0/4 | 4/4 |

## Envolvente ≥ 0,10 por incendio

| Incendio | Horizonte | n | Δ cobertura cicatriz mediana | Δ cobertura FIRMS mediana | Δ FP ha mediana | Δ área predicha ha mediana |
|---|---:|---:|---:|---:|---:|---:|
| epuyen-2025 | 12 h | 6 | 0.0062 | 0.0135 | 56.11 | 63.85 |
| epuyen-2025 | 24 h | 6 | 0.0133 | 0.0096 | 231.30 | 231.30 |
| los-alerces-2023 | 12 h | 3 | 0.0102 | 0.0082 | 16.92 | 16.92 |
| los-alerces-2023 | 24 h | 3 | 0.0251 | 0.0194 | 60.75 | 79.47 |
| los-alerces-2024 | 12 h | 8 | 0.0092 | 0.0085 | 9.95 | 11.84 |
| los-alerces-2024 | 24 h | 8 | 0.0077 | 0.0081 | 20.56 | 29.38 |
| puerto-patriada-2026 | 12 h | 6 | 0.0069 | 0.0034 | 66.01 | 72.27 |
| puerto-patriada-2026 | 24 h | 6 | 0.0058 | 0.0046 | 113.22 | 132.52 |

## Ancho de la banda frente al crecimiento observado

Mide cuánta sensibilidad meteorológica muestra la capa y cuánto crecimiento observado queda fuera de la envolvente `≥ 0,10`. Medianas por incendio.

| Incendio | Horizonte | n | Crecimiento observado ha | Cobertura c00 | Cobertura ≥ 0,10 | Observado fuera de ≥ 0,10 ha | (área ≥ 0,10 − área ≥ 0,80) / área c00 |
|---|---:|---:|---:|---:|---:|---:|---:|
| epuyen-2025 | 12 h | 6 | 75.15 | 0.9531 | 0.9586 | 2.65 | 0.1038 |
| epuyen-2025 | 24 h | 6 | 279.58 | 0.9368 | 0.9500 | 17.68 | 0.1344 |
| los-alerces-2023 | 12 h | 3 | 141.03 | 0.8655 | 0.8901 | 17.73 | 0.0914 |
| los-alerces-2023 | 24 h | 3 | 468.81 | 0.6414 | 0.6665 | 156.33 | 0.1437 |
| los-alerces-2024 | 12 h | 8 | 210.91 | 0.6722 | 0.6914 | 68.67 | 0.0606 |
| los-alerces-2024 | 24 h | 8 | 481.41 | 0.7875 | 0.7956 | 99.04 | 0.0447 |
| puerto-patriada-2026 | 12 h | 6 | 188.10 | 0.7385 | 0.7439 | 63.63 | 0.1062 |
| puerto-patriada-2026 | 24 h | 6 | 1475.28 | 0.5625 | 0.5866 | 685.12 | 0.0870 |

## Resumen global descriptivo

Agrupa reinicios correlacionados dentro de cada incendio; se presenta después de las medianas por incendio y no constituye una muestra de incendios independientes.

| Horizonte | Producto | n | Δ IoU mediana [IQR; rango] | Mejora IoU | Δ Dice mediana [IQR; rango] | Mejora Dice |
|---:|---|---:|---|---:|---|---:|
| 12 h | agreement_ge_10 | 23 | -0.0027 [-0.0044, 0.0005; -0.0155, 0.0088] | 6/23 (26.1%) | -0.0046 [-0.0062, 0.0005; -0.0267, 0.0111] | 6/23 (26.1%) |
| 12 h | agreement_ge_50 | 23 | 0.0001 [-0.0004, 0.0004; -0.0119, 0.0026] | 13/23 (56.5%) | 0.0002 [-0.0007, 0.0006; -0.0204, 0.0028] | 13/23 (56.5%) |
| 12 h | agreement_ge_80 | 23 | 0.0012 [-0.0030, 0.0032; -0.0116, 0.0104] | 14/23 (60.9%) | 0.0019 [-0.0039, 0.0045; -0.0165, 0.0118] | 14/23 (60.9%) |
| 24 h | agreement_ge_10 | 23 | -0.0019 [-0.0052, 0.0005; -0.0123, 0.0201] | 6/23 (26.1%) | -0.0030 [-0.0065, 0.0007; -0.0163, 0.0262] | 6/23 (26.1%) |
| 24 h | agreement_ge_50 | 23 | -0.0004 [-0.0020, 0.0005; -0.0040, 0.0033] | 11/23 (47.8%) | -0.0005 [-0.0024, 0.0008; -0.0057, 0.0052] | 11/23 (47.8%) |
| 24 h | agreement_ge_80 | 23 | 0.0015 [-0.0012, 0.0022; -0.0086, 0.0099] | 15/23 (65.2%) | 0.0023 [-0.0012, 0.0035; -0.0124, 0.0155] | 15/23 (65.2%) |

## Lectura de ≥ 0,10 como envolvente

La banda `≥ 0,10` se evalúa por cobertura adicional, falsos positivos e inflación de área; no se descarta únicamente por IoU. Las columnas completas por reinicio están en el CSV y el JSON consolidados.

## Veredicto

> Esta sección se escribió a mano el 2026-10-17 sobre el consolidado de 23/23. El resto del
> archivo lo genera `scripts/consolidate_ensemble_backtests.py`; si se regenera, hay que
> reponer esta sección.

**Conclusión: adoptar con limitaciones como capa de acuerdo entre simulaciones. No adoptarla
como mejora predictiva de c00.** Las tres preguntas se responden por separado.

### 1. Infraestructura: válida, reproducible y viable fuera de línea

- Se completaron 23/23 reinicios con 31/31 miembros cada uno. No hubo sustituciones de miembro
  ni de ciclo ni fallos científicos. Todos los ciclos se publicaron completos antes del
  reinicio VIIRS.
- Los 23 `integrity.json` dan `integrity_passed=true`. Esos archivos usan tres esquemas de
  gates (5, 9 y 14 claves) porque se generaron en etapas distintas. Por eso los 23 casos se
  volvieron a auditar, en modo sólo lectura, con el gate de 14 claves de
  `scripts/validate_retained_ensemble.py`. El resultado está en
  `data/ensemble-poc/calibration-backtests-uniform-integrity-audit.json`. Las 13 claves
  científicas pasan en los 23 casos. Epuyén w1 sólo falla `reproducible_materializations_removed`
  porque conserva sus inputs completos a propósito, como primer backtest. En los dos casos de la
  etapa manual (Epuyén w1 y Los Alerces 2024 w5) no existe `member-manifests/`, así que los
  hashes `ws`/`wd`/`m1` se tomaron de `weather_hashes` en su `integrity.json`.
- Incidentes de infraestructura. Ninguno entró al denominador.
  - Dos reintentos transitorios de `download-gefs` que conservaron el ciclo (LA 2024 w4 y PP w2).
  - Un c00 de LA 2023 w1 excluido por transporte antes de ELMFIRE.
  - Un c00 de Epuyén w2 interrumpido por concurrencia y aislado en `failures/`.
  - Una interrupción de la cola el 2026-10-17 a las 05:03 UTC, por cierre de la sesión que la
    había lanzado. Ocurrió durante la materialización de PP w2 p28, sin ELMFIRE en curso. Al
    reanudar, el input parcial se borró y p28 se rehízo desde cero.
- Latencia. La pared de cliente del solver por caso tuvo mediana de 592 s (rango 247 s a 5,4 h;
  el máximo es Epuyén w1 con bind mount y contención). La mediana por miembro fue de 16 s. Con
  descarga y materialización, cada caso tardó cerca de 1 h de reloj en serie. Esa latencia no es
  operativa sin paralelizar miembros.
- Almacenamiento retenido después de la política: 44,7 GiB en total. La mediana es de 1,57 GiB
  por caso, casi todo en rangos GRIB fuente (mediana 1,54 GiB), y los TOA ocupan ~3,8 MiB.
  Epuyén w1 conserva 9,9 GiB por ser el primer backtest.
- Costo: CPU/RSS del solver remoto siguen sin exponerse. No se infiere costo facturable.

### 2. Comunicación de sensibilidad: útil y no degenerada, pero angosta

- En los 23 casos el acuerdo no es vacío ni uniforme y las 31 geometrías son distintas. La capa
  muestra una sensibilidad meteorológica real y trazable.
- La banda es estrecha frente al error del modelo. La diferencia de área entre `≥ 0,10` y
  `≥ 0,80` es el 4–14 % del área de c00 (medianas por incendio). En cambio, el IoU absoluto de
  c00 tiene medianas de 0,08–0,35.
- `≥ 0,10` agrega poca cobertura: +0,6 a +2,5 puntos de cicatriz y +0,3 a +1,9 de FIRMS nuevas.
  Las medianas por incendio de lo observado que queda fuera llegan a 156 ha (LA 2023, 24 h) y a
  685 ha (PP, 24 h). La capa no es una envolvente de dónde puede llegar el fuego. Sólo muestra
  cuánto cambia la simulación cuando cambia la meteorología.
- Por eso la leyenda agrega: “Sólo varía la meteorología: el incendio real puede extenderse
  fuera de la zona ≥ 0,10”. El protocolo de usuarios suma una tarea complementaria que evalúa
  esa lectura. Los roles congelados de las bandas no cambian.

### 3. Mejora predictiva consistente entre incendios: no

Se usaron medianas por incendio (n = 4 incendios). Los reinicios están correlacionados y no se
calculan intervalos ni significancia.

- `≥ 0,80` tiene mediana de Δ IoU positiva en 2/4 incendios a 12 h y en 3/4 a 24 h, con
  magnitud ≤ 0,003. En Puerto Patriada empeora en ambos horizontes (−0,0008 y −0,0030). La
  lectura parcial con 9 casos era 3/3 incendios y no se sostuvo. No se promueve a escenario
  central.
- `≥ 0,50` es prácticamente igual a c00: Δ IoU entre −0,0008 y +0,0004 por incendio, con 2/4
  incendios positivos a 12 h y 1/4 a 24 h.
- `≥ 0,10` gana recall en 4/4 incendios y en ambos horizontes. Lo paga con más área (+12 a
  +231 ha) y FP (+10 a +231 ha), y pierde IoU en 4/4 incendios a 12 h y en 3/4 a 24 h. Como
  envolvente, la cobertura extra es pequeña para el área que agrega.

Ninguna banda supera a c00 de forma consistente entre incendios. Todas las diferencias son mucho
menores que la variación del IoU de c00 entre reinicios (por ejemplo, 0,05–0,32 en Epuyén a 12 h).

## Artefactos individuales

- `epuyen-2025-w01`: `data/ensemble-poc/backtest-epuyen-20250115T1833Z-gefs-2025011512/backtest-metrics.json`, `data/ensemble-poc/backtest-epuyen-20250115T1833Z-gefs-2025011512/integrity.json`.
- `epuyen-2025-w02`: `data/ensemble-poc/backtest-epuyen-2025-w02-gefs-2025011600/backtest-metrics.json`, `data/ensemble-poc/backtest-epuyen-2025-w02-gefs-2025011600/integrity.json`.
- `epuyen-2025-w03`: `data/ensemble-poc/backtest-epuyen-2025-w03-gefs-2025011612/backtest-metrics.json`, `data/ensemble-poc/backtest-epuyen-2025-w03-gefs-2025011612/integrity.json`.
- `epuyen-2025-w04`: `data/ensemble-poc/backtest-epuyen-2025-w04-gefs-2025011700/backtest-metrics.json`, `data/ensemble-poc/backtest-epuyen-2025-w04-gefs-2025011700/integrity.json`.
- `epuyen-2025-w05`: `data/ensemble-poc/backtest-batch-c/epuyen-2025-w05-gefs-2025011712/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/epuyen-2025-w05-gefs-2025011712/integrity.json`.
- `epuyen-2025-w06`: `data/ensemble-poc/backtest-batch-c/epuyen-2025-w06-gefs-2025011800/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/epuyen-2025-w06-gefs-2025011800/integrity.json`.
- `los-alerces-2023-w01`: `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w01/backtest-metrics.json`, `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w01/integrity.json`.
- `los-alerces-2023-w02`: `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w02/backtest-metrics.json`, `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w02/integrity.json`.
- `los-alerces-2023-w03`: `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w03/backtest-metrics.json`, `data/ensemble-poc/backtest-lote-a/los-alerces-2023-w03/integrity.json`.
- `los-alerces-2024-w01`: `data/ensemble-poc/backtest-calibration/los-alerces-2024-w01-gefs-2024012600/backtest-metrics.json`, `data/ensemble-poc/backtest-calibration/los-alerces-2024-w01-gefs-2024012600/integrity.json`.
- `los-alerces-2024-w02`: `data/ensemble-poc/backtest-calibration/los-alerces-2024-w02-gefs-2024012612/backtest-metrics.json`, `data/ensemble-poc/backtest-calibration/los-alerces-2024-w02-gefs-2024012612/integrity.json`.
- `los-alerces-2024-w03`: `data/ensemble-poc/backtest-calibration/los-alerces-2024-w03-gefs-2024012700/backtest-metrics.json`, `data/ensemble-poc/backtest-calibration/los-alerces-2024-w03-gefs-2024012700/integrity.json`.
- `los-alerces-2024-w04`: `data/ensemble-poc/backtest-calibration/los-alerces-2024-w04-gefs-2024012712/backtest-metrics.json`, `data/ensemble-poc/backtest-calibration/los-alerces-2024-w04-gefs-2024012712/integrity.json`.
- `los-alerces-2024-w05`: `data/ensemble-poc/backtest-los-alerces-2024-w05-gefs-2024012800/backtest-metrics.json`, `data/ensemble-poc/backtest-los-alerces-2024-w05-gefs-2024012800/integrity.json`.
- `los-alerces-2024-w06`: `data/ensemble-poc/backtest-los-alerces-2024-w06-gefs-2024012812/backtest-metrics.json`, `data/ensemble-poc/backtest-los-alerces-2024-w06-gefs-2024012812/integrity.json`.
- `los-alerces-2024-w07`: `data/ensemble-poc/backtest-los-alerces-2024-w07-gefs-2024012900/backtest-metrics.json`, `data/ensemble-poc/backtest-los-alerces-2024-w07-gefs-2024012900/integrity.json`.
- `los-alerces-2024-w08`: `data/ensemble-poc/backtest-los-alerces-2024-w08-gefs-2024012912/backtest-metrics.json`, `data/ensemble-poc/backtest-los-alerces-2024-w08-gefs-2024012912/integrity.json`.
- `puerto-patriada-2026-w01`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w01-gefs-2026010512/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w01-gefs-2026010512/integrity.json`.
- `puerto-patriada-2026-w02`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w02-gefs-2026010600/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w02-gefs-2026010600/integrity.json`.
- `puerto-patriada-2026-w03`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w03-gefs-2026010612/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w03-gefs-2026010612/integrity.json`.
- `puerto-patriada-2026-w04`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w04-gefs-2026010700/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w04-gefs-2026010700/integrity.json`.
- `puerto-patriada-2026-w05`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w05-gefs-2026010712/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w05-gefs-2026010712/integrity.json`.
- `puerto-patriada-2026-w06`: `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w06-gefs-2026010800/backtest-metrics.json`, `data/ensemble-poc/backtest-batch-c/puerto-patriada-2026-w06-gefs-2026010800/integrity.json`.
