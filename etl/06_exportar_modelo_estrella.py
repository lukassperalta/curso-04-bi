# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Exportación Masiva a Capa Gold
# OBJETIVO: Exportar todas las tablas dw.* a Parquet
# ==========================================================

import duckdb
import os

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
# CONFIGURACIÓN DE RUTAS
# ----------------------------------------------------------
DB_PATH     = r"C:\curso-04-bi\db\aduana.duckdb"
EXPORT_GOLD = r"C:\curso-04-bi\data_lake\gold"

if not os.path.exists(EXPORT_GOLD):
    os.makedirs(EXPORT_GOLD)

con = duckdb.connect(DB_PATH)

# ----------------------------------------------------------
# TABLAS A EXPORTAR
# Dimensiones + Fact Table
# ----------------------------------------------------------
tablas = [
    "dim_acuerdo",
    "dim_aduana",
    "dim_canal",
    "dim_destino",
    "dim_fecha",
    "dim_marca",
    "dim_transporte",
    "dim_operacion",
    "dim_pais",
    "dim_producto",
    "dim_regimen",
    "dim_umedida",
    "fact_aduana"
]

# ==========================================================
# EXPORTACIÓN MASIVA A PARQUET
# ==========================================================
header(f"Iniciando exportación masiva a: {EXPORT_GOLD}")

for t in tablas:
    try:
        ruta_archivo = os.path.join(EXPORT_GOLD, f"{t}.parquet")

        # Eliminar archivo previo para evitar error de DuckDB
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

        con.execute(f"COPY dw.{t} TO '{ruta_archivo}' (FORMAT PARQUET);")
        log(f"  [OK] {t}.parquet generado.")

    except Exception as e:
        log(f"  [ERROR] No se pudo exportar {t}: {e}")

# ----------------------------------------------------------
# CIERRE
# ----------------------------------------------------------
con.close()
header("CAPA GOLD ACTUALIZADA CON ÉXITO")