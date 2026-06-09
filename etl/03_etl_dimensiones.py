# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Poblado de Dimensiones (Capa Gold)
# OBJETIVO: Cargar dimensiones desde staging a dw.*
# ==========================================================

import duckdb

DB_PATH = r"C:\curso-04-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

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
# FUNCIÓN: Cargar dimensiones simples (mapeo directo)
# ----------------------------------------------------------
def cargar_dimension(tabla_dest, columna_stg, id_name, desc_name):
    log(f"-> Procesando {tabla_dest}...")
    con.execute(f"DELETE FROM {tabla_dest};")
    con.execute(f"""
        INSERT INTO {tabla_dest} ({id_name}, {desc_name})
        SELECT 
            row_number() OVER () as {id_name},
            val as {desc_name}
        FROM (
            SELECT DISTINCT {columna_stg} as val 
            FROM dw.stg_aduana 
            WHERE {columna_stg} IS NOT NULL
        ) t;
    """)

# ==========================================================
# INICIO DEL PROCESO
# ==========================================================
header("Poblando dimensiones desde Staging...")

# ----------------------------------------------------------
# 1. DIMENSIONES SIMPLES (mapeo directo)
# ----------------------------------------------------------
cargar_dimension("dw.dim_aduana",     "aduana",                    "id_aduana",     "aduana_nombre")
cargar_dimension("dw.dim_canal",      "canal",                     "id_canal",      "canal_cod")
cargar_dimension("dw.dim_regimen",    "regimen",                   "id_regimen",    "regimen_cod")
cargar_dimension("dw.dim_transporte", "medio_transporte",          "id_transporte", "medio_transporte_desc")
cargar_dimension("dw.dim_acuerdo",    "acuerdo",                   "id_acuerdo",    "acuerdo_desc")
cargar_dimension("dw.dim_umedida",    "unidad_medida_estadistica", "id_umedida",    "unidad_medida_desc")
cargar_dimension("dw.dim_marca",      "marca_item",                "id_marca",      "marca")
cargar_dimension("dw.dim_destino",    "uso",                       "id_destino",    "uso_estado")

# ----------------------------------------------------------
# 2. DIMENSIÓN OPERACIÓN
# Agrega flags booleanos de importación/exportación
# ----------------------------------------------------------
log("-> Procesando dw.dim_operacion...")
con.execute("DELETE FROM dw.dim_operacion;")
con.execute("""
    INSERT INTO dw.dim_operacion (id_operacion, operacion_desc, es_importacion, es_exportacion)
    SELECT 
        row_number() OVER () as id_operacion,
        operacion as operacion_desc,
        CASE WHEN operacion LIKE 'IMPORT%' THEN TRUE ELSE FALSE END as es_importacion,
        CASE WHEN operacion LIKE 'EXPORT%' THEN TRUE ELSE FALSE END as es_exportacion
    FROM (SELECT DISTINCT operacion FROM dw.stg_aduana WHERE operacion IS NOT NULL) t;
""")

# ----------------------------------------------------------
# 3. DIMENSIÓN PAÍS
# Unificamos Origen y Procedencia para tener un catálogo único
# ----------------------------------------------------------
log("-> Procesando dw.dim_pais...")
con.execute("DELETE FROM dw.dim_pais;")
con.execute("""
    INSERT INTO dw.dim_pais (id_pais, pais_nombre)
    SELECT row_number() OVER () as id_pais, t.pais_full
    FROM (
        -- Traemos países de origen
        SELECT DISTINCT pais_origen AS pais_full 
        FROM dw.stg_aduana 
        WHERE pais_origen IS NOT NULL
        
        UNION -- El UNION elimina duplicados automáticamente
        
        -- Traemos países de procedencia
        SELECT DISTINCT pais_procedenciadestino AS pais_full 
        FROM dw.stg_aduana 
        WHERE pais_procedenciadestino IS NOT NULL
    ) t;
""")

# ----------------------------------------------------------
# 4. DIMENSIÓN PRODUCTO
# Por posición NCM toma la descripción más larga (más completa)
# ----------------------------------------------------------
log("-> Procesando dw.dim_producto (con limpieza de duplicados)...")
con.execute("DELETE FROM dw.dim_producto;")
con.execute("""
    INSERT INTO dw.dim_producto (id_producto, posicion_ncm, rubro, desc_capitulo, desc_partida, desc_posicion, mercaderia)
    SELECT 
        row_number() OVER () as id_producto,
        posicion as posicion_ncm,
        rubro,
        desc_capitulo,
        desc_partida,
        desc_posicion,
        mercaderia
    FROM (
        SELECT 
            posicion, 
            mercaderia,
            rubro,
            desc_capitulo,
            desc_partida,
            desc_posicion,
            -- Numeramos las filas por cada posición NCM,
            -- dándole prioridad a la descripción más larga
            ROW_NUMBER() OVER (
                PARTITION BY posicion 
                ORDER BY length(mercaderia) DESC
            ) as ranking
        FROM dw.stg_aduana
        WHERE posicion IS NOT NULL
    ) t
    WHERE t.ranking = 1;
""")

# ----------------------------------------------------------
# 5. DIMENSIÓN FECHA
# Consolida fechas únicas de oficialización y cancelación
# ----------------------------------------------------------
log("-> Procesando dw.dim_fecha...")
con.execute("DELETE FROM dw.dim_fecha;")
con.execute("""
    INSERT INTO dw.dim_fecha (id_fecha, fecha, anio, mes_numero, mes_nombre, trimestre, anio_mes)
    SELECT 
        -- ID numérico basado en la fecha (Ej: 20240501)
        CAST(strftime(fecha, '%Y%m%d') AS INTEGER) as id_fecha,
        fecha,
        EXTRACT(YEAR FROM fecha) as anio,        -- Año real de la fecha
        EXTRACT(MONTH FROM fecha) as mes_numero, -- Mes real
        strftime(fecha, '%B') as mes_nombre,     -- Nombre del mes
        EXTRACT(QUARTER FROM fecha) as trimestre,
        strftime(fecha, '%Y-%m') as anio_mes
    FROM (
        -- Consolidamos fechas únicas de oficialización y cancelación
        SELECT DISTINCT oficializacion AS fecha FROM dw.stg_aduana WHERE oficializacion IS NOT NULL
        UNION
        SELECT DISTINCT cancelacion AS fecha FROM dw.stg_aduana WHERE cancelacion IS NOT NULL
    ) t;
""")

# ----------------------------------------------------------
# CIERRE
# ----------------------------------------------------------
con.close()
header("Todas las dimensiones han sido pobladas exitosamente.")