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
|   |-- benchmark_hilos.py            # Mide el numero optimo de workers para HDD/SSD
|   └-- verificaciones/                # Scripts de validacion contra el CSV crudo
|       |-- 03_verificacion_general.py     # KPIs sin filtro de operacion (12 meses)
|       |-- 04_verificacion_importacion.py # KPIs solo importacion
|       |-- 05_verificacion_exportacion.py # KPIs solo exportacion
|       └-- 08_validacion_deduplicacion.py # Impacto visual con/sin es_primer_subitem
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
|   |-- examen_final/                 # 3 analisis adicionales requeridos por la catedra
|   |   |-- 01_canal_despacho.py      # Canal de control y tiempos de despacho
|   |   |-- 02_ratio_embalaje.py      # Kilo Bruto vs Kilo Neto por rubro
|   |   └-- 03_acuerdos_comerciales.py # Impacto de acuerdos comerciales en el FOB
|   |
|   └-- output_images/                # Imagenes PNG generadas (no incluidas en repo)
|       |-- analisis_power_bi/
|       |-- docente/
|       └-- examen_final/
|
|-- pbi/
|   └-- BI_DNIT_Aduanas_Principal.pbix # Dashboard interactivo Power BI (no incluido en repo)
|
|-- data_lake/                        # Datos (no incluidos en repo, salvo lo indicado)
|   |-- bronze/                       # CSV originales descargados del DNIT
|   |   |-- LISTADO_DE_DESTINACIONES.xlsx # Diccionario de destinaciones (incluido)
|   |   └-- pruebas/
|   |       └-- 2025_ENERO_Tests.xlsx # Muestra reducida para inspeccionar la estructura de columnas
|   |-- silver/                       # Parquet limpio generado por el ETL
|   └-- gold/                         # Modelo estrella en Parquet
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

El archivo `.pbix` no está incluido en el repositorio por su tamaño (195 MB).
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

El archivo `data_lake/bronze/pruebas/2025_ENERO_Tests.xlsx` contiene una
muestra reducida en formato Excel, usada durante el desarrollo para
inspeccionar visualmente la estructura de columnas del dataset original
antes de automatizar la lectura masiva de los 12 CSV mensuales.

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

### Verificacion contra el CSV crudo

Los scripts de `sql/verificaciones/` recalculan los KPIs principales
(volumen, FOB, IVA, top paises, principales productos, participacion
por aduana) leyendo directamente los 12 archivos CSV con pandas, sin
pasar por DuckDB ni por el pipeline. Sirven para validar de forma
independiente que el modelo Gold no introduce errores de calculo.

```bash
python sql/verificaciones/03_verificacion_general.py
python sql/verificaciones/04_verificacion_importacion.py
python sql/verificaciones/05_verificacion_exportacion.py
```

El script `08_validacion_deduplicacion.py` demuestra el impacto de no
aplicar la deduplicacion por item/sub-item, mostrando el caso extremo
(despacho con 2,340 sub-items donde el FOB queda inflado 2,340x) y una
tabla comparativa de totales con y sin `es_primer_subitem = TRUE`.

```bash
python sql/verificaciones/08_validacion_deduplicacion.py
```

---

## Modelo de Datos

El modelo sigue un esquema estrella con 1 tabla de hechos y 12 dimensiones:

**Fact Table**
- `fact_aduana` — granularidad a nivel sub-item (5,054,024 registros, 12 meses de 2025)

**Dimensiones**
- `dim_fecha`, `dim_pais`, `dim_producto`, `dim_aduana`, `dim_operacion`
- `dim_regimen`, `dim_canal`, `dim_transporte`, `dim_marca`
- `dim_destino`, `dim_acuerdo`, `dim_umedida`

**Campos clave de fact_aduana:**
- `es_primer_subitem` (BOOLEAN) — marca TRUE solo en la primera fila de
  cada combinacion despacho+item. Los campos financieros (FOB, IVA,
  derecho, ISC, renta, kilo_neto, kilo_bruto) son valores de cabecera
  del item que el CSV original repite en cada sub-item; toda consulta
  que sume estos campos debe filtrar `WHERE es_primer_subitem = TRUE`
  para no duplicar los totales (promedio: 2.08 sub-items por item).
- `oficializacion`, `cancelacion` (DATE), `dias_despacho` (INTEGER) —
  fechas de despacho y tiempo de procesamiento aduanero, usadas en el
  Analisis 1 del examen final.
- `fob_usd` — ya viene en USD real en el CSV original (verificado
  contra el despacho 25DA000000015728); no requiere conversion por
  cotizacion.
- `impuesto_iva_real_usd` — `impuesto_iva` SI viene en Guaranies en
  el CSV original, se divide por `tasa_valoracion` para obtener el
  valor real en USD.

**Nota metodologica sobre el filtro de año:** el dataset incluye
despachos con `oficializacion` de 2024 o anios anteriores (arrastre
administrativo: el nombre del archivo CSV representa el periodo de
carga del DNIT, no necesariamente la fecha real de oficializacion).
Para representar estrictamente el año 2025, todas las consultas
filtran adicionalmente `oficializacion BETWEEN '2025-01-01' AND
'2025-12-31'`.

**Nota metodologica sobre deduplicacion:** el portal DNIT documenta
explicitamente que los valores pueden repetirse de forma proporcional
a la cantidad de items y sub-items. El campo `es_primer_subitem = TRUE`
corrige este comportamiento. Sin deduplicar, el FOB total queda inflado
5.18x y el IVA 9.04x respecto al valor real.

---

## Valores de referencia validados (2025 completo)

- Volumen de operaciones (items unicos, deduplicados): 2,377,327
- FOB Total 2025 (con filtro de año): $42,831,593,047.48
- FOB Total sin filtro de año (incluye arrastre 2024 y anteriores): $44,072,551,531.76
- IVA Total (USD real): $1,190,275,573.10
- FOB sin deduplicar (inflado): $221,750,393,736.77 (5.18x el valor real)

---

## Optimizaciones implementadas

- Lectura paralela de CSVs con `ThreadPoolExecutor` (2 workers, optimo para HDD)
- Conversion de tipos numericos via SQL con `TRY_CAST` en DuckDB (3x mas rapido que pandas)
- Exportacion directa a Parquet desde DuckDB sin pasar por memoria Python
- Tiempo total del pipeline completo (12 meses): aprox. 9-10 minutos en HDD

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
