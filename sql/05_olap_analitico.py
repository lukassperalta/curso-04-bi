# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Estructuras Analíticas OLAP
# OBJETIVO: Implementar vistas, tablas agregadas y consultas
#           analíticas sobre el modelo estrella
# ==========================================================
# Tres estructuras OLAP obligatorias:
#   A. Vistas SQL      → perspectiva de negocio sobre la fact
#   B. Tablas Agregadas → pre-cálculos para acelerar el BI
#   C. Consultas Analíticas → simulación de análisis real
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

header("Configurando Estructuras Analíticas (OLAP)...")

try:
    # ==========================================================
    # A. VISTAS SQL (Perspectiva de Negocio)
    # Une los hechos con las dimensiones más relevantes para
    # análisis de importaciones. Evita escribir JOINs repetidos
    # en cada consulta de negocio.
    # ==========================================================
    con.execute("""
    CREATE OR REPLACE VIEW dw.v_analisis_importaciones AS
    SELECT 
        f.id_fact,
        d_fe.anio,
        d_fe.mes_nombre,
        d_pa.pais_nombre AS origen,
        d_ad.aduana_nombre AS aduana,
        f.fob_usd,
        f.impuesto_iva,
        f.kilo_neto
    FROM dw.fact_aduana f
    JOIN dw.dim_fecha  d_fe ON f.fecha_key  = d_fe.id_fecha
    JOIN dw.dim_pais   d_pa ON f.pais_key   = d_pa.id_pais
    JOIN dw.dim_aduana d_ad ON f.aduana_key = d_ad.id_aduana;
    """)
    log("[OK] Vista analítica v_analisis_importaciones creada.")

    # ==========================================================
    # B. TABLAS AGREGADAS (Performance)
    # Pre-calcula totales por mes para evitar que el BI
    # recorra millones de filas en cada consulta del dashboard.
    # ==========================================================
    con.execute("DROP TABLE IF EXISTS dw.agg_recaudacion_por_mes;")
    con.execute("""
    CREATE TABLE dw.agg_recaudacion_por_mes AS
    SELECT 
        anio,
        mes_nombre,
        SUM(fob_usd)      AS total_fob,
        SUM(impuesto_iva) AS total_iva,
        COUNT(id_fact)    AS cantidad_despachos
    FROM dw.v_analisis_importaciones
    GROUP BY anio, mes_nombre
    ORDER BY anio DESC, total_fob DESC;
    """)
    log("[OK] Tabla agregada agg_recaudacion_por_mes creada.")

    # ==========================================================
    # C. CONSULTAS ANALÍTICAS (Simulación)
    # Demuestra el uso de las estructuras OLAP creadas.
    # Consulta los 5 países de origen con mayor valor FOB
    # acumulado — caso de uso típico de análisis de comercio.
    # ==========================================================
    print("\nEjecutando consulta analítica de prueba (Top 5 Orígenes):")
    sep("Ejecutando consulta analítica de prueba (Top 5 Orígenes):")
    res = con.execute("""
        SELECT origen, SUM(fob_usd) as total 
        FROM dw.v_analisis_importaciones 
        GROUP BY origen 
        ORDER BY total DESC 
        LIMIT 5
    """).df()
    res["total"] = res["total"].apply(lambda x: f"${x:,.0f}")
    print(res)
    sep(str(res.to_string().split('\n')[0]))

except Exception as e:
    log(f"Error en fase OLAP: {e}")

finally:
    con.close()

header("Estructuras OLAP configuradas exitosamente.")