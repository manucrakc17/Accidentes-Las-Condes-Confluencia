# Siniestros registrados en Las Condes en 2025

Análisis exploratorio de **676 siniestros** etiquetados `Zonas_urb_ = Urbano` en la planilla local. [Cotejo de la planilla de referencia con CONASET, cobertura y definiciones](../../docs/fuente_y_alcance.md)

El conjunto registra **212 personas lesionadas** y **4 personas fallecidas**. Hay **179 siniestros con personas lesionadas**, **181 con lesión o muerte** y **47 con al menos una lesión grave o muerte**.

## Posición solar y clima

- Con el mismo umbral de elevación solar ≤0°, que incluye el crepúsculo, la proporción pasa de **75.89% (513/676)** a **24.41% (165/676)**. El indicador original por sí solo marcaba 69.38%.
- El error medio absoluto de la elevación original es **60.24°** respecto de la elevación corregida y **0.09°** respecto de la simulación desplazada 12 h en el reloj del mismo día. La simulación identifica la fase horaria opuesta. El mecanismo original requiere el proceso de enriquecimiento.
- **32 de 42 atropellos** tuvieron el sol sobre el horizonte. El indicador geométrico de sol bajo describe elevación solar. Para medir encandilamiento hacen falta orientación y condiciones observadas.
- El pavimento adverso estimado y el indicador de lluvia previa coinciden en **675/676 filas**. Faltan mediciones en calzada y exposición para evaluar la ocurrencia de siniestros según clima.

## Severidad dentro de los siniestros registrados

- **34/165 siniestros con usuarios vulnerables** tuvieron desenlace grave o fatal frente a **13/511** del resto.
- De 30 pruebas de Fisher, 30 fueron estimables. Hay 13 con p <0,05, 11 con ajuste Benjamini–Hochberg (BH) y 10 con ajuste Holm. Cada familia de pruebas se ajustó por separado.
- El modelo grave/fatal usa **47 eventos**, 676 registros y 9 predictores. Los OR describen odds ajustadas dentro de la muestra. El análisis carece de aforos y los coeficientes son exploratorios.

| Factor | OR ajustado (IC 95% nominal) | p | q BH | p Holm |
|---|---:|---:|---:|---:|
| Atropello | 16.6 (6.7–41.3) | 1.4e-09 | 1.26e-08 | 1.26e-08 |
| Motocicleta | 9.9 (4.64–21.1) | 3.14e-09 | 1.41e-08 | 2.51e-08 |
| Bicicleta | 5.62 (1.41–22.3) | 0.0143 | 0.0322 | 0.0859 |
| Causa específica registrada | 1.91 (0.846–4.33) | 0.119 | 0.179 | 0.477 |
| Elevación solar ≤0° | 2.17 (1.07–4.42) | 0.0324 | 0.0583 | 0.162 |
| Pavimento adverso estimado | 0.666 (0.242–1.83) | 0.431 | 0.498 | 1 |
| Ubicación clasificada como cruce | 0.76 (0.336–1.72) | 0.511 | 0.511 | 1 |
| Cota ≥750 m | 4.37 (1.94–9.83) | 0.000371 | 0.00111 | 0.0026 |
| Sábado o domingo | 1.39 (0.599–3.23) | 0.443 | 0.498 | 1 |

Al añadir hora cíclica, el OR de elevación solar ≤0° pasa a **2.59** (IC 0.795–8.45, p = 0.114). Con altitud continua, el OR por 50 m es **1.37** (IC 1.06–1.78). La pendiente, el tipo de vía y la velocidad requieren datos adicionales.

## Concentración espacial

- **27 puntos** quedan fuera del límite comunal de referencia de CIREN. 26 están a 50 m o menos. El máximo es 7842 m. En 99/99 intersecciones repetidas todas las filas comparten exactamente la coordenada. La exactitud vial requiere el catastro y los partes.
- DBSCAN a 150 m agrupa **377/676 siniestros en 39 grupos**. 11 grupos se extienden más de 300 m. El parámetro es distancia de vecindad y el rótulo es el nodo más frecuente dentro del grupo. Se publican 38 grupos con al menos 5 siniestros.
- Gi* usa 260 celdas ocupadas, centros geométricos y 19999 permutaciones. El criterio principal exige Z positivo y q BH ≤0,05 tanto con la aproximación analítica como con permutaciones. Se publican 41 celdas con al menos 5 siniestros.
- Los dos puntajes acumulados suman 1131 (ponderación histórica por persona) y 1264 (peor consecuencia por siniestro, más frecuencia). Comparten 9 grupos en sus diez primeros lugares.

| Atributo para Gi* | Nominal | BH analítico | BH con permutación | Ambos BH |
|---|---:|---:|---:|---:|
| Frecuencia | 20 | 9 | 0 | 0 |
| Puntaje histórico | 17 | 0 | 0 | 0 |
| Puntaje CONASET | 19 | 0 | 0 | 0 |

La comparación espacial es exploratoria y está condicionada a celdas con registros. La priorización requiere una red vial de referencia, validación temporal y comprobación en terreno.

## Medidas candidatas a evaluación

Los filtros generan 647 selecciones en 595 siniestros distintos. 43 entran en más de una medida. Los conteos describen el filtro aplicado. La efectividad local de cada medida requiere una evaluación.

| Código | Línea de acción | Siniestros | Personas lesionadas | Siniestros graves o fatales |
|---|---|---:|---:|---:|
| MIT-01 | Protección de cruces semaforizados | 15 | 13 | 3 |
| MIT-02 | Conflictos viales con motocicletas | 27 | 11 | 3 |
| MIT-03 | Choques de noche durante el fin de semana | 8 | 11 | 3 |
| MIT-04 | Pavimento adverso estimado en sectores altos | 4 | 4 | 1 |
| MIT-05 | Cruces peatonales en ejes con atropellos diurnos | 7 | 7 | 3 |
| MIT-06 | Calidad del registro de causas y ubicación | 586 | 156 | 36 |

[Filtros, evidencia y verificación propuesta](03_matriz_mitigacion_evidencia.csv)
