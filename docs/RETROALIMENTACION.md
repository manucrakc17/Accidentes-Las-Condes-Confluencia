# Retroalimentación Recibida y Decisiones del Equipo

**Proyecto:** Análisis de Siniestros de Tránsito, Clima Horario, Puntos Calientes y Medidas de Mitigación en Las Condes (2025)  
**Fecha de última presentación / auditoría previa:** 20 de octubre de 2026 (`confluencia-agents-demo/project/aaaasd.pdf`)  
**Fecha de sesión actual (Clase 7):** 3 de noviembre de 2026  

---

## 1. Contexto de la Retroalimentación Anterior

En la sesión anterior (20/10/2026) se presentó el cruce de la base de siniestros de Las Condes 2025 (`SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx`, $n = 676$ registros $\times$ 63 columnas) junto con la auditoría metodológica generada por un pipeline de agentes (`researcher` $\rightarrow$ `critic` $\rightarrow$ `writer` $\rightarrow$ `reviewer`).

Dicha revisión identificó **6 problemas metodológicos críticos del plan original** y **6 hallazgos empíricos sobre la calidad de los datos**:

### A. Hallazgos Críticos sobre Calidad de Datos (20/10/2026)
1. **Error sistemático de $+12\text{ h}$ en las variables solares (`sol_alt_grados`, `periodo_solar`, `noche`):** El cálculo previo desplazó en 12 horas la hora local chilena, clasificando como nocturnos el $69,4\%$ de los siniestros (cuando el valor astronómico real es $\approx 24,1\%$), invirtiendo artificialmente la narrativa de "siniestralidad nocturna" (p. ej., 30 de los 42 atropellos ocurren de día).
2. **Monolitismo del campo `CAUSA_NUEV`:** El $86,7\%$ ($586/676$) aparece agrupado bajo `"DISTRACCION DEL CONDUCTOR"`, ocultando la variabilidad del campo original `CAUSA_SINI` (que distingue imprudencia del peatón, no respetar derecho preferente de paso, virajes indebidos, conducción bajo influencia del alcohol, distancia no razonable, etc.).
3. **Variables climáticas saturadas o mal calibradas:**
   - `viento_cat` tiene el valor `"calma"` en el $100\%$ de los casos (umbral mal calibrado).
   - `clima_estado` tiene `"llenado"` en el $100\%$ de los casos (metadato operativo sin varianza).
   - `visib_estim_km` está saturado en $20\text{ km}$ en casi toda la muestra por ser un proxy paramétrico $(T - T_{\text{rocío}})$ y no visibilidad observada en estación.
4. **Inviabilidad del componente de velocidad vehicular:** La base no posee mediciones de velocidad por tramo ni se verificó una fuente abierta georreferenciada de velocidades en la comuna.

### B. Observaciones Metodológicas del *Critic* (20/10/2026)
5. **Ausencia de denominador de exposición (flujo vehicular / km-vía):** Un ranking por conteo absoluto mide *concentración de ocurrencia*, no *tasa de riesgo* por vehículo-kilómetro.
6. **Ambigüedad en la detección de *hotspots* (puntos calientes):** Se criticó la propuesta difusa de aplicar *Getis-Ord $G_i^*$* "sobre una superficie de densidad KDE". El método exige aplicarse sobre conteos agregados en unidades espaciales discretas (grilla o segmentos viales) con matriz de pesos espaciales definida, o bien complementar con clustering espacial basado en densidad métrica (DBSCAN con distancia Haversine) y ponderación por severidad.
7. **Exactitud posicional y subregistro diferencial:** Se advirtió verificar la coherencia entre las coordenadas (`Latitud`, `longitud`) y la dirección vial declarada (`Calle_Uno`, `Calle_Dos`, `Numero`, `UBICACION`), así como analizar la severidad desagregada (`FALLECIDOS`, `GRAVES`, `MENOS_GRAV`, `LEVES`) dado que el subregistro policial afecta principalmente a siniestros sin lesionados o leves (Elvik & Mysen, 1999).
8. **Falta de análisis inferencial multivariado y conexión con medidas de mitigación:** El análisis descriptivo univariado (pavimento seco vs. mojado) no tenía potencia por sí solo sin cruzar simultáneamente tipología de siniestro, usuarios vulnerables (motocicletas, peatones, ciclistas), iluminación corregida, morfología vial (cruce vs. tramo recto), altitud/gradiente comunal y causas específicas (`CAUSA_SINI`) para fundamentar medidas de mitigación concretas.

---

## 2. Matriz de Decisiones del Equipo (Del Feedback a la Acción)

Siguiendo la pauta de la Clase 7 (*"Del feedback a decisiones"*), el equipo definió las siguientes decisiones y evidencias verificables ejecutadas dentro del entorno contenerizado (`experimentacion`):

