# Registro de verificación y revisión del equipo

Esta página acompaña la revisión técnica. La aprobación humana del estudio y de sus propuestas necesita revisión y firma del equipo.

| Comprobación | Evidencia para revisar |
|---|---|
| Cobertura, unidad de observación y procedencia | [Ficha de fuente y alcance](../docs/fuente_y_alcance.md). |
| Coherencia de cifras, intervalos y población objetivo | [Informe regenerado](../experimentos/resultados/REPORTE_EXPERIMENTOS.md) y [matriz de medidas](../experimentos/resultados/03_matriz_mitigacion_evidencia.csv). |
| Reejecución e integridad | El pipeline genera un manifiesto y se verifica con `python desarrollo/run_all.py --verificar`. Poseer los mismos archivos acredita integridad. |
| Precisión de puntos, aforos y efectividad de medidas | Pendiente de fuentes adicionales, comprobación de ubicación y revisión del equipo. |

La planilla enriquecida y el CSV individual quedan en rutas locales ignoradas por Git. El historial anterior puede contener versiones de esos datos y un informe con un caso individual. La conformidad de publicación y las condiciones de redistribución requieren confirmación con quienes administran los datos.
