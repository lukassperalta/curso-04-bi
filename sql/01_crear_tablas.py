# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Creación de Estructura de Datos (DDL)
# OBJETIVO: Definir el Schema 'dw' y las capas Silver/Gold
# ==========================================================

import duckdb

# ----------------------------------------------------------
# FUNCIONES AUXILIARES DE LOG
# ----------------------------------------------------------

def sep(msg, char="-"):
    print(char * len(msg))

def log(msg, char="-"):
    print(msg)
    sep(msg, char)

def header(msg):
    sep(msg, "=")
    print(msg)
    sep(msg, "=")

# ----------------------------------------------------------
# CONFIGURACIÓN DE CONEXIÓN
# ----------------------------------------------------------
DB_PATH = r"C:\curso-04-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

# ==========================================================
# DDL: DEFINICIÓN COMPLETA DEL MODELO DE DATOS
# ==========================================================
sql = """
CREATE SCHEMA IF NOT EXISTS dw;

-- ==============================================================
-- 1. CAPA SILVER: TABLA DE STAGING (STG_ADUANA)
-- Finalidad: Recibir los datos crudos del CSV sin filtros.
-- Aquí todo es flexible (VARCHAR) para evitar errores de carga.
-- ==============================================================
DROP TABLE IF EXISTS dw.stg_aduana;
CREATE TABLE dw.stg_aduana (
    despacho_cifrado    VARCHAR,
    operacion           VARCHAR,
    destinacion         VARCHAR,
    regimen             VARCHAR,
    oficializacion      VARCHAR,
    cancelacion         VARCHAR,
    anio                INTEGER,
    mes                 VARCHAR,
    aduana              VARCHAR,
    cotizacion          DOUBLE,
    medio_transporte    VARCHAR,
    canal               VARCHAR,
    item                INTEGER,
    pais_origen         VARCHAR,
    pais_procedencia    VARCHAR,
    uso                 VARCHAR,
    unidad_medida_est   VARCHAR,
    cantidad_est        DOUBLE,
    kilo_neto           DOUBLE,
    kilo_bruto          DOUBLE,
    fob_usd             DOUBLE,
    flete_usd           DOUBLE,
    seguro_usd          DOUBLE,
    imponible_usd       DOUBLE,
    imponible_gs        DOUBLE,
    ajuste_incluir      DOUBLE,
    ajuste_deducir      DOUBLE,
    posicion            VARCHAR,
    rubro               VARCHAR,
    desc_capitulo       VARCHAR,
    desc_partida        VARCHAR,
    desc_posicion       VARCHAR,
    mercaderia          VARCHAR,
    marca_item          VARCHAR,
    acuerdo             VARCHAR,
    sub_item_nro        INTEGER,
    sub_item_cantidad   DOUBLE,
    sub_item_precio_un  DOUBLE,
    sub_item_desc       VARCHAR,
    sub_item_marca      VARCHAR,
    derecho             DOUBLE,
    isc                 DOUBLE,
    servicio            DOUBLE,
    renta               DOUBLE,
    iva                 DOUBLE,
    otros               DOUBLE,
    total                DOUBLE
);

-- ================================================
-- 2. CAPA GOLD: 12 TABLAS DE DIMENSIÓN (CONTEXTO)
-- ================================================
DROP TABLE IF EXISTS dw.dim_producto;
CREATE TABLE IF NOT EXISTS dw.dim_producto (
    id_producto    INTEGER PRIMARY KEY,
    rubro          VARCHAR,
    desc_capitulo  VARCHAR,
    desc_partida   VARCHAR,
    posicion_ncm   VARCHAR,
    mercaderia     TEXT,
    desc_posicion  VARCHAR
);

DROP TABLE IF EXISTS dw.dim_marca;
CREATE TABLE IF NOT EXISTS dw.dim_marca (
    id_marca       INTEGER PRIMARY KEY,
    marca          VARCHAR
);

DROP TABLE IF EXISTS dw.dim_fecha;
CREATE TABLE IF NOT EXISTS dw.dim_fecha (
    id_fecha    INTEGER PRIMARY KEY,
    fecha       DATE,
    anio        INTEGER,
    mes_numero  INTEGER,
    mes_nombre  VARCHAR,
    trimestre   INTEGER,
    anio_mes    VARCHAR
);

DROP TABLE IF EXISTS dw.dim_destino;
CREATE TABLE IF NOT EXISTS dw.dim_destino (
    id_destino     INTEGER PRIMARY KEY,
    uso_estado     VARCHAR
);

DROP TABLE IF EXISTS dw.dim_aduana;
CREATE TABLE IF NOT EXISTS dw.dim_aduana (
    id_aduana      INTEGER PRIMARY KEY,
    aduana_nombre  VARCHAR
);

DROP TABLE IF EXISTS dw.dim_pais;
CREATE TABLE IF NOT EXISTS dw.dim_pais (
    id_pais        INTEGER PRIMARY KEY,
    pais_nombre    VARCHAR
);

DROP TABLE IF EXISTS dw.dim_canal;
CREATE TABLE IF NOT EXISTS dw.dim_canal (
    id_canal       INTEGER PRIMARY KEY,
    canal_cod      VARCHAR
);

DROP TABLE IF EXISTS dw.dim_operacion;
CREATE TABLE IF NOT EXISTS dw.dim_operacion (
    id_operacion   INTEGER PRIMARY KEY,
    operacion_desc VARCHAR,
    es_importacion BOOLEAN,
    es_exportacion BOOLEAN
);

DROP TABLE IF EXISTS dw.dim_regimen;
CREATE TABLE IF NOT EXISTS dw.dim_regimen (
    id_regimen     INTEGER PRIMARY KEY,
    regimen_cod    VARCHAR
);

DROP TABLE IF EXISTS dw.dim_transporte;
CREATE TABLE IF NOT EXISTS dw.dim_transporte (
    id_transporte         INTEGER PRIMARY KEY,
    medio_transporte_desc VARCHAR
);

DROP TABLE IF EXISTS dw.dim_acuerdo;
CREATE TABLE IF NOT EXISTS dw.dim_acuerdo (
    id_acuerdo     INTEGER PRIMARY KEY,
    acuerdo_desc   VARCHAR
);

DROP TABLE IF EXISTS dw.dim_umedida;
CREATE TABLE IF NOT EXISTS dw.dim_umedida (
    id_umedida         INTEGER PRIMARY KEY,
    unidad_medida_desc VARCHAR
);

-- Diccionario de destinaciones (83 registros del Excel)
DROP TABLE IF EXISTS dw.stg_destinaciones;
CREATE TABLE dw.stg_destinaciones (
    cod_destinacion     VARCHAR,
    descripcion_dest    VARCHAR,
    tipo_regimen_base   VARCHAR,
    tipo_operacion_base VARCHAR,
    observacion         VARCHAR
);

-- ============================================
-- 3. CAPA GOLD: TABLA DE HECHOS (FACT_ADUANA)
-- Granularidad: Atómica (Nivel Sub-ítem)
-- ============================================
DROP TABLE IF EXISTS dw.fact_aduana;
CREATE TABLE IF NOT EXISTS dw.fact_aduana (
    id_fact              BIGINT PRIMARY KEY,  -- Surrogate Key

    -- Foreign Keys (FK) hacia dimensiones
    fecha_key            INTEGER,
    producto_key         INTEGER,
    marca_key            INTEGER,
    destino_key          INTEGER,
    aduana_key           INTEGER,
    pais_key             INTEGER,
    canal_key            INTEGER,
    operacion_key        INTEGER,
    regimen_key          INTEGER,
    transporte_key       INTEGER,
    acuerdo_key          INTEGER,
    umedida_key          INTEGER,

    -- Claves de negocio (trazabilidad)
    despacho_id          VARCHAR,
    item_nro             INTEGER,
    sub_item_nro         INTEGER,

    -- Flag de deduplicación: TRUE solo en la primera fila de cada
    -- combinación despacho+item. Los campos financieros (FOB, IVA,
    -- derecho, etc.) pertenecen al ITEM y se repiten en cada sub-item
    -- del CSV original. Para sumar totales sin duplicar, filtrar por
    -- es_primer_subitem = TRUE. Para análisis a nivel sub-item
    -- (marca, descripción de producto) usar todas las filas.
    es_primer_subitem    BOOLEAN,

    -- Fechas de despacho (columnas directas, decisión pragmática):
    -- se evaluó modelarlas como FK adicionales hacia dim_fecha
    -- (Role-Playing Dimension), pero se optó por columnas DATE
    -- directas porque solo se usan para calcular dias_despacho
    -- y para un filtro simple de página, sin necesitar drill-down
    -- jerárquico (año/trimestre/mes) propio de cada fecha.
    oficializacion        DATE,
    cancelacion           DATE,
    dias_despacho         INTEGER,

    -- Métricas financieras (precisión: 2 y 4 decimales)
    fob_usd              DECIMAL(18,2),
    flete_usd            DECIMAL(18,2),
    seguro_usd           DECIMAL(18,2),
    kilo_neto            DECIMAL(18,2),
    kilo_bruto            DECIMAL(18,2),
    sub_item_cantidad    DECIMAL(18,2),
    sub_item_precio_un   DECIMAL(18,4),
    ajuste_incluir       DECIMAL(18,2),
    ajuste_deducir       DECIMAL(18,2),

    -- Bloque impositivo (liquidación)
    impuesto_iva         DECIMAL(18,2),
    impuesto_derecho     DECIMAL(18,2),
    impuesto_isc         DECIMAL(18,2),
    anticipo_renta       DECIMAL(18,2),
    tasa_valoracion      DECIMAL(18,2),

    -- Columna normalizada: iva viene en Guaraníes en el CSV
    -- original, se divide por cotizacion para obtener USD real.
    impuesto_iva_real_usd DECIMAL(18,2),

    -- Metadatos de carga
    batch_id             VARCHAR,
    fecha_carga          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----------------------------------------------------------
# EJECUCIÓN Y CIERRE
# ----------------------------------------------------------
con.execute(sql)
con.close()

header("Esquema 'dw' y Tablas (12 Dim + 1 Fact + 1 STG) creadas exitosamente.")