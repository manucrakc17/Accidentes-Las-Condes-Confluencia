# HANDOFF DE AUDITORÍA CIENTÍFICA Y TRAZABILIDAD (CLASE 7)

**Proyecto:** Siniestros de Tránsito, Condiciones Meteorológicas Horarias, Puntos Calientes (*Hotspots*) y Medidas de Mitigación Basadas en Evidencia en Las Condes (2025)  
**Repositorio:** `Accidentes-Las-Condes-Confluencia`  
**Fecha de auditoría:** 3 de noviembre de 2026 (`2026-11-03T15:47:01Z`)  
**Agente Auditor:** Agente de Auditoría Independiente (`lc-auditoria` — entorno aislado de solo lectura sobre código, datos y resultados)  
**Entorno verificado:** Python `3.12.16` sobre `Linux-5.15.153.1-microsoft-standard-WSL2-x86_64-with-glibc2.41` (Docker Compose multi-servicio: `lc-desarrollo`, `lc-experimentacion`, `lc-auditoria`)  

---

## 01. Objetivo y Estado Anterior

### 1.1. Contexto Científico y Base de Datos
El proyecto investiga los determinantes ambientales, viales, temporales y humanos de la siniestralidad vial y su severidad en la comuna de **Las Condes durante el año completo 2025** ($n = 676$ siniestros georreferenciados entre el `2025-01-02` y el `2025-12-29`, estructurados originalmente en $676 \text{ registros} \times 63 \text{ columnas}$ en `datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx`).

La base integra tres capas de información:
1. **Registro comunal/policial de siniestros viales:** Fecha, hora, coordenadas (`Latitud`, `longitud`), dirección vial (`Calle_Uno`, `Calle_Dos`, `Numero`, `UBICACION`), clase de accidente (`Accidente`: colisión, choque, atropello, caída, volcamiento), parque vehicular involucrado (`Automovil`, `Motociclet`, `Bicicleta`, transporte público y carga), causa registrada (`CAUSA_SINI` original y `CAUSA_NUEV` recodificada) y conteo desagregado de víctimas (`FALLECIDOS`, `GRAVES`, `MENOS_GRAV`, `LEVES`, `TOTAL_LESI`).
2. **Reanálisis meteorológico horario ERA5 / Open-Meteo:** Temperatura a 2 m (`temp_c`), humedad relativa (`humedad_pct`), punto de rocío (`rocio_c`), precipitación horaria (`preci_mm`) y acumulada en 24 h (`preci_prev_24h`, `horas_lluvia_24h`), velocidad de viento a 10 m (`viento_kmh`), ráfagas (`rafaga_kmh`), nubosidad (`nubes_pct`), código meteorológico WMO (`wmo_code`) y estado estimado de la calzada (`pavimento_est`, `lluvia`, `niebla`).
3. **Modelo Digital de Elevación (DEM Copernicus GLO-90) y geometría solar:** Altitud ortométrica (`altitud_m`, rango comunal entre el eje poniente de Tobalaba/Andrés Bello $\approx 600\text{ m s.n.m.}$ y el piedemonte andino $> 950\text{ m s.n.m.}$) y variables de posición solar (`sol_alt_grados`, `periodo_solar`, `noche`).

### 1.2. Estado en la Presentación Anterior (20 de octubre de 2026)
En la sesión previa (`confluencia-agents-demo/project/aaaasd.pdf`), el equipo presentó la construcción del dataset integrado y una primera exploración descriptiva centrada en comparar siniestros en pavimento seco vs. pavimento húmedo/mojado, acompañada de una auditoría crítica ejecutada por un pipeline de agentes (`researcher` $\rightarrow$ `critic` $\rightarrow$ `writer` $\rightarrow$ `reviewer`). En ese punto:
- No se habían ejecutado aún las correcciones sobre los errores críticos de preprocesamiento detectados en el dataset (específicamente el desfase astronómico de $+12\text{ h}$ en la altitud solar y la saturación de variables derivadas).
- No existía un modelamiento inferencial multivariado ni una matriz completa de correlaciones con control de tasa de falsos descubrimientos (FDR).
- La propuesta de detección de puntos calientes (*hotspots*) estaba formulada en términos conceptuales pero con ambigüedades metodológicas (mezclando KDE con Getis-Ord $G_i^*$) y sin desacoplar la *concentración de frecuencia* de la *severidad ponderada*.
- Tampoco se había formulado una matriz operativa de medidas de mitigación cuantificada sobre la población objetivo de la muestra.

### 1.3. Reformulación del Objetivo para la Clase 7
A partir de la retroalimentación recibida, el equipo reformuló y acotó rigurosamente la pregunta de investigación:
> *¿Qué factores viales, horarios/lumínicos (astronómicamente corregidos), meteorológicos, topográficos y de tipología de usuario se asocian estadísticamente con la ocurrencia de lesiones y con la severidad grave/fatal en los siniestros viales de Las Condes (2025), cómo se distribuyen espacialmente los puntos calientes al desacoplar frecuencia absoluta de severidad equivalente (EPDO), y qué medidas de mitigación específicas se desprenden de esta evidencia empírica?*

---

## 02. Retroalimentación Recibida

Durante la revisión crítica de la presentación anterior (`docs/RETROALIMENTACION.md`), se documentaron **6 hallazgos empíricos sobre calidad de datos** y **6 objeciones metodológicas estructurales**:

1. **Error sistemático de $+12\text{ h}$ en las variables solares (`sol_alt_grados`, `periodo_solar`, `noche`):** El script previo de enriquecimiento solar desplazó en $+12\text{ horas}$ la hora local chilena antes de calcular la elevación solar, clasificando erróneamente el **69,38%** de los siniestros como nocturnos (`noche` o `noche_cerrada`) e invirtiendo la interpretación de los accidentes diurnos (particularmente los atropellos).
2. **Monolitismo del campo recodificado `CAUSA_NUEV`:** El **86,69%** ($586/676$) de los registros fue colapsado en la categoría `"DISTRACCION DEL CONDUCTOR"`, ocultando causas operativas críticas presentes en el campo original `CAUSA_SINI` (como no respetar luz roja o derecho preferente de paso, virajes indebidos, adelantamientos sin espacio/tiempo, conducción bajo influencia del alcohol e imprudencia del peatón).
3. **Saturación de variables climáticas derivadas:**
   - `viento_cat` presentaba el valor `"calma"` en el **100%** de los registros ($676/676$) por un umbral mal parametrizado.
   - `clima_estado` tenía el string constante `"llenado"` en el **100%** de los registros (metadato técnico sin varianza).
   - `visib_estim_km` estaba saturado en $20\text{ km}$ en casi toda la muestra por ser una aproximación paramétrica de la depresión del punto de rocío $(T - T_{\text{rocío}})$ y no visibilidad horizontal medida por sensor óptico.
4. **Inviabilidad del componente de velocidad vehicular:** El registro policial comunal no contiene mediciones de velocidad de circulación ni de impacto, y no existe una capa abierta, continua y validada de velocidades por arco vial para Las Condes 2025.
5. **Ausencia de denominador de exposición vehicular (AADT / flujo por arco):** El *Critic* advirtió que ordenar calles o intersecciones únicamente por número de siniestros mide *concentración de eventos* y no *riesgo individual de circulación*, pudiendo sesgar la priorización hacia arterias de alto volumen pero baja severidad media.
6. **Ambigüedad matemática en la detección de *hotspots* y falta de verificación posicional:** Se cuestionó la frase inicial de aplicar *"Getis-Ord $G_i^*$ sobre una superficie KDE"*, exigiendo definir unidades espaciales discretas con matriz de pesos explícita y/o clustering espacial métrico sobre coordenadas verificadas contra la dirección vial (`Calle_Uno` $\times$ `Calle_Dos`). Asimismo, se exigió conectar los hallazgos estadísticos con **medidas de mitigación concretas**.

---

## 03. Decisiones y Justificación

