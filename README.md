# Siniestros registrados en Las Condes en 2025

Estudio exploratorio de severidad, horario y concentración espacial en la categoría `Urbano` de la capa georreferenciada de CONASET. Este repositorio nació en la Clase 7 de Confluencia Científica. El [informe calculado](experimentos/resultados/REPORTE_EXPERIMENTOS.md) presenta resultados y medidas candidatas a evaluación. La [ficha de fuente y alcance](docs/fuente_y_alcance.md) documenta el subconjunto, los denominadores y las limitaciones.

## Reproducir en Docker

1. Coloca una **copia autorizada** de la planilla enriquecida de referencia en `datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx`. Su SHA‑256 se registra en el manifiesto. La geometría de CIREN se incluye en `datos/las_condes_ciren.geojson`.
2. Ejecuta desde la raíz del repositorio.

   ```bash
   mkdir -p experimentos/resultados
   mkdir -m 700 -p experimentos/privado
   chmod 600 datos/SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx
   export ANALISIS_UID="$(id -u)" ANALISIS_GID="$(id -g)"
   docker compose build experimentacion
   docker compose run --rm experimentacion
   docker compose run --rm auditoria
   ```

La construcción de la imagen descarga dependencias fijadas. En ejecución, los servicios operan sin red, con usuario sin privilegios, sin capacidades adicionales y con el sistema de archivos del contenedor en solo lectura. Experimentación monta el Excel y el código en solo lectura y escribe el CSV individual en `experimentos/privado/`. Auditoría verifica los resultados agregados mediante montajes de solo lectura y carece de acceso al Excel y al CSV individual.

**Si actualizas la versión anterior**, conserva una copia autorizada de la planilla **fuera del checkout antes de cambiar de rama**. Después de actualizar, cópiala a la ruta local indicada. Retira el CSV heredado del directorio público si conservas una copia no versionada allí. El verificador rechaza archivos inesperados. Las revisiones anteriores del historial de Git pueden seguir conteniendo la planilla, el CSV y un informe con un caso individual.

## Ejecución local

En Linux o macOS con Python 3.11 o 3.12, crea un entorno virtual y carga las dependencias fijadas.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONTZPATH='' MPLBACKEND=Agg python desarrollo/run_all.py
python desarrollo/run_all.py --verificar
MPLBACKEND=Agg python -m unittest discover -s tests -v
```

`experimentos/resultados/` contiene el informe, las tablas y figuras agregadas, y el manifiesto SHA‑256. La verificación falla ante un archivo faltante, inesperado o alterado. Los subdirectorios con prefijo `.ejecucion-` se reservan para archivos temporales. Al volver a ejecutar, el flujo retira los que quedaron por una interrupción. El manifiesto guarda versiones y hashes de los dos insumos. Las dependencias y la imagen están fijadas. La plataforma o el entorno gráfico pueden afectar el orden o la representación binaria de algunos resultados. El [handoff técnico](auditoria/HANDOFF.md) describe cómo interpretar y extender el análisis.
