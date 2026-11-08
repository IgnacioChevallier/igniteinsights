"""Diagnóstico de copa del primer reinicio, fuera de línea (docs/resultados/pronostico/p24.md).

Compara, celda por celda y hora por hora, dos criterios de iniciación de copa:

- **CFIS** (Cruz, Alexander y Wakimoto 2004, Forest Science 50:640, tabla 4): regresión logística
  con el viento a 10 m en campo abierto, la separación entre estratos (FSG), el consumo superficial
  (SFC, en tres categorías) y la humedad fina estimada (EFFM). Corte en P = 0,5. No usa Rothermel.
- **Lo que hace ELMFIRE 2025.0212**: Van Wagner sobre la intensidad superficial de Rothermel, con el
  viento a media llama reducido por su WAF (`elmfire_spread_rate.f90` CROWN_SPREAD_RATE,
  `elmfire_init.f90` CALC_WIND_ADJUSTMENT_FACTOR_*). Rothermel/Albini reimplementado acá sin
  pendiente: es un orden de magnitud, no ELMFIRE byte a byte.

Cruz y Alexander (2010, IJWF 19:377) documentan que el acople Rothermel + Van Wagner subpredice la
copa; esto mide cuánto en los incendios del benchmark, sin correr nada ni ajustar nada.
"""
import numpy as np

# Tabla 4 de Cruz et al. (2004). U10 en km/h, FSG en m, EFFM en %.
CFIS_CONSTANTE, CFIS_U10, CFIS_FSG, CFIS_EFFM = 4.236, 0.357, -0.710, -0.331
CFIS_SFC_MENOR_1, CFIS_SFC_1_A_2 = -4.613, -1.856   # SFC < 1 kg/m², 1–2 kg/m²; > 2: 0
CFIS_CORTE = 0.5
LB_FT2_A_KG_M2 = 4.8824
PIE_M = 0.3048
MPH_20FT_A_KMH_10M = 1.609 / 0.87    # el mismo factor que ELMFIRE en CROWN_SPREAD_RATE
HUMEDAD_FOLIAR = 90.0                # FOLIAR_MOISTURE_CONTENT por defecto; el repo no lo escribe


def prob_cfis(u10_kmh, fsg_m, sfc_kg_m2, effm_pct) -> np.ndarray:
    sfc = np.asarray(sfc_kg_m2, dtype="float64")
    dummies = np.where(sfc < 1.0, CFIS_SFC_MENOR_1, np.where(sfc < 2.0, CFIS_SFC_1_A_2, 0.0))
    g = (CFIS_CONSTANTE + CFIS_U10 * np.asarray(u10_kmh) + CFIS_FSG * np.asarray(fsg_m)
         + dummies + CFIS_EFFM * np.asarray(effm_pct))
    return 1.0 / (1.0 + np.exp(-g))


def intensidad_critica(cbh_m, fmc_pct: float = HUMEDAD_FOLIAR) -> np.ndarray:
    """Van Wagner (1977) como lo escribe ELMFIRE: (0,01 · CBH · (460 + 26 · FMC))^1,5, kW/m."""
    return (0.01 * np.maximum(cbh_m, 0.1) * (460.0 + 26.0 * fmc_pct)) ** 1.5


def _waf_sin_dosel(profundidad_ft: float) -> float:
    if profundidad_ft <= 1e-4:
        return 0.0
    term1 = (1.0 + 0.36) / np.log((20.0 + 0.36 * profundidad_ft) / (0.13 * profundidad_ft))
    return float(term1 * (np.log((1.0 + 0.36) / 0.13) - 1.0))


def waf_elmfire(cc_frac, ch_m, profundidad_ft: float, crown_ratio: float = 1.0) -> np.ndarray:
    """CALC_WIND_ADJUSTMENT_FACTOR_EVERYWHERE (`elmfire_init.f90:523-571`): con F = CC/3 ·
    CROWN_RATIO ≥ 0,05, el WAF bajo dosel de Albini y Baughman; por debajo, la mezcla con el WAF
    del lecho. La tabla va por CC entero en % y CH entero en m, y vale 0 sin dosel (`:121-127`).
    `crown_ratio`: el de `&SIMULATOR` (default de ELMFIRE 1,0; el repo no lo escribe)."""
    cc = np.asarray(cc_frac, dtype="float64")
    icc = np.clip(np.rint(cc * 100), 0, 100) / 100
    ich = np.clip(np.rint(np.asarray(ch_m, dtype="float64")), 0, 120)
    libre = _waf_sin_dosel(profundidad_ft)
    hft = ich / PIE_M
    with np.errstate(divide="ignore", invalid="ignore"):
        protegido = (1.0 / np.log((20.0 + 0.36 * hft) / (0.13 * hft))) \
            * (0.555 / np.sqrt(0.3333 * icc * crown_ratio * hft))
    protegido = np.where((icc > 1e-4) & (ich > 1e-4), np.minimum(protegido, libre), 0.0)
    f = 0.3333 * cc * crown_ratio
    fraccion_libre = 1.0 - 20.0 * f
    waf = np.where(f >= 0.05, protegido, fraccion_libre * libre + (1 - fraccion_libre) * protegido)
    return np.where(cc < 0, 0.0, waf)