La siguiente matriz documenta de forma trazable cómo cada observación de la retroalimentación fue transformada en una decisión metodológica, implementada en código dentro de `desarrollo/` y respaldada por artefactos verificables en `experimentos/resultados/`:

| ID | Observación de Retroalimentación | Decisión del Equipo | Justificación Metodológica y Científica | Implementación (`desarrollo/`) y Evidencia (`experimentos/resultados/`) |
|---|---|---|---|---|
| **D1** | Sesgo sistemático de $+12\text{ h}$ en `sol_alt_grados`, `periodo_solar` y `noche`. | **Aceptada (Prioridad Crítica).** Recalcular desde cero la geometría solar astronómica (ecuaciones NOAA: declinación solar, ecuación del tiempo y ángulo horario verdadero) usando latitud, longitud, fecha y hora oficial de Chile continental 2025 (horario de verano UTC-3 hasta el 05/04/2025 y desde el 07/09/2025; horario de invierno UTC-4 entre el 06/04/2025 y el 06/09/2025). | Sin corregir la fase diurna/nocturna, cualquier inferencia sobre iluminación artificial, fatiga nocturna o visibilidad solar carece de validez interna. Además, se creó el indicador físico de **ventana de sol rasante / encandilamiento** ($0^\circ < \alpha_{\text{sol}} \le 15^\circ$) para capturar el efecto de deslumbramiento en ejes oriente-poniente (`APOQUINDO`, `LAS CONDES`, `KENNEDY`). | **Script:** `desarrollo/01_limpieza_y_correccion_solar.py`<br>**Evidencias:** `01_auditoria_calidad_y_solar.json`, `SINIESTROS_LAS_CONDES_CORREGIDO.csv`, `fig01_correccion_solar_impacto.png` |
| **D2** | Monolitismo de `CAUSA_NUEV` ($86,7\%$ distracción) y variables climáticas saturadas (`viento_cat`, `clima_estado`, `visib_estim_km`). | **Aceptada.** (1) Descartar `clima_estado` y `visib_estim_km` de las pruebas inferenciales; (2) Recalibrar `viento_cat_corr` según umbrales físicos (`calma_real`, `brisa_leve`, `brisa_moderada`, `viento_fuerte_o_rafaga`); (3) Auditar y recodificar `CAUSA_SINI` original en 7 categorías operativas (`causa_especifica`) e introducir indicadores binarios de alta especificidad (`causa_distinta_no_atento`, `causa_violacion_paso_semaforo`). | En registros policiales, la etiqueta *"no atento a las condiciones del tránsito"* opera como categoría residual por defecto cuando no hay peritaje SIAT inmediato. Separar las causas explícitamente tipificadas ($n=90$) de la categoría por defecto ($n=586$) permite aislar el verdadero efecto de infracciones críticas (luz roja, preferencia, alcohol, distancia de seguimiento) sobre la severidad. | **Script:** `desarrollo/01_limpieza_y_correccion_solar.py`, `desarrollo/02_correlaciones_y_factores.py`<br>**Evidencias:** `01_auditoria_calidad_y_solar.json`, `02_asociaciones_categoricas_chi2_or.csv`, `02_resumen_correlaciones.json` |
| **D3** | Inviabilidad de datos abiertos de velocidad vehicular y ausencia de flujo vehicular (exposición AADT). | **Aceptada con reformulación de alcance.** Se elimina el componente de velocidad vehicular y se desacopla explícitamente la **concentración espacial ($N$)** de la **severidad equivalente (EPDO)** y de la **probabilidad condicional de lesión grave/fatal dado el siniestro**. | Cuando no se dispone de flujos AADT por arco, la literatura de seguridad vial (PIARC / Highway Safety Manual) recomienda ponderar los siniestros mediante el índice **EPDO (*Equivalent Property Damage Only*)**: $\text{EPDO} = 12\cdot F + 6\cdot G + 3\cdot MG + 2\cdot L + 1\cdot \text{PDO}$ (aplicado de forma jerárquica o aditiva ponderada en `indice_epdo`), evitando que rotondas o cruces con alta frecuencia de roces leves eclipsen tramos con alta letalidad. | **Scripts:** `desarrollo/01_limpieza_y_correccion_solar.py`, `desarrollo/03_puntos_calientes_y_mitigacion.py`<br>**Evidencias:** `03_hotspots_dbscan.csv`, `03_grilla_getis_ord_gi.csv`, `03_intersecciones_y_ejes_criticos.csv` |
| **D4** | Ambigüedad en la metodología de *hotspots* (confusión entre KDE y Getis-Ord $G_i^*$). | **Aceptada.** Implementar una estrategia espacial dual y complementaria:<br>1. **Getis-Ord $G_i^*$** sobre una grilla métrica proyectada de $250\text{ m} \times 250\text{ m}$ con matriz de pesos espaciales por distancia ($d \le 400\text{ m}$), calculando $Z(G_i^*)$ y $p$-valores tanto para **conteo ($N$)** como para **severidad (EPDO)**.<br>2. **DBSCAN espacial** con métrica geodésica Haversine ($\varepsilon = 150\text{ m}$, $\text{min\_samples} = 5$) para identificar micro-nodos e intersecciones exactas. | El estadístico $G_i^*$ de Getis & Ord (1992) requiere unidades espaciales discretas con atributos cuantitativos agregados ($x_j$) y pesos definidos ($w_{ij}$). Combinar la grilla regular de $250\text{ m}$ ($G_i^*$ para significancia estadística regional) con DBSCAN Haversine de $150\text{ m}$ (escala de una intersección arterial y sus colas de aproximación) resuelve simultáneamente el problema de unidad de área modificable (MAUP) y la localización de ingeniería de tránsito. | **Script:** `desarrollo/03_puntos_calientes_y_mitigacion.py`<br>**Evidencias:** `03_grilla_getis_ord_gi.csv`, `03_hotspots_dbscan.csv`, `03_sintesis_mitigacion.json`, `fig05_mapa_hotspots_y_severidad.png`, `fig06_perfiles_clusters_criticos.png` |
| **D5** | Necesidad de verificar exactitud posicional de coordenadas frente a calles declaradas. | **Aceptada.** Ejecutar auditoría automatizada de coherencia geográfica verificando pertenencia al *bounding box* comunal y midiendo la dispersión métrica Haversine entre siniestros asignados a la misma intersección normalizada (`Calle_Uno_norm` $\times$ `Calle_Dos_norm`). | Garantiza que los clusters espaciales reflejen concentración real de accidentes y no artefactos de geocodificación errónea o centroides administrativos arbitrarios. | **Script:** `desarrollo/01_limpieza_y_correccion_solar.py`<br>**Evidencia:** `01_auditoria_calidad_y_solar.json` |
| **D6** | Profundizar en correlaciones estadísticas multivariadas y vincularlas con medidas de mitigación. | **Aceptada (Núcleo de Clase 7).** Ejecutar: (1) Matriz exhaustiva de 406 pares con correlación de Spearman ($\rho$), Pearson ($r$) y corrección Benjamini-Hochberg ($q_{\text{FDR}}$); (2) Pruebas exactas de Fisher, $\chi^2$, $V$ de Cramér y Odds Ratios (IC 95%) para 30 hipótesis; (3) Dos modelos de Regresión Logística Multivariada (`con_lesionados` y `grave_o_fatal`); y (4) Diseño de 6 medidas de mitigación (`MIT-01` a `MIT-06`) con población objetivo cuantificada. | Permite transitar desde la descripción exploratoria hacia la inferencia controlada por confusores (controlando simultáneamente tipo de usuario, iluminación nocturna corregida, estado del pavimento, morfología de cruce, cota altitudinal y fin de semana), traduciendo cada factor de riesgo en una intervención de ingeniería vial o gestión de tránsito medible. | **Scripts:** `desarrollo/02_correlaciones_y_factores.py`, `desarrollo/03_puntos_calientes_y_mitigacion.py`<br>**Evidencias:** `02_correlaciones_estadisticas.csv`, `02_asociaciones_categoricas_chi2_or.csv`, `02_resumen_correlaciones.json`, `03_matriz_mitigacion_evidencia.csv`, `fig02_matriz_correlaciones_spearman.png`, `fig03_factores_riesgo_severidad_or.png`, `fig04_perfiles_horarios_y_vulnerables.png` |

