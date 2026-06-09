# BI - Análisis Aduanas DNIT Paraguay 2025

Proyecto de Business Intelligence sobre datos abiertos de la
Dirección Nacional de Ingresos Tributarios (DNIT) de Paraguay.
Implementa un pipeline ETL completo con arquitectura Data Lake
en capas Bronze/Silver/Gold y visualizaciones en Python y Power BI.

---

## Arquitectura

```
Bronze (CSV raw) --> Silver (Parquet limpio) --> Gold (Modelo Estrella) --> Análisis
```

El pipeline transforma los datos crudos de aduana en un modelo
dimensional (esquema estrella) listo para análisis y dashboards.

---

## Estructura del Proyecto

```
curso-04-bi/
|
|-- etl/
|   |-- 02_etl_cargar_staging.py      # Ingesta CSV -> capa Silver (lectura paralela con 2 workers)
|   |-- 03_etl_dimensiones.py         # Poblar 12 dimensiones desde staging
|   |-- 04_etl_fact_aduana.py         # Poblar fact_aduana con JOINs masivos
|   |-- 06_exportar_modelo_estrella.py # Exportar modelo estrella a Parquet (Gold)
|   └-- cargar_fin.py                 # Orquestador: ejecuta el pipeline completo
|
|-- sql/
|   |-- 01_crear_tablas.py            # DDL: crea schema dw y todas las tablas
|   |-- 05_olap_analitico.py          # Vistas SQL y tablas agregadas (OLAP)
|   |-- 07_verificar_creacion_tablas.py # Auditoria de calidad e integridad
|   └-- benchmark_hilos.py            # Mide el numero optimo de workers para HDD/SSD
|
|-- reports/
|   |-- analisis_power_bi/            # Scripts de analisis y visualizacion Python
|   |   |-- 01_monto_total_fob.py     # Tarjeta KPI: FOB total acumulado
|   |   |-- 02_iva_total.py           # Tarjeta KPI: IVA total acumulado
|   |   |-- 03_evolucion_fob.py       # Linea temporal: FOB mensual 2025
|   |   |-- 04_top_paises_origen.py   # Barras: Top 10 paises por FOB
|   |   |-- 05_principales_productos.py # Barras: Top 5 productos por FOB
|   |   |-- 06_participacion_aduanas.py # Dona: participacion por puesto aduanero
|   |   └-- 07_dashboard.py           # Dashboard estatico consolidado (PNG)
|   |
|   |-- docente/                      # Ejemplos del docente adaptados al proyecto
|   |   |-- 01_importacion_vs_exportacion.py
|   |   |-- 02_composicion_tributaria.py
|   |   └-- 03_fob_por_rubro.py
|   |
|   └-- output_images/                # Imagenes PNG generadas (no incluidas en repo)
|       |-- analisis_power_bi/
|       └-- docente/
|
|-- pbi/
|   └-- BI_DNIT_Aduanas_Principal.pbix # Dashboard interactivo Power BI (no incluidas en repo)
|
|-- data_lake/                        # Datos (no incluidos en repo)
|   |-- bronze/                       # CSV originales descargados del DNIT
|   |   └-- LISTADO_DE_DESTINACIONES.xlsx # Diccionario de destinaciones (incluido)
|   |-- silver/                       # Parquet limpio generado por el ETL
|   |-- gold/                         # Modelo estrella en Parquet
|   └-- pruebas/                      # CSVs de prueba (subconjunto para desarrollo)
|
|-- db/
|   └-- aduana.duckdb                 # Base de datos DuckDB (no incluida en repo)
|
|-- .gitignore
|-- requirements.txt
|-- pyvenv.cfg
└-- README.md
```

---

## Dashboard Power BI

El archivo `.pbix` no está incluido en el repositorio por su tamaño (172 MB).
Para regenerarlo, conectar Power BI Desktop a los archivos Parquet
de la carpeta `data_lake/gold/` una vez ejecutado el pipeline.

## Como ejecutar

### Requisitos previos
- Python 3.11 o superior
- Git

### Instalacion

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/curso-04-bi.git
cd curso-04-bi

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual (Windows)
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt
```

### Datos

Descargar los archivos CSV mensuales desde el portal de datos abiertos del DNIT:
https://www.dnit.gov.py/web/portal-institucional/datos-abiertos

Colocar los archivos descargados en `data_lake/bronze/`.

Para pruebas con menos datos, colocar un subconjunto de CSVs en `data_lake/pruebas/`
y ajustar la variable `CSV_FOLDER` en `02_etl_cargar_staging.py`.

### Ejecucion

```bash
# Pipeline completo (todos los pasos en orden)
python etl/cargar_fin.py

# O ejecutar paso a paso
python sql/01_crear_tablas.py
python etl/02_etl_cargar_staging.py
python etl/03_etl_dimensiones.py
python etl/04_etl_fact_aduana.py
python sql/05_olap_analitico.py
python etl/06_exportar_modelo_estrella.py
python sql/07_verificar_creacion_tablas.py
```

---

## Modelo de Datos

El modelo sigue un esquema estrella con 1 tabla de hechos y 12 dimensiones:

**Fact Table**
- `fact_aduana` — granularidad a nivel sub-item (5 millones de registros con 12 meses de 2025)

**Dimensiones**
- `dim_fecha`, `dim_pais`, `dim_producto`, `dim_aduana`, `dim_operacion`
- `dim_regimen`, `dim_canal`, `dim_transporte`, `dim_marca`
- `dim_destino`, `dim_acuerdo`, `dim_umedida`

---

## Optimizaciones implementadas

- Lectura paralela de CSVs con `ThreadPoolExecutor` (2 workers, optimo para HDD)
- Conversion de tipos numericos via SQL con `TRY_CAST` en DuckDB (3x mas rapido que pandas)
- Exportacion directa a Parquet desde DuckDB sin pasar por memoria Python
- Tiempo total del pipeline completo (12 meses): aprox. 8-10 minutos en HDD

---

## Tecnologias

- DuckDB 1.5.1 — base de datos analitica embebida
- Pandas 3.0.2 — transformacion de datos
- Matplotlib 3.10.9 — visualizaciones Python
- Power BI Desktop — dashboard interactivo
- Python 3.13

---

## Fuente de Datos

DNIT - Direccion Nacional de Ingresos Tributarios
Portal de Datos Abiertos: https://www.dnit.gov.py/web/portal-institucional/datos-abiertos

Archivos utilizados:
- CSV mensuales de importaciones y exportaciones 2025 (enero a diciembre)
- LISTADO_DE_DESTINACIONES.xlsx — diccionario de 83 destinaciones aduaneras