def rothermel(modelo: list[str], m1, m10, m100, mlh: float, mlw: float, u_mf_ft_min):
    """(velocidad ft/min, intensidad de Byram kW/m) de una fila de `fuel_models.csv` (id, nombre,
    dinámico, cargas lb/ft² 1h/10h/100h/herb/leñosa, SAV 1h/herb/leñosa, profundidad ft, Mx %,
    calor Btu/lb). Humedades en fracción; viento a media llama en ft/min. Sin pendiente ni
    límite de viento (no muerde en estos combustibles; ver diagnóstico P-24)."""
    w1, w10, w100, wh, wl = (float(x) for x in modelo[3:8])
    s1, sh, sl = (float(x) for x in modelo[8:11])
    prof, mx, calor = float(modelo[11]), float(modelo[12]) / 100, float(modelo[13])
    m1, m10, m100 = (np.asarray(x, dtype="float64") for x in (m1, m10, m100))
    u = np.asarray(u_mf_ft_min, dtype="float64")
    herb_muerta = 0.0
    if modelo[2].strip().upper() == ".TRUE." and wh > 0:   # curado: con LH ≤ 30 % todo muerto
        vivo = min(max((mlh - 0.30) / 0.90, 0.0), 1.0)
        herb_muerta, wh = wh * (1 - vivo), wh * vivo
    muertas = [(w1, s1, m1), (w10, 109.0, m10), (w100, 30.0, m100), (herb_muerta, sh, m1)]
    vivas = [(wh, sh, mlh), (wl, sl, mlw)]
    rho_p, st, se = 32.0, 0.0555, 0.010

    def areas(clases):
        a = [w * s / rho_p for w, s, _ in clases]
        return a, sum(a)

    a_d, at_d = areas(muertas)
    a_v, at_v = areas(vivas)
    at = at_d + at_v
    sigma_d = sum(a * s for a, (_, s, _) in zip(a_d, muertas)) / at_d
    sigma_v = sum(a * s for a, (_, s, _) in zip(a_v, vivas)) / at_v if at_v else 0.0
    sigma = (at_d * sigma_d + at_v * sigma_v) / at
    carga = sum(w for w, _, _ in muertas + vivas)
    beta = carga / prof / rho_p
    rel = beta / (3.348 * sigma ** -0.8189)
    a_ = 133.0 * sigma ** -0.7913
    gmax = sigma ** 1.5 / (495 + 0.0594 * sigma ** 1.5)
    gamma = gmax * rel ** a_ * np.exp(a_ * (1 - rel))
    wn_d = sum(a / at_d * w for a, (w, _, _) in zip(a_d, muertas)) * (1 - st)
    wn_v = sum(a / at_v * w for a, (w, _, _) in zip(a_v, vivas)) * (1 - st) if at_v else 0.0
    md = sum(a / at_d * m for a, (_, _, m) in zip(a_d, muertas))
    mv = sum(a / at_v * m for a, (_, _, m) in zip(a_v, vivas)) if at_v else 0.0
    fino_d = sum(w * np.exp(-138 / s) for w, s, _ in muertas)
    fino_v = sum(w * np.exp(-500 / s) for w, s, _ in vivas)
    if fino_v > 0:
        mf = sum(w * np.exp(-138 / s) * m for w, s, m in muertas) / fino_d
        mx_v = np.maximum(2.9 * (fino_d / fino_v) * (1 - mf / mx) - 0.226, mx)
    else:
        mx_v = mx

    def eta(m, mxx):
        r = np.minimum(m / mxx, 1.0)
        return np.clip(1 - 2.59 * r + 5.11 * r ** 2 - 3.52 * r ** 3, 0, 1)

    ir = gamma * calor * 0.174 * se ** -0.19 * (wn_d * eta(md, mx) + wn_v * eta(mv, mx_v))
    xi = np.exp((0.792 + 0.681 * sigma ** 0.5) * (beta + 0.1)) / (192 + 0.2595 * sigma)
    c = 7.47 * np.exp(-0.133 * sigma ** 0.55)
    b = 0.02526 * sigma ** 0.54
    e = 0.715 * np.exp(-3.59e-4 * sigma)
    phi_w = c * np.maximum(u, 0) ** b * rel ** -e
    qig = sum(a / at * (250 + 1116 * m) * np.exp(-138 / s)
              for a, (_, s, m) in zip(a_d + a_v, muertas + vivas))
    ros = ir * xi * (1 + phi_w) / (beta * rho_p * qig)
    flin = ir * (384 / sigma) * ros / 60 * 3.4613
    return ros, flin


def consumo_superficial(modelo: list[str], con_100h: bool) -> float:
    """SFC (kg/m²) declarado, no ajustado: 1h + 10h (cota baja) o todo lo muerto más la
    herbácea (cota alta). CFIS lo usa sólo por categorías (< 1, 1–2, > 2)."""
    w1, w10, w100, wh = (float(x) for x in modelo[3:7])
    return (w1 + w10 + (w100 + wh if con_100h else 0.0)) * LB_FT2_A_KG_M2