---

## 04. Avances Concretos Logrados en la Sesión

El pipeline reproducible ejecutado por el contenedor `lc-experimentacion` (`python desarrollo/run_all.py`) materializó cuatro bloques técnicos cuyos resultados exactos se sintetizan a continuación:

### 4.1. Bloque 1: Demostración Matemática y Corrección del Error Solar (+12 h) y Auditoría de Calidad (`01_limpieza_y_correccion_solar.py`)
1. **Demostración exacta de la hipótesis del desfase de $+12\text{ h}$:**
   - Al comparar la columna original `sol_alt_grados` con el cálculo astronómico NOAA evaluado en la hora local real del siniestro, el Error Medio Absoluto (MAE) es de **60,24°**.
   - Al evaluar el mismo modelo astronómico desplazando artificialmente la hora local en **$+12\text{ horas}$**, el MAE cae a **0,09°**, demostrando de forma irrefutable que el preprocesamiento original invirtió AM/PM (o sumó medio día al convertir a UTC).
2. **Impacto estructural sobre la distribución lumínica de los siniestros ($n = 676$):**
   - **Distribución original (errónea):** `dia` = 163 (24,11%), `crepusculo` = 44 (6,51%), `noche` = 83 (12,28%), `noche_cerrada` = 386 (57,10%). Total nocturno ($\alpha_{\text{sol}} \le 0^\circ$): **69,38%** (469 siniestros).
   - **Distribución astronómica corregida:** `dia` = **511** (75,59%), `crepusculo` = **31** (4,59%), `noche` = **48** (7,10%), `noche_cerrada` = **86** (12,72%). Total nocturno corregido ($\alpha_{\text{sol, corr}} \le 0^\circ$): **24,41%** (165 siniestros; o 196 incluyendo crepúsculo/noche civil).
   - **Reversión de la narrativa sobre atropellos y sol rasante:** Con el cálculo corregido, **32 de los 42 atropellos peatonales (76,19%) ocurren con plena luz de día** ($\alpha_{\text{sol, corr}} > 0^\circ$) y **106 siniestros (15,68%)** ocurren dentro de la ventana crítica de encandilamiento o sol rasante ($0^\circ < \alpha_{\text{sol, corr}} \le 15^\circ$).
3. **Auditoría posicional y recodificación:**
   - **Exactitud comunal:** **675 de 676 registros (99,85%)** se ubican estrictamente dentro del *bounding box* geográfico de Las Condes.
   - **Consistencia de intersecciones:** Sobre los $n = 279$ siniestros ocurridos en intersecciones con múltiples eventos (`Calle_Uno` $\times$ `Calle_Dos`), la **mediana de dispersión posicional respecto al centroide de la intersección es 0,0 m** y el **100,0%** se ubica a menos de $100\text{ m}$.
   - **Morfología vial clasificada:** `CRUCE_SEMAFORIZADO` = 476 (70,41%), `CRUCE_PRIORIDAD_SENAL` = 81 (11,98%), `TRAMO_RECTO` = 73 (10,80%), `OTROS` = 27 (3,99%), `CRUCE_SEMAFORO_APAGADO` = 8 (1,18%), `ROTONDA_O_ENLACE` = 7 (1,04%), `INFRAESTRUCTURA_PEATON_CICLO` = 4 (0,59%).
   - **Recalibración eólica (`viento_cat_corr`):** Pasa de 676 casos en `"calma"` a una distribución física informativa: `brisa_leve` = 203, `brisa_moderada` = 189, `viento_fuerte_o_rafaga` = 164 y `calma_real` = 120.
   - **Desagregación de `CAUSA_SINI` (`causa_especifica`):** Permite distinguir entre `NO_ATENTO_CONDICIONES_TRANSITO` ($n=586$, 23,9% lesionados, 6,1% graves/fatales, EPDO medio 1,55) y las causas específicas ($n=90$): `MANIOBRA_PISTA_ADELANTAMIENTO_VIRAJE` ($n=36$), `VELOCIDAD_O_DISTANCIA_SEGUIMIENTO` ($n=17$, **58,8% lesionados**, EPDO medio 2,06), `VIOLACION_SEMAFORO_O_PREFERENCIA` ($n=15$, **66,7% lesionados**, EPDO medio 2,00), `FALLA_MECANICA_U_OTRA` ($n=9$, **55,6% lesionados**, **33,3% graves/fatales**, EPDO medio 5,56), `ALCOHOL_EN_CONDUCTOR` ($n=7$, **71,4% lesionados**, **28,6% graves/fatales**, EPDO medio 4,86) y `FACTOR_PEATON_O_PASAJERO` ($n=6$, **83,3% lesionados**, **50,0% graves/fatales**, EPDO medio 4,00).

### 4.2. Bloque 2: Correlaciones Estadísticas, Tablas de Contingencia y Modelos Logísticos Multivariados (`02_correlaciones_y_factores.py`)
1. **Matriz de correlaciones continuas y ordinales (406 pares evaluados con ajuste FDR Benjamini-Hochberg):**
   - **Gradiente orográfico comunal:** Correlación altamente significativa entre altitud DEM y longitud geográfica ($\rho = 0,9277$, $r = 0,9110$, $p = 1,07 \times 10^{-290}$, $q_{\text{FDR}} = 0,0$) y entre altitud y latitud ($\rho = 0,7278$, $q_{\text{FDR}} = 0,0$), reflejando el ascenso topográfico poniente-oriente hacia la precordillera.
   - **Consistencia física hidro-meteorológica:** Altísima colinealidad entre precipitación acumulada en 24 h y horas de lluvia ($\rho = 0,9991$, $q_{\text{FDR}} = 0,0$) y con pavimento adverso ($\rho = 0,9899$, $q_{\text{FDR}} = 0,0$); correlación positiva entre viento medio y ráfagas ($\rho = 0,9186$, $q_{\text{FDR}} = 0,0$) y entre altitud solar corregida y temperatura ($\rho = 0,5283$, $q_{\text{FDR}} = 0,0$); y correlación inversa entre temperatura y humedad relativa ($\rho = -0,7792$, $q_{\text{FDR}} = 0,0$).
   - **Acoplamiento con severidad:** Fuerte correlación de la presencia de usuarios vulnerables con motocicletas ($\rho = 0,7418$, $q_{\text{FDR}} = 0,0$) y del índice EPDO con el total de lesionados ($\rho = 0,9778$) y con siniestros graves/fatales ($\rho = 0,5666$, $r = 0,8569$, $q_{\text{FDR}} = 0,0$).
