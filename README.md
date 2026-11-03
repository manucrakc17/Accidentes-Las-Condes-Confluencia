# Siniestros de Tránsito en Las Condes 2025: Correlaciones, Puntos Calientes y Medidas de Mitigación

Repositorio oficial de trabajo para la **Clase 7 (De la retroalimentación al handoff: Avanzar con agentes de IA y dejar evidencia verificable)** — Confluencia Científica (03/11/2026).

---

## 1. Arquitectura de Contenedores y Estructura del Repositorio

Siguiendo el estándar de separación de espacios y permisos de la Clase 7, el repositorio se estructura en tres entornos desacoplados definidos en [`compose.yaml`](compose.yaml) y [`Dockerfile`](Dockerfile):

1. **`desarrollo` (`lc-desarrollo`):** Entorno de implementación con acceso de lectura a `datos/` y `docs/`, y lectura/escritura a `desarrollo/`.
2. **`experimentacion` (`lc-experimentacion`):** Ejecuta de forma determinista el pipeline estadístico y geoespacial (`python desarrollo/run_all.py`), con acceso de **solo lectura (`:ro`)** a `datos/` y `desarrollo/`, y escritura exclusiva en `experimentos/resultados/`.
3. **`auditoria` (`lc-auditoria`):** Entorno aislado para el agente auditor con acceso de **solo lectura (`:ro`)** a `datos/`, `docs/`, `desarrollo/` y `experimentos/resultados/`, y escritura restringida únicamente a `auditoria/` (sin montar credenciales, directorio personal ni `docker.sock`).

```text
Accidentes-Las-Condes-Confluencia/
├── README.md
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .gitignore
├── datos/
│   └── SINIESTROS_LAS_CONDES_CON_CLIMA.xlsx
├── docs/
│   └── RETROALIMENTACION.md
├── desarrollo/
│   ├── 01_limpieza_y_correccion_solar.py
│   ├── 02_correlaciones_y_factores.py
│   ├── 03_puntos_calientes_y_mitigacion.py
│   └── run_all.py
├── experimentos/
│   └── resultados/
│       ├── SINIESTROS_LAS_CONDES_CORREGIDO.csv
│       ├── 01_auditoria_calidad_y_solar.json
│       ├── 02_correlaciones_estadisticas.csv
│       ├── 02_asociaciones_categoricas_chi2_or.csv
│       ├── 02_resumen_correlaciones.json
│       ├── 03_hotspots_dbscan.csv
│       ├── 03_grilla_getis_ord_gi.csv
│       ├── 03_intersecciones_y_ejes_criticos.csv
│       ├── 03_matriz_mitigacion_evidencia.csv
│       ├── 03_sintesis_mitigacion.json
│       ├── REPORTE_EXPERIMENTOS.md
│       ├── manifest_evidencia.json
│       ├── fig01_correccion_solar_impacto.png
│       ├── fig02_matriz_correlaciones_spearman.png
│       ├── fig03_factores_riesgo_severidad_or.png
│       ├── fig04_perfiles_horarios_y_vulnerables.png
│       ├── fig05_mapa_hotspots_y_severidad.png
│       └── fig06_perfiles_clusters_criticos.png
└── auditoria/
    ├── HANDOFF.md
    └── VALIDACION_HUMANA.md
```

---

## 2. Comandos de Ejecución y Verificación Reproducible

### A. Ejecución mediante Docker Compose
```bash
docker --version
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs experimentacion
```

### B. Ejecución directa / local (Respaldo verificable)
```bash
pip install -r requirements.txt
python desarrollo/run_all.py
```

### C. Verificación de Integridad Criptográfica (SHA-256)
Todos los archivos generados en `experimentos/resultados/` quedan registrados con su hash SHA-256 y tamaño en `experimentos/resultados/manifest_evidencia.json`.
