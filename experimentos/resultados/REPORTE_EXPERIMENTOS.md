# Reporte Técnico de Experimentación en Contenedor: Siniestros Las Condes 2025

**Fecha de ejecución:** 2026-11-03 15:47:01 UTC  
**Entorno de ejecución:** Python `3.12.16` sobre `Linux-5.15.153.1-microsoft-standard-WSL2-x86_64-with-glibc2.41`  
**Muestra analizada:** $n = 676$ siniestros georreferenciados (2025-01-02 a 2025-12-29)  

---

## 1. Corrección del Error Solar (+12 h) y Auditoría de Calidad de Datos

- **Verificación matemática del sesgo solar (+12 h):**
  - Error Medio Absoluto (MAE) entre `sol_alt_grados` original y cálculo astronómico NOAA real: **60.24°**.
  - MAE entre `sol_alt_grados` original y cálculo astronómico desplazado en $+12\text{ h}$: **0.09°** (confirma que el pipeline previo sumó 12 horas al convertir la hora local).
  - Porcentaje de siniestros nocturnos (`altitud <= 0°`): cae desde **69.38%** (erróneo) a **24.41%** (corregido: 511 diurnos, 31 crepúsculo, 48 noche y 86 noche cerrada).
  - **Atropellos diurnos:** 32 de 42 atropellos (**76.2%**) ocurren con luz de día, y 106 siniestros ocurren en ventana de sol rasante ($0^\circ < \text{alt} \le 15^\circ$).
- **Coherencia posicional y vial:**
  - Registros dentro del *bounding box* comunal de Las Condes: **675/676 (99.85%)**.
  - Mediana de dispersión posicional entre siniestros asignados a la misma intersección (`Calle_Uno x Calle_Dos`, $n=279$): **0.0 m** (100.0% dentro de 100 m).

---

## 2. Correlaciones Estadísticas y Factores Asociados a la Severidad

### 2.1. Asociaciones Categóricas Significativas ($p < 0,05$, Test Exacto de Fisher / $\chi^2$)

| Hipótesis Evaluada | % Evento Expuestos | % Evento No Expuestos | Odds Ratio (IC 95%) | $p$-valor (Fisher) | $V$ de Cramér |
|---|---:|---:|---:|---:|---:|
| Atropello a peatón -> Siniestro con lesionados | 88.1% (37/42) | 22.4% (142/634) | **25.639** (9.892–66.453) | `0.0` | 0.358 |
| Cualquier usuario vulnerable (peatón/moto/bici) -> Siniestro con lesionados | 58.18% (96/165) | 16.24% (83/511) | **7.174** (4.865–10.581) | `0.0` | 0.407 |
| Usuario vulnerable (peatón/moto/bici) -> Siniestro grave o fatal | 20.61% (34/165) | 2.54% (13/511) | **9.942** (5.1–19.381) | `0.0` | 0.303 |
| Atropello a peatón -> Siniestro grave o fatal | 30.95% (13/42) | 5.36% (34/634) | **7.911** (3.775–16.578) | `1e-06` | 0.24 |
| Involucramiento de motocicleta -> Siniestro grave o fatal | 19.61% (20/102) | 4.7% (27/574) | **4.941** (2.65–9.214) | `2e-06` | 0.206 |
| Involucramiento de motocicleta -> Siniestro con lesionados | 45.1% (46/102) | 23.17% (133/574) | **2.724** (1.762–4.21) | `9e-06` | 0.174 |
| Involucramiento de bicicleta -> Siniestro con lesionados | 64.0% (16/25) | 25.04% (163/651) | **5.322** (2.308–12.276) | `6.6e-05` | 0.162 |
| Causa específica (maniobra/semáforo/alcohol/peatón vs 'no atento') -> Con lesionados | 43.33% (39/90) | 23.89% (140/586) | **2.436** (1.541–3.852) | `0.000183` | 0.145 |
| Desobedecer semáforo o preferencia de paso -> Con lesionados | 66.67% (10/15) | 25.57% (169/661) | **5.822** (1.962–17.277) | `0.001139` | 0.132 |
| Ocurrencia en cruce (semaforizado o con señal) -> Con lesionados | 24.07% (136/565) | 38.74% (43/111) | **0.501** (0.327–0.769) | `0.002101` | 0.117 |
| Zona alta precordillerana (>= 750 m s.n.m.) -> Siniestro grave o fatal | 14.94% (13/87) | 5.77% (34/589) | **2.868** (1.448–5.681) | `0.004994` | 0.115 |
| Zona alta precordillerana (>= 750 m s.n.m.) -> Con lesionados | 36.78% (32/87) | 24.96% (147/589) | **1.749** (1.089–2.81) | `0.026316` | 0.081 |
| Causa específica distinta a 'no atento' -> Siniestro grave o fatal | 12.22% (11/90) | 6.14% (36/586) | **2.127** (1.04–4.35) | `0.044214` | 0.072 |