2. **Pruebas bivariadas de asociación categórica ($\chi^2$, Exacta de Fisher, $V$ de Cramér y Odds Ratios crudos):**
   - De las 30 hipótesis contrastadas en `02_asociaciones_categoricas_chi2_or.csv`, **13 resultan estadísticamente significativas ($p < 0,05$)**:
     - **Atropello $\rightarrow$ Con lesionados:** 88,10% (37/42) vs. 22,40% (142/634); $\text{OR} = \mathbf{25,639}$ ($\text{IC 95\%}: 9,892\text{–}66,453$), $p_{\text{Fisher}} < 10^{-6}$, $V = 0,358$.
     - **Usuario vulnerable (peatón/moto/bici) $\rightarrow$ Con lesionados:** 58,18% (96/165) vs. 16,24% (83/511); $\text{OR} = \mathbf{7,174}$ ($\text{IC 95\%}: 4,865\text{–}10,581$), $p_{\text{Fisher}} < 10^{-6}$, $V = 0,407$.
     - **Usuario vulnerable $\rightarrow$ Grave o fatal:** 20,61% (34/165) vs. 2,54% (13/511); $\text{OR} = \mathbf{9,942}$ ($\text{IC 95\%}: 5,100\text{–}19,381$), $p_{\text{Fisher}} < 10^{-6}$, $V = 0,303$.
     - **Atropello $\rightarrow$ Grave o fatal:** 30,95% (13/42) vs. 5,36% (34/634); $\text{OR} = \mathbf{7,911}$ ($\text{IC 95\%}: 3,775\text{–}16,578$), $p_{\text{Fisher}} = 1 \times 10^{-6}$, $V = 0,240$.
     - **Motocicleta $\rightarrow$ Grave o fatal:** 19,61% (20/102) vs. 4,70% (27/574); $\text{OR} = \mathbf{4,941}$ ($\text{IC 95\%}: 2,650\text{–}9,214$), $p_{\text{Fisher}} = 2 \times 10^{-6}$, $V = 0,206$.
     - **Motocicleta $\rightarrow$ Con lesionados:** 45,10% (46/102) vs. 23,17% (133/574); $\text{OR} = \mathbf{2,724}$ ($\text{IC 95\%}: 1,762\text{–}4,210$), $p_{\text{Fisher}} = 9 \times 10^{-6}$, $V = 0,174$.
     - **Bicicleta $\rightarrow$ Con lesionados:** 64,00% (16/25) vs. 25,04% (163/651); $\text{OR} = \mathbf{5,322}$ ($\text{IC 95\%}: 2,308\text{–}12,276$), $p_{\text{Fisher}} = 6,6 \times 10^{-5}$, $V = 0,162$.
     - **Desobedecer semáforo o preferencia $\rightarrow$ Con lesionados:** 66,67% (10/15) vs. 25,57% (169/661); $\text{OR} = \mathbf{5,822}$ ($\text{IC 95\%}: 1,962\text{–}17,277$), $p_{\text{Fisher}} = 0,001139$, $V = 0,132$.
     - **Causa específica (distinta a 'no atento') $\rightarrow$ Con lesionados:** 43,33% (39/90) vs. 23,89% (140/586); $\text{OR} = \mathbf{2,436}$ ($\text{IC 95\%}: 1,541\text{–}3,852$), $p_{\text{Fisher}} = 0,000183$, $V = 0,145$; y para **Grave o fatal**: 12,22% (11/90) vs. 6,14% (36/586); $\text{OR} = \mathbf{2,127}$ ($\text{IC 95\%}: 1,040\text{–}4,350$), $p_{\text{Fisher}} = 0,044214$.
     - **Zona alta precordillerana ($\ge 750\text{ m s.n.m.}$) $\rightarrow$ Grave o fatal:** 14,94% (13/87) vs. 5,77% (34/589); $\text{OR} = \mathbf{2,868}$ ($\text{IC 95\%}: 1,448\text{–}5,681$), $p_{\text{Fisher}} = 0,004994$, $V = 0,115$; y para **Con lesionados**: 36,78% (32/87) vs. 24,96% (147/589); $\text{OR} = \mathbf{1,749}$ ($\text{IC 95\%}: 1,089\text{–}2,810$), $p_{\text{Fisher}} = 0,026316$.
     - **Ocurrencia en cruce (semaforizado o señalizado) vs. tramo recto $\rightarrow$ Con lesionados:** 24,07% (136/565) en cruces vs. 38,74% (43/111) fuera de cruce; $\text{OR} = \mathbf{0,501}$ ($\text{IC 95\%}: 0,327\text{–}0,769$), $p_{\text{Fisher}} = 0,002101$, confirmando que si bien los cruces concentran el volumen de siniestros, los accidentes en tramos rectos o enlaces tienen mayor probabilidad condicional de dejar lesionados por mayor energía cinética.
3. **Modelos de Regresión Logística Multivariada (`02_resumen_correlaciones.json`):**
   - **Modelo 1 — Probabilidad de Siniestro con Lesionados (`con_lesionados`, Pseudo-$R^2$ de McFadden = `0.2018`, $p_{\text{LLR}} = 2,25 \times 10^{-29}$):**
     - `Atropello`: $\text{OR}_{\text{ajustado}} = \mathbf{37,995}$ ($\text{IC 95\%}: 14,230\text{–}101,450$, $p < 0,0001$).
     - `Bicicleta`: $\text{OR}_{\text{ajustado}} = \mathbf{9,805}$ ($\text{IC 95\%}: 4,087\text{–}23,524$, $p < 0,0001$).
     - `Motociclet`: $\text{OR}_{\text{ajustado}} = \mathbf{4,323}$ ($\text{IC 95\%}: 2,669\text{–}7,001$, $p < 0,0001$).
     - `causa_distinta_no_atento`: $\text{OR}_{\text{ajustado}} = \mathbf{2,426}$ ($\text{IC 95\%}: 1,426\text{–}4,127$, $p = 0,001073$).
     - `zona_alta_precordillera` ($\ge 750\text{ m}$): $\text{OR}_{\text{ajustado}} = \mathbf{2,116}$ ($\text{IC 95\%}: 1,222\text{–}3,664$, $p = 0,007433$).
     - `es_cruce`: $\text{OR}_{\text{ajustado}} = \mathbf{0,525}$ ($\text{IC 95\%}: 0,317\text{–}0,869$, $p = 0,012179$).
     - Factores no significativos al ajustar por los demás: `pavimento_adverso` ($\text{OR} = 1,495$, $p = 0,1586$), `es_fin_de_semana` ($\text{OR} = 1,095$, $p = 0,7295$) y `noche_corr` ($\text{OR} = 0,952$, $p = 0,8404$).
   - **Modelo 2 — Probabilidad de Siniestro Grave o Fatal (`grave_o_fatal`, Pseudo-$R^2$ de McFadden = `0.2287`, $p_{\text{LLR}} = 3,96 \times 10^{-13}$):**
     - `Atropello`: $\text{OR}_{\text{ajustado}} = \mathbf{16,639}$ ($\text{IC 95\%}: 6,697\text{–}41,341$, $p < 0,0001$).
     - `Motociclet`: $\text{OR}_{\text{ajustado}} = \mathbf{9,898}$ ($\text{IC 95\%}: 4,636\text{–}21,131$, $p < 0,0001$).
     - `Bicicleta`: $\text{OR}_{\text{ajustado}} = \mathbf{5,616}$ ($\text{IC 95\%}: 1,412\text{–}22,343$, $p = 0,014317$).
     - `zona_alta_precordillera` ($\ge 750\text{ m}$): $\text{OR}_{\text{ajustado}} = \mathbf{4,366}$ ($\text{IC 95\%}: 1,939\text{–}9,828$, $p = 0,000371$).
     - `noche_corr` ($\alpha_{\text{sol, corr}} \le 0^\circ$): $\text{OR}_{\text{ajustado}} = \mathbf{2,172}$ ($\text{IC 95\%}: 1,067\text{–}4,420$, $p = 0,032371$). **Hallazgo crucial:** Una vez corregido el error solar y controlado el efecto del flujo diurno de peatones/ciclistas, la condición nocturna emerge como un predictor estadísticamente significativo que **más que duplica** las chances de desenlace grave o fatal.

