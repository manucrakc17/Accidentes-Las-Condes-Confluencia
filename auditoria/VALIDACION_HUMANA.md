# Validación Humana del Equipo sobre la Experimentación y el Handoff

**Proyecto:** Siniestros de Tránsito en Las Condes 2025 — Clima Horario, Puntos Calientes y Medidas de Mitigación  
**Curso:** Confluencia Científica — Clase 7 (*De la retroalimentación al handoff*)  
**Fecha:** 3 de noviembre de 2026  

---

## 1. Lista de Cotejo de Validación del Equipo (Pauta Clase 7, Diapositiva 11)

| Pregunta de Validación | Estado | Verificación Empírica Realizada |
|---|---|---|
| **1. ¿Representa el trabajo real?** | **SÍ (Verificado)** | El documento `auditoria/HANDOFF.md` y el reporte `experimentos/resultados/REPORTE_EXPERIMENTOS.md` reflejan fielmente los 3 scripts desarrollados en `desarrollo/` y ejecutados dentro del contenedor `lc-experimentacion` (`las-condes-siniestros:clase7`) sobre los $n = 676$ registros reales de `datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx`. |
| **2. ¿Existen las evidencias?** | **SÍ (Verificado)** | Existen los 17 artefactos de salida en `experimentos/resultados/`: 1 dataset corregido (`SINIESTROS_LAS_CONDES_CORREGIDO.csv`), 4 tablas analíticas CSV (`02_correlaciones_estadisticas.csv`, `02_asociaciones_categoricas_chi2_or.csv`, `03_hotspots_dbscan.csv`, `03_grilla_getis_ord_gi.csv`, `03_intersecciones_y_ejes_criticos.csv`, `03_matriz_mitigacion_evidencia.csv`), 3 resúmenes JSON, 6 figuras PNG de alta resolución y el manifiesto criptográfico `manifest_evidencia.json`. |
| **3. ¿Se puede reproducir?** | **SÍ (Verificado)** | El archivo `compose.yaml` y el `Dockerfile` construyen la imagen `las-condes-siniestros:clase7` (Python 3.12-slim) y ejecutan `python desarrollo/run_all.py` de forma determinista con `docker compose up -d --build`, regenerando exactamente las mismas métricas y hashes SHA-256. |
| **4. ¿Reconoce las limitaciones?** | **SÍ (Verificado)** | Se mantiene una estricta higiene epistémica: (a) se explicita que sin flujo vehicular (AADT) por tramo se mide *concentración de ocurrencia* y *severidad equivalente acumulada/media (EPDO)*, no riesgo por vehículo-kilómetro; (b) se advierte que `pavimento` y `visib_estim_km` provienen del reanálisis horario ERA5 ($9\text{ km}$) y no de sensores en calzada; y (c) se distingue qué está comprobado, qué tiene reserva y qué queda pendiente. |

---

## 2. Contraste de Afirmaciones Clave vs. Archivos de Resultados

1. **Corrección del error de $+12\text{ h}$ en posición solar (`01_auditoria_calidad_y_solar.json`):**
   - Afirmación: El archivo original desplazó en $+12\text{ h}$ el cálculo solar.
   - Contraste: Verificado matemáticamente; el MAE contra la posición solar real es $60,24^\circ$, mientras que contra una simulación desplazada $+12\text{ h}$ es apenas $0,09^\circ$. La proporción de siniestros nocturnos baja de $69,38\%$ a $24,41\%$, y el $76,2\%$ ($32/42$) de los atropellos ocurre de día.
2. **Factores asociados a la severidad (`02_asociaciones_categoricas_chi2_or.csv` y `02_resumen_correlaciones.json`):**
   - Afirmación: Los usuarios vulnerables, las causas específicas de maniobra/semáforo, la noche corregida y la zona alta precordillerana ($\ge 750\text{ m}$) incrementan significativamente la gravedad.
   - Contraste: Verificado en el modelo logístico multivariado para siniestro grave/fatal ($\text{Pseudo-}R^2 = 0,2287, p < 0,0001$): Atropello ($\text{OR}_{\text{ajustado}} = 16,64$), Motocicleta ($\text{OR}_{\text{ajustado}} = 9,90$), Bicicleta ($\text{OR}_{\text{ajustado}} = 5,62$), Cota $\ge 750\text{ m}$ ($\text{OR}_{\text{ajustado}} = 4,37$) y Noche corregida ($\text{OR}_{\text{ajustado}} = 2,17$).
3. **Puntos calientes y medidas de mitigación (`03_hotspots_dbscan.csv`, `03_grilla_getis_ord_gi.csv`, `03_matriz_mitigacion_evidencia.csv`):**
   - Afirmación: La detección de *hotspots* separa frecuencia de severidad ponderada (EPDO) y fundamenta 6 medidas de mitigación (`MIT-01` a `MIT-06`).
   - Contraste: Verificado en las 12 celdas *hotspot* Getis-Ord $G_i^*$ de severidad EPDO ($p \le 0,05$), los 39 micro-clusters DBSCAN ($55,77\%$ de los siniestros en radios de $150\text{ m}$) y las poblaciones objetivo cuantificadas en `03_matriz_mitigacion_evidencia.csv`.
