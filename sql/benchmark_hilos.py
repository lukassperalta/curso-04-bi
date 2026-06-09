# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Benchmark de Lectura Paralela (Workers)
# OBJETIVO: Determinar el número óptimo de hilos para
#           la lectura de CSVs mensuales según el hardware
# ==========================================================
# Ejecutar UNA SOLA VEZ antes de configurar el ETL.
# Lee los 12 CSVs con 1, 2, 4 y 8 workers y mide el tiempo.
# El worker más rápido se fija en 02_etl_cargar_staging.py.
#
# NOTA: En HDD el óptimo suele ser 2 (cabezal mecánico).
#       En SSD puede llegar a 4-8 sin penalidad de disco.
# ==========================================================

import glob
import os
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

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
# CONFIGURACIÓN
# ----------------------------------------------------------
CSV_FOLDER   = r"C:\curso-04-bi\data_lake\bronze"
archivos_csv = glob.glob(os.path.join(CSV_FOLDER, "*.csv"))

# ----------------------------------------------------------
# FUNCIÓN: Leer un CSV mensual
# Misma configuración que el ETL para resultados comparables
# ----------------------------------------------------------
def leer_csv(archivo):
    return pd.read_csv(
        archivo,
        sep=',',
        quotechar='"',
        dtype=str,
        encoding='latin1',
        on_bad_lines="skip"
    )

# ==========================================================
# BENCHMARK: 1 lectura completa por cada configuración
# ADVERTENCIA: Lee los CSVs 4 veces en total — tarda varios
# minutos. No es parte del pipeline de producción.
# ==========================================================
header(f"Benchmark iniciado — {len(archivos_csv)} archivos detectados")

for workers in [1, 2, 4, 8]:
    t = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        lista_dataframes = list(executor.map(leer_csv, archivos_csv))
    msg = f"workers={workers} → {time.time()-t:.1f}s"
    log(msg)

header("Benchmark finalizado — fijá el worker ganador en 02_etl_cargar_staging.py")