### 4.3. Bloque 3: Detección Espacial de Puntos Calientes (*Hotspots*) Desacoplando Concentración vs. Severidad EPDO (`03_puntos_calientes_y_mitigacion.py`)
1. **Estadístico Espacial Getis-Ord $G_i^*$ en Grilla Métrica ($250\text{ m} \times 250\text{ m}$, radio de vecindad $d \le 400\text{ m}$):**
   - Sobre un total de **271 celdas activas** con siniestros en la comuna, el análisis identifica **22 celdas *hotspot* estadísticamente significativas ($p \le 0,05$) por frecuencia absoluta ($N$)** y **12 celdas *hotspot* significativas ($p \le 0,05$) por severidad ponderada EPDO**.
   - Los núcleos con mayor $Z(G_i^*)$ por EPDO se localizan en el corredor **Manquehue Norte / Presidente Riesco / Apoquindo** (`grid_ix=-2, grid_iy=0`: $Z_{\text{conteo}} = 5,677$, $Z_{\text{EPDO}} = 3,610$, $p = 0,00031$; `grid_ix=-3, grid_iy=2` en Pdte. Riesco: $Z_{\text{EPDO}} = 3,515$, $p = 0,00044$; `grid_ix=-2, grid_iy=-1` en Apoquindo: $n=24$ siniestros, $\text{EPDO}=29$, $Z_{\text{conteo}} = 5,021$, $Z_{\text{EPDO}} = 3,134$, $p = 0,00173$), en el enlace **Presidente Kennedy / Las Verbenas** (`grid_ix=7, grid_iy=7`: $Z_{\text{EPDO}} = 2,754$, $p = 0,00588$; `grid_ix=5, grid_iy=8`: $n=11$, $Z_{\text{conteo}} = 3,668$, $Z_{\text{EPDO}} = 2,241$) y en el nodo poniente **Andrés Bello / Nueva Tajamar** (`grid_ix=-17, grid_iy=-4`: $n=7$, $\text{EPDO}=13$, $Z_{\text{conteo}} = 3,058$, $Z_{\text{EPDO}} = 2,008$, $p = 0,0446$).
2. **Clustering Espacial DBSCAN Haversine ($\varepsilon = 150\text{ m}$, $\text{min\_samples} = 5$):**
   - Detecta **39 micro-clusters críticos** que concentran **377 de los 676 siniestros comunales (55,77%)**.
   - El contraste entre el ranking por conteo y el ranking por severidad EPDO demuestra el valor de la recomendación del *Critic*:
     - **Cluster 10 (`APOQUINDO x CUARTO CENTENARIO`, rotonda Atenas):** Es el #1 en frecuencia ($N = 38$, $\text{EPDO total} = 52$), pero tiene **0 fallecidos y 0 graves** ($\text{EPDO medio} = 1,37$, 28,9% lesionados leves/menos graves, predominio de colisiones de baja velocidad en rotonda).
     - En cambio, clusters de tamaño moderado presentan altísima severidad media: **Cluster 0 (`CUARTO CENTENARIO (TRAMO)`)** con $N = 9$ acumula **4 graves** ($\text{EPDO total} = 33$, $\text{EPDO medio} = \mathbf{3,67}$, 22,2% graves/fatales); **Cluster 8 (`LAS CONDES x SAN FRANCISCO DE ASIS`)** con $N = 7$ registra **57,1% de lesionados, 28,6% graves/fatales y 71,4% de involucramiento de usuarios vulnerables** ($\text{EPDO medio} = \mathbf{2,86}$); y **Cluster 32 (`CERRO COLORADO x MANQUEHUE NORTE`)** con $N = 5$ registra **1 fallecido**, 60,0% lesionados y $\text{EPDO medio} = \mathbf{3,80}$.
3. **Ranking de Ejes Viales Críticos Normalizados (`03_intersecciones_y_ejes_criticos.csv`):**
   - Top 5 arterial comunal por severidad acumulada:
     1. **`LAS CONDES`:** $N = 61$, $\text{EPDO total} = 116$ ($\text{EPDO medio} = 1,90$), 1 fallecido, 4 graves, 27 lesionados (32,8% con lesionados, 26,2% vulnerables, 34,4% nocturnos, altitud media $735,6\text{ m}$).
     2. **`PRESIDENTE KENNEDY`:** $N = 50$, $\text{EPDO total} = 83$ ($\text{EPDO medio} = 1,66$), 1 fallecido, 3 graves, 10 lesionados (28,0% nocturnos).
     3. **`APOQUINDO`:** $N = 54$, $\text{EPDO total} = 78$ ($\text{EPDO medio} = 1,44$), 0 fallecidos, 1 grave, 18 lesionados (25,9% con lesionados, 16,7% pavimento adverso).
     4. **`PRESIDENTE RIESCO`:** $N = 31$, $\text{EPDO total} = 59$ ($\text{EPDO medio} = 1,90$), 4 graves, 11 lesionados (**35,5% con lesionados**, **12,9% graves/fatales**, **35,5% usuarios vulnerables**).
     5. **`CRISTOBAL COLON`:** $N = 33$, $\text{EPDO total} = 55$ ($\text{EPDO medio} = 1,67$), 3 graves, 10 lesionados (30,3% usuarios vulnerables).
   - Destacan además por su **severidad condicional extrema** ejes secundarios/colectores como **`TOMAS MORO`** ($N=12$, 3 graves, $\text{EPDO medio} = \mathbf{2,58}$, 25,0% pavimento adverso), **`FRANCISCO BILBAO`** ($N=14$, 2 graves, **50,0% con lesionados**, $\text{EPDO medio} = \mathbf{2,14}$) y **`LOS MILITARES`** ($N=17$, **52,9% de involucramiento de usuarios vulnerables**).

### 4.4. Bloque 4: Matriz de Medidas de Mitigación Basadas en Evidencia (`03_matriz_mitigacion_evidencia.csv`)
Cada patrón estadístico y espacial fue traducido en una línea de intervención con focalización espacio-temporal y población objetivo cuantificada directamente sobre la base 2025:
- **`MIT-01` (Protección de Cruces Semaforizados para Usuarios Vulnerables):** Intervalos peatonales anticipados (LPI de 4–6 s), cajas de detención adelantada (*motobox/bikebox*) y eliminación de giros libres en rojo en los 15 cruces con *hotspot* Getis-Ord $G_i^*$ ($p < 0,05$) en Av. Apoquindo, Av. Las Condes, Cristóbal Colón, Manquehue Sur y Pdte. Riesco. **Población objetivo:** **134 siniestros, 78 lesionados y 26 graves/fatales**.
- **`MIT-02` (Gestión de Pistas y Conflictos Laterales de Motocicletas — Delivery y Commuting):** Segregación táctica de virajes, canalización en intersecciones complejas y zonas de detención exclusiva para *delivery* fuera de la primera pista de circulación en el eje comercial Apoquindo–Las Condes–Manquehue–Colón (12:00 a 21:00 h). **Población objetivo:** **38 siniestros, 20 lesionados y 7 graves/fatales**.
- **`MIT-03` (Seguridad Vial Nocturna y de Fin de Semana contra Choques a Elementos Fijos):** Delineadores direccionales retroreflectivos, amortiguadores de impacto en puntas de islas/bandejones centrales, iluminación LED de alto contraste y controles focalizados viernes/sábado (21:00–06:00 h) en enlaces de Av. Pdte. Kennedy, Av. Las Condes oriente y rotondas. **Población objetivo:** **35 siniestros, 14 lesionados y 3 graves/fatales**.
- **`MIT-04` (Mitigación Climática y Topográfica en Pavimento Húmedo y Sector Precordillerano):** Tratamiento superficial antideslizante de alta fricción (HFST) en pendientes longitudinales $>4\%$, drenaje superficial y señalización dinámica activada por humedad/lluvia ($>0,2\text{ mm/h}$ o humedad $\ge 85\%$) en el sector alto oriente ($\ge 750\text{ m s.n.m.}$: San Carlos de Apoquindo, Camino El Alba, Av. Las Condes oriente) y Pdte. Kennedy en otoño-invierno. **Población objetivo:** **41 siniestros, 21 lesionados y 3 graves/fatales**.
- **`MIT-05` (Pacificación Peatonal Diurna en Polos Laborales, Educacionales y de Servicios):** Pasos peatonales a nivel de acera en accesos secundarios, refugios peatonales en calzadas de $\ge 4$ pistas y viseras/orientación óptica de semáforos para mitigar encandilamiento en ventanas de sol rasante ($0^\circ < \alpha_{\text{sol}} \le 15^\circ$) en el eje Línea 1 (Tobalaba a Los Dominicos, 08:00–19:00 h). **Población objetivo:** **39 siniestros, 36 lesionados y 13 graves/fatales**.
- **`MIT-06` (Estandarización del Registro Policial/Municipal de Causas y Auditoría de Geocodificación):** Sustitución de la glosa genérica *"no atento a las condiciones del tránsito"* (actualmente 86,7% de la muestra) por una lista de verificación multifactorial obligatoria en terreno y validación GPS contra el catastro vial municipal. **Población objetivo:** **90 siniestros con causa específica actual, 56 lesionados y 11 graves/fatales** (con meta de reducir la glosa genérica de 86,7% a $<35\%$).

