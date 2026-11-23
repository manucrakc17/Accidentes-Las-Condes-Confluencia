# Fuentes, cobertura y límites del análisis

## Población analizada

La unidad de análisis es un siniestro registrado. El conjunto principal cubre 676 registros de Las Condes de 2025, de la categoría literal `Zonas_urb_ = Urbano` de la capa georreferenciada de CONASET. Las cifras comunales incluyen un universo más amplio. [Informe comunal Las Condes 2025](https://www.conaset.cl/wp-content/uploads/2026/10/Las-Condes.pdf) · [Capa Siniestros individuales 2025](https://mapas-conaset.opendata.arcgis.com/datasets/8098a36e7b1d496ea001f1d2271a22f3_0)

| Universo 2025 | Siniestros | Personas lesionadas | Personas fallecidas |
| --- | ---: | ---: | ---: |
| Estadística comunal de CONASET | 742 | 226 | 4 |
| Capa georreferenciada para Las Condes | 711 | 221 | 4 |
| Categoría `Urbano` en la capa y libro del proyecto | 676 | 212 | 4 |

Los 676 identificadores del libro coinciden con la capa. Después de armonizar nombres y formatos, se verificó la igualdad en 34 atributos, incluidos fecha, hora, coordenadas y severidad. Se usó `ID` para cruzar ambas fuentes. El identificador interno `FID` presenta diferencias. Para repetir la consulta usar `AÑO = 2025 AND COMUNA = 'Las Condes'`. Para el contraste previo cambiar el año a 2024. [Servicio de consulta de la capa](https://services3.arcgis.com/vaJl1B5HEzZj7154/arcgis/rest/services/Base_SINIESTROS_2020_2025/FeatureServer/0)

El SHA‑256 de la planilla cotejada es `649287b8b00292683c93e14932da0bacbaad5d68c516dd46bffa0765c744a7c6`. El manifiesto consigna el hash de la planilla usada en cada ejecución.

De los 711 registros, los 35 excluidos del libro llevan la categoría `Zonas_urb_ = Rutas` y todos figuran como urbanos en el campo distinto `ZONA`. En la muestra, ese segundo campo clasifica seis registros como rurales. Los 35 excluidos tienen el campo `Ruta` vacío y el informe comunal reporta cero siniestros en rutas. Conviene interpretar el filtro únicamente como una categoría de la capa hasta confirmar su definición con CONASET. La diferencia de 31 eventos y 5 personas lesionadas entre la capa y la estadística comunal queda sin conciliar. Antes de ampliar el análisis, solicitar a CONASET la base original, el diccionario de campos y los criterios de cobertura y geocodificación. [Ficha de la capa georreferenciada](https://www.arcgis.com/home/item.html?id=8098a36e7b1d496ea001f1d2271a22f3) · [Informe comunal Las Condes 2025](https://www.conaset.cl/wp-content/uploads/2026/10/Las-Condes.pdf)

## Severidad y contraste temporal

`con_lesionados` indica al menos una persona lesionada según `TOTAL_LESI`. `grave_o_fatal` indica al menos una persona en `GRAVES` o `FALLECIDOS`. `MENOS_GRAV` permanece como categoría separada. Las estadísticas CONASET usan fallecimientos hasta 48 horas desde 2019. El manual de puntos negros agrupa graves y menos graves para su protocolo, por lo que una comparación con ese manual debe armonizar la definición de severidad. [Definición estadística de CONASET](https://conaset.cl/programa/observatorio-datos-estadistica/biblioteca-observatorio/estadisticas-generales/) · [Manual de puntos negros de CONASET](https://conaset.cl/wp-content/uploads/2022/05/Manual_Puntos-Negros-Actualizacion_2025.pdf)

| Muestra | Grave o fatal con usuario vulnerable | Grave o fatal sin usuario vulnerable |
| --- | ---: | ---: |
| Capa 2024, categoría `Urbano` | 58 de 224 | 15 de 617 |
| Capa 2025, categoría `Urbano` | 34 de 165 | 13 de 511 |
| Capa 2025, todas las categorías | 35 de 171 | 13 de 540 |

El contraste usa indicadores de atropello, motocicleta o bicicleta. Las proporciones describen severidad entre los siniestros registrados en cada grupo. El contraste de 2024 comprueba la dirección de la asociación descriptiva en otro año. La validación de los modelos ajustados y la consistencia de medición entre años requieren datos comparables y un análisis específico. Para estimar ocurrencia o tasas por recorrido se necesitan aforos o vehículos-kilómetro y observaciones de tramos y horas con y sin siniestros.

## Ubicación, meteorología y medidas

El límite de comuna de CIREN corresponde al código 13114. Se consultó el 23 de noviembre de 2026. Queda pendiente corroborar su vigencia para 2025. El límite ayuda a detectar discrepancias geográficas. Se conserva la muestra de 676 registros para los resultados principales. Para verificar la posición del impacto, revisar la coordenada contra el parte y el catastro, con especial atención a posiciones repetidas y discrepancias con la comuna declarada, antes de excluir observaciones o priorizar sitios. [Capa de límites administrativos de CIREN](https://esri.ciren.cl/server/rest/services/LIMITES_ADMINISTRATIVOS/MapServer/3)

La hoja `Progreso` menciona Open-Meteo, ERA5/ECMWF e IFS de 9 km y Copernicus GLO-90. Falta conservar el producto meteorológico exacto, los parámetros de consulta y el procedimiento de emparejamiento entre la hora local chilena y la serie UTC. También quedan pendientes las reglas de precipitación acumulada, pavimento y visibilidad estimados. GLO-90 representa la superficie terrestre a resolución nominal de 90 m, con efectos de infraestructura y vegetación. Para evaluar pendiente longitudinal, fricción, iluminación o visibilidad se requieren mediciones locales. [API histórica de Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) · [Modelo de superficie Copernicus](https://documentation.dataspace.copernicus.eu/Data/Others/CCM.html)

La matriz de mitigación define seis poblaciones observables para orientar evaluaciones. Un caso puede entrar en varias medidas. Los conteos por persona y por siniestro tienen unidades distintas. Cada intervalo horario incluye el inicio y excluye el fin. Lunes a viernes se refiere al día calendario. La comprobación de un mecanismo vial, la línea base de exposición y una evaluación con sitios comparables son pasos previos para estimar el efecto de una intervención. [Manual de puntos negros de CONASET](https://conaset.cl/wp-content/uploads/2022/05/Manual_Puntos-Negros-Actualizacion_2025.pdf)

## Reproducción y acceso

La ejecución requiere una copia autorizada de `datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx` en la máquina de trabajo. El CSV por evento queda en `experimentos/privado/SINIESTROS_LAS_CONDES_CORREGIDO.csv`. Ambos se excluyen de Git. La combinación de hora, lugar y severidad permite vincular registros con otras fuentes. Las tablas espaciales públicas aplican un mínimo de cinco siniestros por unidad y omiten conteos separados de fallecimientos por eje o grupo. Los conteos sensibles dentro de unidades y los filtros con pocos casos también requieren una revisión antes de distribuir resultados. El historial de los commits públicos anteriores todavía puede contener los archivos originales.
