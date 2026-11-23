# Handoff de la auditoría científica

El pipeline analiza la categoría `Urbano` de la capa georreferenciada de CONASET para Las Condes en 2025. Describe los siniestros registrados y la severidad dentro de ese universo. La [ficha de procedencia](../docs/fuente_y_alcance.md) deja constancia de los universos de 742, 711 y 676 siniestros y del contraste descriptivo con 2024. El [informe generado](../experimentos/resultados/REPORTE_EXPERIMENTOS.md) es la referencia para las cifras de esta versión.

## Cómo se genera la evidencia

| Etapa | Qué queda registrado |
|---|---|
| Limpieza y posición solar | Entradas validadas, zona `America/Santiago`, umbral común de 0°, personas y eventos por separado, coincidencia de proxies, discrepancias con el polígono CIREN y posibles duplicados. El CSV por siniestro queda en un directorio privado. |
| Asociaciones | Matriz de correlaciones, Fisher con p crudos y ajustes BH y Holm, regresiones logísticas y sensibilidades de hora cíclica y altitud continua. El modelo de lesionados usa la presencia de al menos una persona lesionada. El desenlace grave o fatal requiere al menos una persona grave o fallecida. |
| Concentración espacial | DBSCAN Haversine con vecindad principal de 150 m y sensibilidad de radio y límite. Gi* usa una grilla de 250 m en UTM 19S, centros geométricos y 19.999 permutaciones globales. Se calculan ajustes BH por indicador. Z positivo y q ≤0,05 en ambos métodos es el criterio exploratorio principal. |
| Medidas candidatas | Los filtros son ejecutables. La matriz distingue personas lesionadas, siniestros graves o fatales y solapamiento. La validación de una intervención requiere observación y evaluación local. |

## Cómo leer la evidencia

- La elevación solar al nivel del horizonte o inferior incluye el crepúsculo. La simulación de 12 horas reproduce la fase opuesta del mismo día civil. El script de enriquecimiento original permitiría determinar el mecanismo del desfase.
- Los OR son razones de odds de severidad condicional. Las comparaciones de ocurrencia en la red vial requieren aforos y observación de horas o tramos sin siniestros. Las causas probables registradas se interpretan como glosas de registro.
- El polígono de CIREN permite detectar discrepancias administrativas. Su versión histórica de 2025 queda por confirmar. Los grupos de cruces con una misma coordenada sirven para verificar consistencia interna. La exactitud de la ubicación requiere el catastro y el parte. Los posibles duplicados se conservan mientras se valida la clave del registro.
- El parámetro de DBSCAN es una distancia de vecindad. Un grupo puede contener varios cruces. La tabla registra cuántos siniestros corresponden al nodo más frecuente y muestra su diámetro. Un siniestro puede contar en dos ejes distintos si ambas calles están informadas. Los recuentos por eje sirven para examinar cada vía y su suma carece de interpretación comunal.
- Gi* compara celdas ocupadas bajo un nulo de intercambiabilidad de sus valores. El archivo público y la figura muestran celdas con cinco o más siniestros. El ajuste se calcula con todas las celdas ocupadas. Una priorización de ingeniería requiere un universo vial, validación temporal, diagnóstico en terreno y medidas de exposición cuando estén disponibles.
- El puntaje histórico crece con frecuencia y número de víctimas. La sensibilidad CONASET usa la consecuencia más grave por siniestro, más un punto por ocurrencia, sin sustituir el diagnóstico completo que exige el manual.

## Verificación y pendientes

Ejecuta `docker compose run --rm auditoria` tras una ejecución completa de experimentación. La auditoría verifica existencia, inventario, bytes y SHA‑256 de los archivos agregados. Los hashes acreditan integridad de los archivos. La comprobación científica de cobertura, sesgos y medidas requiere la evidencia descrita en la ficha de procedencia.

1. Conciliar los 31 registros entre el informe comunal y la capa y aclarar qué significa `Rutas` en el campo `Zonas_urb_`.
2. Recuperar las consultas y las reglas originales de enriquecimiento meteorológico y de altitud. Comparar valores y marcas de tiempo con las fuentes y conservar las versiones.
3. Resolver candidatos a duplicado y ubicaciones discrepantes mediante partes y catastro de 2025.
4. Definir una unidad vial estable y usar años adicionales y datos de exposición donde existan. Evaluar las medidas con un diseño antes-después que contemple una comparación apropiada.

[Manual CONASET de puntos negros](https://conaset.cl/wp-content/uploads/2022/05/Manual_Puntos-Negros-Actualizacion_2025.pdf)