### 2.2. Modelos Multivariados de Regresión Logística

- **Modelo 1 (`con_lesionados`, Pseudo-$R^2$ McFadden = `0.2018`, $p < 10^{-10}$):**
  - El involucramiento de usuarios vulnerables domina la probabilidad de lesiones: Atropello ($\text{OR}_{\text{ajustado}} = 37.995$, $p < 0,0001$), Bicicleta ($\text{OR}_{\text{ajustado}} = 9.805$, $p < 0,0001$) y Motocicleta ($\text{OR}_{\text{ajustado}} = 4.323$, $p < 0,0001$).
- **Modelo 2 (`grave_o_fatal`, Pseudo-$R^2$ McFadden = `0.2287`, $p < 10^{-10}$):**
  - Incrementan significativamente la probabilidad de muerte o lesión grave: **Atropello** ($\text{OR}_{\text{ajustado}} = 16.639$, $p < 0,0001$), **Bicicleta** ($\text{OR}_{\text{ajustado}} = 5.616$, $p < 0,0001$), **Motocicleta** ($\text{OR}_{\text{ajustado}} = 9.898$, $p < 0,0001$) y **Causa específica distinta a 'no atento'** ($\text{OR}_{\text{ajustado}} = 1.913$, $p = 0.119313$).

---

## 3. Detección de Puntos Calientes (Hotspots) y Desacoplamiento Concentración vs. Severidad

- **Estadístico Espacial Getis-Ord $G_i^*$ (Grilla $250\text{ m} \times 250\text{ m}$, vecindad $d \le 400\text{ m}$):**
  - Sobre 271 celdas activas, se identifican **22 celdas *hotspot* por frecuencia ($p \le 0,05$)** y **12 celdas *hotspot* por severidad ponderada EPDO ($p \le 0,05$)**.
- **Clustering Espacial DBSCAN ($\varepsilon = 150\text{ m}$, $\text{min\_samples} = 5$, métrica Haversine):**
  - Se detectan **39 micro-clusters críticos** que agrupan **377 siniestros (55.77% del total comunal)**.

### Top 10 Micro-Clusters Críticos ordenados por Severidad Equivalente (EPDO)