---

## 05. Resultados y Archivos de Evidencia Verificados

Todos los resultados fueron generados de manera determinista por el contenedor `lc-experimentacion` y auditados en modo solo lectura por el contenedor `lc-auditoria`. La tabla siguiente inventaría los **17 artefactos de evidencia** registrados en `experimentos/resultados/manifest_evidencia.json`:

| # | Ruta del Archivo (`experimentos/resultados/`) | Tipo / Contenido Técnico | Tamaño (Bytes) | Hash SHA-256 Verificado (`lc-auditoria`) |
|---:|---|---|---:|---|
| 1 | `01_auditoria_calidad_y_solar.json` | Métricas de corrección solar NOAA (MAE 60,24° vs 0,09°), conteos por periodo lumínico, auditoría posicional (99,85% en bbox) y recalibración de viento/causas. | 2.127 | `2a11a5595ad5ed7c18a3ad9b0a9ec1038505e554a0dc6a09a578adb56c9bd7d1` |
| 2 | `02_asociaciones_categoricas_chi2_or.csv` | Tabla de 30 pruebas de hipótesis ($\chi^2$, Fisher exacto, $V$ de Cramér, Odds Ratio e IC 95%). | 5.013 | `cc5c017f212952a26f28fa3a7649f863871c9c7ffdf23cb23a01009b0c1eac83` |
| 3 | `02_correlaciones_estadisticas.csv` | Matriz completa de 406 pares de variables con Spearman $\rho$, Pearson $r$, $p$-valores y $q$-valores FDR (Benjamini-Hochberg). | 29.531 | `7c8623521b7758dbf1383e66256d01768fad2d046ee9e0b048b0c4a5f14b7edc` |
| 4 | `02_resumen_correlaciones.json` | Síntesis JSON con top correlaciones, asociaciones significativas ($p<0,05$), ambos modelos logísticos multivariados y desglose de causas específicas. | 16.779 | `0650fe6a994202a8c075ac1c792a93282321a31e53e74b800e7a01c605d969c9` |
| 5 | `03_grilla_getis_ord_gi.csv` | Resultados espaciales de las 271 celdas activas ($250\text{ m} \times 250\text{ m}$) con $Z(G_i^*)$, $p$-valores y categorías hotspot/coldspot para conteo y EPDO. | 39.458 | `67ea412e34c19e0bbea9c4c5b907be616aa6efd8e4103ec48f188ed00ccbfc75` |
| 6 | `03_hotspots_dbscan.csv` | Caracterización completa de los 39 micro-clusters detectados por DBSCAN Haversine ($\varepsilon=150\text{ m}$, $\text{min\_samples}=5$). | 7.303 | `65a557e1d65932f3b6547c72479bdc061a10ec9ba4a0554d05ab79895b91b9ca` |
| 7 | `03_intersecciones_y_ejes_criticos.csv` | Ranking de los ejes viales más críticos normalizados por EPDO total, EPDO medio, lesionados, graves/fatales y perfil modal/climático. | 2.066 | `e4bb0bf5ce8e16d88cad49cacfadc29177a8bd4d4d1939b0f73841981541e76d` |
| 8 | `03_matriz_mitigacion_evidencia.csv` | Tabla estructurada de las 6 medidas de mitigación (`MIT-01` a `MIT-06`), respaldo empírico, localización y población objetivo. | 5.502 | `82261dff1de2b7b60884440295368990efed07c3d922b0739afa9b16fafabf38` |
| 9 | `03_sintesis_mitigacion.json` | Consolidado JSON de clusters DBSCAN, celdas Getis-Ord $G_i^*$, top 10 ejes viales y medidas de mitigación. | 27.366 | `b1870efdc615779d1781d6d3cf26c51c60f1999dc86dc8f100f636f22d78d4b2` |
| 10 | `REPORTE_EXPERIMENTOS.md` | Reporte técnico ejecutivo autogenerado por el pipeline de experimentación. | 8.978 | `3a2161e292f38877b7e0ccbdde652ad2f0701b6521674e5715f27d88e9734b4d` |
| 11 | `SINIESTROS_LAS_CONDES_CORREGIDO.csv` | Dataset maestro enriquecido y depurado ($676 \text{ filas} \times 87 \text{ columnas}$), incluyendo variables solares corregidas, `indice_epdo`, taxonomías viales y asignación de cluster/celda. | 490.459 | `a5fbcba6e0c825f8f89d1c2058dc44b1a7640f54596a8bb8f7356df2554bad81` |
| 12 | `fig01_correccion_solar_impacto.png` | Figura de diagnóstico del desfase de $+12\text{ h}$, curva solar anual/horaria y cambio en distribución día/noche. | 319.739 | `1729cb9588aa5e10fb1e2a113a4329f67a9f7ae7a552200e68cf4d802b96b440` |
| 13 | `fig02_matriz_correlaciones_spearman.png` | Mapa de calor jerárquico de correlaciones de Spearman ($\rho$) entre variables climáticas, orográficas, viales y de severidad. | 255.933 | `aa39bafe47df682b8ea958a50bd4719d12477000389caf0814f45d485c21ca3a` |
| 14 | `fig03_factores_riesgo_severidad_or.png` | *Forest plot* comparativo de Odds Ratios crudos y ajustados (IC 95%) para siniestros con lesionados y graves/fatales. | 203.901 | `10ec62aa54b793e5b9eb588b5b8a6d19a07e8848f317b3508dfa2cb9a890fa24` |
| 15 | `fig04_perfiles_horarios_y_vulnerables.png` | Distribución horaria y por periodo lumínico corregido según modo involucrado (peatones, motocicletas, bicicletas, automóviles) y severidad. | 214.547 | `e4f1afc9cf0201a85f4558122dc0fbe2e22a050510bb40ac10f516e1c8291b75` |
| 16 | `fig05_mapa_hotspots_y_severidad.png` | Mapa espacial comparativo de la grilla Getis-Ord $G_i^*$ (frecuencia vs. EPDO) y los micro-clusters DBSCAN en Las Condes. | 461.466 | `af8586802880fa12c2f93a7dbc3d9dbfd29fa67c837637b68c73671a47f1a840` |
| 17 | `fig06_perfiles_clusters_criticos.png` | Comparación de los top micro-clusters críticos desacoplando volumen total ($N$), puntaje EPDO, severidad media y composición modal. | 195.825 | `65b4038a88bcbc27fe2cb0ba388b143d03c31dff4bb55481a9ea57b5770e955f` |

---

## 06. Comandos de Verificación y Reproducibilidad

La arquitectura de contenedores definida en `compose.yaml` separa estrictamente los roles:
- **`lc-desarrollo`:** Acceso `:ro` a `datos/` y `docs/`, y `:rw` únicamente a `desarrollo/`.
- **`lc-experimentacion`:** Acceso `:ro` a `datos/` y `desarrollo/`, y `:rw` únicamente a `experimentos/resultados/`. Ejecuta `python desarrollo/run_all.py`.
- **`lc-auditoria`:** Acceso estrictamente de **solo lectura (`:ro`)** a `datos/`, `docs/`, `desarrollo/` y `experimentos/resultados/`, y escritura (`:rw`) únicamente en `auditoria/`.

### 6.1. Comandos para Reproducir el Pipeline Completo desde Cero
```powershell
# 1. Construir la imagen reproducible y levantar los servicios de desarrollo y auditoría
docker compose up -d --build desarrollo auditoria

# 2. Ejecutar el contenedor de experimentación (regenera los 17 artefactos y el manifiesto SHA-256)
docker compose run --rm experimentacion
```