| # | Observación recibida | Decisión del equipo | Acción implementada en código (`desarrollo/`) | Evidencia verificable (`experimentos/resultados/`) |
|---|---|---|---|---|
| **O1** | Error de $+12\text{ h}$ en `sol_alt_grados`, `periodo_solar` y `noche` bloquea cualquier análisis horario/lumínico. | **Aceptada (Prioridad 1).** Recalcular astronómicamente la altitud solar para cada registro usando latitud, longitud, fecha y hora local de Santiago (con cambio de huso horario oficial Chile 2025 UTC-3/UTC-4) y auditar el error medio absoluto (MAE). | `desarrollo/01_limpieza_y_correccion_solar.py` | `SINIESTROS_LAS_CONDES_CORREGIDO.csv`, `01_auditoria_calidad_y_solar.json`, `fig01_correccion_solar_impacto.png` |
| **O2** | `CAUSA_NUEV` es monolítica ($86,7\%$ distracción) y `viento_cat` / `clima_estado` no discriminan. | **Aceptada.** Auditar y recategorizar `CAUSA_SINI` original en taxonomías operativas (imprudencia en cruce/señalización, distancia/alcance, peatón, alcohol, pérdida de control, atención general) y recalibrar `viento_cat` por cuartiles/escala Beaufort. Descartar `clima_estado` de los modelos. | `desarrollo/01_limpieza_y_correccion_solar.py` | `01_auditoria_calidad_y_solar.json`, `02_asociaciones_categoricas_chi2_or.csv` |
| **O3** | Inviabilidad de datos abiertos de velocidad vehicular y ausencia de flujo vehicular (exposición). | **Aceptada con reformulación de alcance.** Se descarta definitivamente el componente de velocidad vehicular. Para evitar confundir *concentración* con *riesgo*, se incorporan tres métricas complementarias por unidad espacial: (1) Frecuencia absoluta, (2) Índice de Severidad Equivalente (*EPDO*: Fallecido=12, Grave=6, Menos Grave=3, Leve=2, Daños=1), y (3) Tasa de severidad condicional (% lesionados y % graves/fatales por siniestro ocurrido). | `desarrollo/02_correlaciones_y_factores.py`, `desarrollo/03_puntos_calientes_y_mitigacion.py` | `03_hotspots_dbscan.csv`, `03_grilla_getis_ord_gi.csv`, `03_intersecciones_y_ejes_criticos.csv` |
| **O4** | Método de detección de *hotspots* ambiguo en la propuesta inicial (confusión entre KDE y Getis-Ord $G_i^*$). | **Aceptada.** Implementar dos métodos espaciales matemáticamente rigurosos y reproducibles: (1) **Getis-Ord $G_i^*$** sobre una grilla métrica proyectada de $250\text{ m} \times 250\text{ m}$ con vecindad tipo *Queen/distancia* ($d \le 400\text{ m}$) tanto para conteo como para severidad EPDO; y (2) **Clustering espacial DBSCAN** con métrica Haversine ($\varepsilon = 150\text{ m}$, $\text{min\_samples} = 5$) para identificar micro-zonas críticas e intersecciones exactas. | `desarrollo/03_puntos_calientes_y_mitigacion.py` | `03_hotspots_dbscan.csv`, `03_grilla_getis_ord_gi.csv`, `fig05_mapa_hotspots_y_severidad.png`, `fig06_perfiles_clusters_criticos.png` |
| **O5** | Falta verificar la coherencia posicional entre coordenadas y direcciones viales declaradas. | **Aceptada.** Ejecutar una auditoría automatizada de coherencia espacial de los 676 registros verificando límites comunales, dispersión transversal por calle (`Calle_Uno`) y consistencia de intersecciones (`Calle_Uno` $\times$ `Calle_Dos`). | `desarrollo/01_limpieza_y_correccion_solar.py` | `01_auditoria_calidad_y_solar.json` |
| **O6** | Necesidad de avanzar hacia **correlaciones entre variables** y **formulación de medidas de mitigación** respaldadas por datos. | **Aceptada (Objetivo central de Clase 7).** Ejecutar batería completa de correlaciones no paramétricas (Spearman $\rho$), pruebas de asociación ($\chi^2$, exacta de Fisher, $V$ de Cramér, Odds Ratios con IC 95%), modelos multivariados de severidad y matriz de medidas de mitigación vinculadas a cada patrón y punto caliente detectado. | `desarrollo/02_correlaciones_y_factores.py`, `desarrollo/03_puntos_calientes_y_mitigacion.py` | `02_correlaciones_estadisticas.csv`, `02_asociaciones_categoricas_chi2_or.csv`, `03_matriz_mitigacion_evidencia.csv`, `REPORTE_EXPERIMENTOS.md` |