| Rank | Cluster / Nodo Dominante | Siniestros ($N$) | Puntaje EPDO | EPDO Medio | % Lesionados | % Grave/Fatal | Motos | Atropellos | Bicis |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | APOQUINDO x CUARTO CENTENARIO | 38 | **52** | 1.37 | 28.9% | 0.0% | 3 | 3 | 0 |
| 2 | LAS CONDES (TRAMO) | 19 | **34** | 1.79 | 31.6% | 10.5% | 5 | 1 | 2 |
| 3 | CUARTO CENTENARIO (TRAMO) | 9 | **33** | 3.67 | 33.3% | 22.2% | 1 | 0 | 0 |
| 4 | APOQUINDO (TRAMO) | 16 | **29** | 1.81 | 25.0% | 12.5% | 2 | 2 | 0 |
| 5 | PRESIDENTE KENNEDY (TRAMO) | 16 | **24** | 1.5 | 25.0% | 6.2% | 2 | 2 | 1 |
| 6 | MANQUEHUE SUR (TRAMO) | 15 | **23** | 1.53 | 26.7% | 6.7% | 2 | 0 | 2 |
| 7 | ANDRES BELLO x NUEVA TAJAMAR | 14 | **22** | 1.57 | 28.6% | 7.1% | 3 | 0 | 3 |
| 8 | LAS CONDES x SAN FRANCISCO DE ASIS | 7 | **20** | 2.86 | 57.1% | 28.6% | 3 | 2 | 0 |
| 9 | ANDRES BELLO x PRESIDENTE RIESCO | 13 | **19** | 1.46 | 15.4% | 7.7% | 4 | 0 | 0 |
| 10 | CERRO COLORADO x MANQUEHUE NORTE | 5 | **19** | 3.8 | 60.0% | 20.0% | 0 | 1 | 0 |

---

## 4. Formulación de Medidas de Mitigación Basadas en Evidencia

| Código | Línea de Acción | Medida Concreta | Población Objetivo en Muestra (2025) |
|---|---|---|---|
| **MIT-01** | Protección de Cruces Semaforizados para Usuarios Vulnerables | Implementar fases semafóricas de salida anticipada peatonal (LPI - Leading Pedestrian Interval de 4–6 s), cajas de detención adelantada para motocicletas/bicicletas (motobox/bikebox) y eliminación de giros libres en rojo en los 15 cruces con Hotspot Getis-Ord Gi* (p < 0.05). | **134 siniestros**, **78 lesionados**, **26 graves/fatales** |
| **MIT-02** | Gestión de Pistas y Conflictos Laterales de Motocicletas (Delivery y Commuting) | Segregación táctica de virajes, demarcación de canalización en intersecciones complejas, zonas de detención exclusiva para reparto (delivery) fuera de la primera pista de circulación y fiscalización automatizada de cambios sorpresivos de pista. | **38 siniestros**, **20 lesionados**, **7 graves/fatales** |
| **MIT-03** | Seguridad Vial Nocturna y de Fin de Semana contra Choques a Elementos Fijos | Instalación de delineadores direccionales retroreflectivos, amortiguadores de impacto en puntas de islas/bandejones centrales, iluminación LED de alto contraste en curvas/enlaces y controles preventivos focalizados viernes/sábado 22:00–06:00 h. | **35 siniestros**, **14 lesionados**, **3 graves/fatales** |
| **MIT-04** | Mitigación Climática y Topográfica en Pavimento Húmedo y Sector Precordillerano | Tratamiento superficial antideslizante de alta fricción (HFST) en pendientes longitudinales >4%, mejoramiento de drenaje superficial y señalización dinámica variable activada por humedad/precipitación (>0.2 mm/h o humedad >=85%). | **41 siniestros**, **21 lesionados**, **3 graves/fatales** |
| **MIT-05** | Pacificacíon Peatonal Diurna en Polos Laborales, Educacionales y de Servicios | Cruces peatonales a nivel de acera (pasos elevados) en accesos de calles secundarias a ejes arteriales, refugios peatonales en calzadas de >= 4 pistas y viseras/orientación de semáforos en horarios de sol rasante (0° < altitud solar <= 15°). | **39 siniestros**, **36 lesionados**, **13 graves/fatales** |
| **MIT-06** | Estandarización del Registro Policial/Municipal de Causas y Auditoría de Geocodificación | Reemplazar el campo libre/genérico de causa por una lista de verificación multifactorial obligatoria en terreno (maniobra previa, fase semafórica, estado de calzada, visibilidad real) y captura automática de coordenada GPS con validación contra catastro vial. | **90 siniestros**, **56 lesionados**, **11 graves/fatales** |