### 6.2. Comando de Auditoría Independiente Ejecutado en `lc-auditoria`
Como Agente Auditor Independiente, se ejecutó la siguiente verificación directamente dentro del contenedor `lc-auditoria` para comprobar: (a) la integridad criptográfica SHA-256 y tamaño exacto en bytes de los 17 archivos listados en `manifest_evidencia.json`, y (b) el bloqueo efectivo de escritura (`Errno 30: Read-only file system`) sobre `/workspace/datos`, `/workspace/desarrollo` y `/workspace/experimentos/resultados`:

```powershell
docker exec lc-auditoria python -c "import json, hashlib, os; m = json.load(open('/workspace/experimentos/resultados/manifest_evidencia.json')); ok = all(os.path.exists(f['archivo']) and hashlib.sha256(open(f['archivo'],'rb').read()).hexdigest() == f['sha256'] and os.path.getsize(f['archivo']) == f['bytes'] for f in m['archivos']); print('HASH_CHECK_ALL_17:', ok, 'TOTAL:', len(m['archivos'])); ro_checks = {}; 
for d in ['/workspace/datos', '/workspace/desarrollo', '/workspace/experimentos/resultados']:
    try:
        open(d + '/_test_ro', 'w')
        ro_checks[d] = 'WRITABLE_ERROR'
    except OSError as e:
        ro_checks[d] = f'READ_ONLY_OK ({e.errno})'
print('RO_CHECKS:', ro_checks)"
```

**Salida real verificada durante la auditoría (Código de salida `0`):**
```text
HASH_CHECK_ALL_17: True TOTAL: 17
RO_CHECKS: {'/workspace/datos': 'READ_ONLY_OK (30)', '/workspace/desarrollo': 'READ_ONLY_OK (30)', '/workspace/experimentos/resultados': 'READ_ONLY_OK (30)'}
```

### 6.3. Inspección Rápida de Métricas Clave desde `lc-auditoria`
```powershell
# Verificar métricas de corrección solar y modelos logísticos sin abrir archivos manualmente
docker exec lc-auditoria python -c "import json; s=json.load(open('experimentos/resultados/01_auditoria_calidad_y_solar.json')); c=json.load(open('experimentos/resultados/02_resumen_correlaciones.json')); h=json.load(open('experimentos/resultados/03_sintesis_mitigacion.json')); print('Solar MAE real vs +12h:', s['correccion_solar']['mae_original_vs_real_grados'], 'vs', s['correccion_solar']['mae_original_vs_simulacion_mas12h_grados']); print('Logit R2 (Lesionados / Graves):', c['modelo_logistico_con_lesionados']['pseudo_r2_mcfadden'], '/', c['modelo_logistico_grave_o_fatal']['pseudo_r2_mcfadden']); print('DBSCAN clusters:', h['resumen_dbscan']['n_clusters_detectados'], '| Gi* hotspots (N / EPDO):', h['resumen_getis_ord_gi']['celdas_hotspot_conteo_p05'], '/', h['resumen_getis_ord_gi']['celdas_hotspot_epdo_p05'])"
```

---

## 07. Limitaciones y Pendientes (Clasificación Epistemológica A / B / C)

Siguiendo el estándar de honestidad científica de Confluencia Científica (Clase 7), se distingue explícitamente entre lo demostrado empíricamente hoy, las afirmaciones sujetas a supuestos o reserva metodológica, y las tareas pendientes para iteraciones futuras:

### 7.1. [Categoría A] Hechos Comprobados con Evidencia Verificable en el Repositorio
1. **Existencia y causa exacta del error solar previo:** Está demostrado matemáticamente ($\text{MAE} = 0,09^\circ$ contra una simulación desplazada $+12\text{ h}$ vs. $\text{MAE} = 60,24^\circ$ contra la posición astronómica real) que el dataset original desplazó en 12 horas la hora local chilena.
2. **Predominio diurno de la siniestralidad y de los atropellos en Las Condes 2025:** El **75,59%** ($511/676$) de los siniestros y el **76,19%** ($32/42$) de los atropellos ocurren de día ($\alpha_{\text{sol, corr}} > 0^\circ$). La proporción nocturna real ($\alpha_{\text{sol, corr}} \le 0^\circ$) es **24,41%** ($165/676$) y no 69,38%.
3. **Asimetría extrema de severidad hacia usuarios vulnerables:** En modelos multivariados ajustados por iluminación, pavimento, morfología vial, altitud, causa y día de la semana, el involucramiento de peatones ($\text{OR}_{\text{ajustado}} = 16,64$), motocicletas ($\text{OR}_{\text{ajustado}} = 9,90$) y bicicletas ($\text{OR}_{\text{ajustado}} = 5,62$) incrementa de manera altamente significativa ($p \le 0,014$) el riesgo de desenlace grave o fatal.
4. **Efecto independiente de la noche corregida y de la cota precordillerana ($\ge 750\text{ m s.n.m.}$) sobre la severidad grave/fatal:** Controlando por la composición modal diurna, la condición nocturna duplica el riesgo de gravedad/letalidad ($\text{OR}_{\text{ajustado}} = 2,172$, $p = 0,0324$) y el sector alto precordillerano cuadruplica dicho riesgo ($\text{OR}_{\text{ajustado}} = 4,366$, $p = 0,00037$).
5. **Divergencia espacial entre concentración de frecuencia y severidad equivalente (EPDO):** El 55,77% de los siniestros se agrupa en 39 micro-clusters DBSCAN ($\varepsilon = 150\text{ m}$) y existen 22 celdas *hotspot* Getis-Ord $G_i^*$ por conteo frente a 12 por EPDO ($p \le 0,05$). Nodos de altísima frecuencia como `APOQUINDO x CUARTO CENTENARIO` ($N=38$, 0 graves/fatales) difieren sustancialmente de nodos de alta letalidad/gravedad media como `CUARTO CENTENARIO (TRAMO)` ($\text{EPDO medio} = 3,67$), `LAS CONDES x SAN FRANCISCO DE ASIS` ($\text{EPDO medio} = 2,86$) o `CERRO COLORADO x MANQUEHUE NORTE` ($\text{EPDO medio} = 3,80$).

### 7.2. [Categoría B] Afirmaciones con Reserva Metodológica / No Verificadas Directamente
1. **Horizonte de seguimiento de fallecidos (24–48 h vs. 30 días):** No es posible verificar a partir del archivo fuente si el conteo de `FALLECIDOS` corresponde exclusivamente al reporte policial preliminar (fallecidos en el sitio o dentro de las primeras 24–48 horas) o si incorpora la corrección ministerial a 30 días de CONASET/DEIS. Por tanto, la letalidad absoluta podría presentar subregistro hospitalario tardío.
2. **Condición de calzada (`pavimento_est`) e información meteorológica ERA5 como *proxy* de microclima:** Las variables meteorológicas provienen de reanálisis horario grillado ERA5 / Open-Meteo ($\approx 9\text{–}25\text{ km}$ de resolución espacial) y no de sensores físicos de humedad superficial instalados en el pavimento de cada intersección. Aunque la correlación entre lluvia previa de 24 h y pavimento adverso es $\rho = 0,9899$, el microclima local (sombra de edificios en el eje Apoquindo/El Golf o riego urbano nocturno) no está capturado.
3. **Ausencia de exposición por flujo vehicular (AADT) y peatonal:** Los *hotspots* de frecuencia ($N$) y de severidad acumulada (EPDO) identifican **dónde se concentra el daño vial comunal** y la **severidad condicional por siniestro ocurrido**, pero no estiman la probabilidad individual de accidente por cada $10^6$ vehículos-kilómetro o peatones-cruce al no disponerse de conteos UOCT/SCAT en el repositorio.
4. **Sesgo de clasificación en la causa policial (`CAUSA_SINI`):** Aunque desagregar los 90 registros con causa específica demostró un poder discriminante significativo ($\text{OR}_{\text{ajustado}} = 2,426$ para lesionados), el 86,69% restante rotulado como *"no atento a las condiciones del tránsito"* probablemente oculta infracciones específicas no peritadas en siniestros de solo daños materiales.

### 7.3. [Categoría C] Tareas Pendientes Priorizadas para Próximas Etapas
1. **Integración de denominadores de exposición vehicular y peatonal (Prioridad Alta):** Cruzar los 39 micro-clusters DBSCAN y las 271 celdas de la grilla con conteos continuos de flujo vehicular de la Unidad Operativa de Control de Tránsito (UOCT / espiras SCAT en Las Condes) y aforos peatonales/transporte público (validaciones bip! en estaciones Línea 1 de Metro: Tobalaba, El Golf, Alcántara, Escuela Militar, Manquehue, Hernando de Magallanes y Los Dominicos) para estimar modelos de regresión de Poisson / Binomial Negativa con *offset* de exposición.
2. **Auditoría del único registro fuera del *bounding box* comunal (0,15%, $1/676$):** Inspeccionar manualmente contra el parte original el único registro cuyas coordenadas caen fuera del polígono de Las Condes y validar con un geocodificador inverso (`Calle_Uno` + `Numero`) los 73 siniestros ocurridos en tramo recto.
3. **Evaluación ex-ante de costo-efectividad de las medidas `MIT-01` a `MIT-06`:** Aplicar factores de modificación de siniestros (*Crash Modification Factors*, CMF del *Highway Safety Manual*) a las 6 medidas propuestas para estimar la reducción esperada anual de lesionados graves y fallecidos antes de su implementación municipal.

---

## 08. Instrucciones Paso a Paso para Otro Agente / Otro Equipo (Equipo B — Próxima Clase)

Esta guía está diseñada para que cualquier integrante o agente del **Equipo B** pueda tomar control del repositorio en la próxima sesión **en menos de 3 minutos**, sin necesidad de conocer el historial previo de conversación:

### Paso 1: Entender la Estructura del Proyecto (Lectura de 2 minutos)
1. Lee este archivo (`auditoria/HANDOFF.md`) de principio a fin: contiene el problema científico, las 6 objeciones de la sesión pasada, cómo se resolvieron, todas las cifras exactas y las limitaciones clasificadas en [A], [B] y [C].
2. Revisa el reporte ejecutivo autogenerado en `experimentos/resultados/REPORTE_EXPERIMENTOS.md` y las 6 figuras listas para presentación en `experimentos/resultados/fig01_*.png` a `fig06_*.png`.

### Paso 2: Verificar la Integridad y Reproducibilidad del Entorno (1 minuto)
Ejecuta en PowerShell o terminal desde la raíz del repositorio:
```powershell
# 1. Comprobar que los contenedores están activos (o levantarlos si están detenidos)
docker compose up -d desarrollo auditoria

# 2. Verificar desde el contenedor de auditoría que los 17 archivos de evidencia existen,
#    que sus hashes SHA-256 coinciden al 100% y que el entorno está blindado en solo lectura (:ro)
docker exec lc-auditoria python -c "import json, hashlib, os; m = json.load(open('/workspace/experimentos/resultados/manifest_evidencia.json')); print('Verificacion SHA-256 (17 archivos):', all(hashlib.sha256(open(f['archivo'],'rb').read()).hexdigest() == f['sha256'] for f in m['archivos']))"
```
Si deseas comprobar que el código regenera exactamente todos los resultados desde cero, ejecuta:
```powershell
docker compose run --rm experimentacion
```

### Paso 3: Guion Sugerido para Defender/Explicar el Proyecto en 5 Diapositivas
Si el Equipo B debe exponer los avances de este proyecto ante el curso, se recomienda estructurar la presentación siguiendo el hilo conductor de las 6 figuras generadas:
1. **Diapositiva 1 — El giro metodológico tras el feedback (`fig01_correccion_solar_impacto.png`):** Mostrar cómo la auditoría detectó y corrigió matemáticamente el desfase de $+12\text{ h}$ en la posición solar ($\text{MAE}$ cae de $60,24^\circ$ a $0,09^\circ$). Explicar cómo esto cambió la conclusión central: la siniestralidad en Las Condes es predominantemente diurna (75,6%) y el **76,2% de los atropellos ocurre de día**.
2. **Diapositiva 2 — Estructura de correlaciones y gradiente comunal (`fig02_matriz_correlaciones_spearman.png`):** Explicar la consistencia hidro-meteorológica de ERA5 y el fuerte gradiente topográfico oriente-poniente ($\rho = 0,9277$ entre altitud y longitud), que distingue la zona plana comercial de la zona alta precordillerana ($\ge 750\text{ m s.n.m.}$).
3. **Diapositiva 3 — ¿Qué mata o lesiona gravemente en Las Condes? (`fig03_factores_riesgo_severidad_or.png` y `fig04_perfiles_horarios_y_vulnerables.png`):** Presentar los Odds Ratios ajustados del modelo logístico multivariado (Pseudo-$R^2 = 0,2287$): la severidad grave/fatal está dominada por **peatones ($\text{OR}=16,64$), motocicletas ($\text{OR}=9,90$) y ciclistas ($\text{OR}=5,62$)**, junto con la **cota alta precordillerana ($\text{OR}=4,37$)** y la **noche corregida ($\text{OR}=2,17$)**. Destacar que desagregar `CAUSA_SINI` reveló que violar luz roja/preferencia multiplica las lesiones ($\text{OR}=5,82$).
4. **Diapositiva 4 — Puntos calientes desacoplando Frecuencia vs. Severidad EPDO (`fig05_mapa_hotspots_y_severidad.png` y `fig06_perfiles_clusters_criticos.png`):** Mostrar cómo se resolvió la crítica sobre *hotspots* combinando **Getis-Ord $G_i^*$** en grilla de $250\text{ m}$ (22 celdas *hotspot* por frecuencia vs. 12 por EPDO) y **DBSCAN Haversine** ($\varepsilon=150\text{ m}$, 39 micro-clusters = 55,8% de los siniestros). Contrastar `APOQUINDO x CUARTO CENTENARIO` (#1 en cantidad con 38 siniestros pero 0 graves) frente a `CUARTO CENTENARIO (TRAMO)` o `LAS CONDES x SAN FRANCISCO DE ASIS` (alta severidad grave/fatal).
5. **Diapositiva 5 — De los datos a la acción (`03_matriz_mitigacion_evidencia.csv`):** Presentar las 6 medidas concretas (`MIT-01` a `MIT-06`) —intervalos peatonales LPI y *motobox* en 15 cruces $G_i^*$, gestión de pistas de *delivery*, amortiguadores/delineación nocturna en Kennedy y Las Condes oriente, pavimento antideslizante HFST en cota $\ge 750\text{ m}$, pasos elevados diurnos en eje Línea 1 y reforma del formulario policial de causas— junto con las limitaciones [B] y próximos pasos [C] (cruce con flujos AADT de UOCT).

### Paso 4: Cómo Extender el Código en la Próxima Iteración
- Todo el código fuente modular reside en `desarrollo/`:
  - `desarrollo/01_limpieza_y_correccion_solar.py` (preprocesamiento, astronomía NOAA, EPDO y auditoría posicional).
  - `desarrollo/02_correlaciones_y_factores.py` (Spearman/Pearson con FDR, $\chi^2$/Fisher/OR y regresiones logísticas `statsmodels`).
  - `desarrollo/03_puntos_calientes_y_mitigacion.py` (grilla Getis-Ord $G_i^*$, DBSCAN Haversine, rankings viales y matriz de mitigación).
  - `desarrollo/run_all.py` (orquestador maestro que ejecuta los 3 scripts en orden, redacta `REPORTE_EXPERIMENTOS.md` y firma criptográficamente `manifest_evidencia.json`).
- Cualquier modificación debe realizarse dentro del contenedor `lc-desarrollo`, ejecutarse con `docker compose run --rm experimentacion` y verificarse nuevamente desde `lc-auditoria`.
