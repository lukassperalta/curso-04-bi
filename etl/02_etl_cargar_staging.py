# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Carga de Staging (Capa Silver)
# OBJETIVO: Ingesta de CSV (Aduana) y Excel (Destinaciones)
# ==========================================================

import duckdb
import pandas as pd
import os
import glob
import time
from concurrent.futures import ThreadPoolExecutor

# Cronómetro global
tiempo_inicio = time.time()

# ----------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ----------------------------------------------------------
DB_PATH       = r"C:\curso-04-bi\db\aduana.duckdb"
CSV_FOLDER    = r"C:\curso-04-bi\data_lake\bronze"
DEST_PATH     = r"C:\curso-04-bi\data_lake\bronze\LISTADO_DE_DESTINACIONES.xlsx"
EXPORT_SILVER = r"C:\curso-04-bi\data_lake\silver"

os.makedirs(EXPORT_SILVER, exist_ok=True)
con = duckdb.connect(DB_PATH)

# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------

def sep(msg, char="-"):
    # Imprime separador del mismo largo que el mensaje
    print(char * len(msg))

def log(msg, char="-"):
    # Imprime mensaje con separador debajo
    print(msg)
    sep(msg, char)

def header(msg):
    # Imprime mensaje entre dos líneas de =
    sep(msg, "=")
    print(msg)
    sep(msg, "=")

def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    # Limpia nombres: minúsculas, sin espacios ni caracteres especiales
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
    )
    return df

def leer_csv(archivo):
    # Lee un archivo CSV mensual con encoding Windows (cp1252)
    print(f"  Leyendo: {os.path.basename(archivo)}...")
    return pd.read_csv(
        archivo,
        sep=',',
        quotechar='"',
        dtype=str,
        encoding='cp1252',
        on_bad_lines="skip"
    )

# ==========================================================
# PASO A: CARGA DEL CSV PRINCIPAL (ADUANA)
# ==========================================================
try:
    header("Leyendo CSVs con lectura paralela...")

    archivos_csv = glob.glob(os.path.join(CSV_FOLDER, "*.csv"))

    if len(archivos_csv) == 0:
        raise FileNotFoundError(
            f"No se encontraron archivos CSV en: {CSV_FOLDER}"
        )

    log(f"Se detectaron {len(archivos_csv)} archivos mensuales.")

    # 2 workers: óptimo medido con benchmark en HDD
    workers = 2
    log(f"Iniciando lectura paralela con {workers} workers...")

    # *** Lectura paralela de archivos mensuales ***
    t_lectura = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        lista_dataframes = list(executor.map(leer_csv, archivos_csv))

    log(f"Lectura completada en {time.time() - t_lectura:.1f}s")
    print("Concatenando todos los meses...")
    df_csv = pd.concat(lista_dataframes, ignore_index=True)

    if len(df_csv.columns) <= 1:
        log("ATENCION: solo se detectó 1 columna. Revisá el separador del CSV.")
    else:
        log(f"Columnas detectadas: {len(df_csv.columns)}")

    # ----------------------------------------------------------
    # LIMPIEZA Y NORMALIZACIÓN
    # ----------------------------------------------------------

    # 1. Normalizar nombres de columnas
    df_csv = normalizar_columnas(df_csv)

    # 2. Limpiar pais_origen: quitar código "XX - " del inicio
    if 'pais_origen' in df_csv.columns:
        df_csv['pais_origen'] = (
            df_csv['pais_origen']
            .str.split(' - ')
            .str[-1]
            .str.strip()
        )
        log("OK: pais_origen limpiado.")

    # 3. Limpiar pais_procedenciadestino: misma lógica
    if 'pais_procedenciadestino' in df_csv.columns:
        df_csv['pais_procedenciadestino'] = (
            df_csv['pais_procedenciadestino']
            .str.split(' - ')
            .str[-1]
            .str.strip()
        )
        log("OK: pais_procedenciadestino limpiado.")

    # 4. Corregir Ñ guardada como backslash en el CSV original
    if 'pais_origen' in df_csv.columns:
        df_csv['pais_origen'] = df_csv['pais_origen'].str.replace('ESPA\\A', 'ESPAÑA', regex=False)

    if 'pais_procedenciadestino' in df_csv.columns:
        df_csv['pais_procedenciadestino'] = df_csv['pais_procedenciadestino'].str.replace('ESPA\\A', 'ESPAÑA', regex=False)

    # 5. Acortar descripción de mercadería a 50 caracteres
    if 'mercaderia' in df_csv.columns:
        df_csv['mercaderia'] = df_csv['mercaderia'].str[:50]
        log("OK: mercaderia acortada a 50 caracteres.")

    # 6. Convertir fechas DD/MM/YYYY a TIMESTAMP
    for col in ["oficializacion", "cancelacion"]:
        if col in df_csv.columns:
            df_csv[col] = pd.to_datetime(df_csv[col], errors="coerce", dayfirst=True)

    # ----------------------------------------------------------
    # CARGA A DUCKDB Y CONVERSIÓN DE TIPOS
    # ----------------------------------------------------------

    # 7. Registrar dataframe en DuckDB para operar con SQL
    log("Registrando datos en DuckDB...")
    con.register("df_crudo", df_csv)

    # *** Conversión numérica vía SQL: más rápido que pandas para 5M+ filas ***
    print("Aplicando conversiones de tipos en SQL...")
    t_conv = time.time()

    columnas_numericas = {
        'cotizacion', 'cantidad_estadistica', 'kilo_neto', 'kilo_bruto',
        'fob_dolar', 'flete_dolar', 'seguro_dolar', 'imponible_dolar',
        'imponible_gs', 'total', 'ajuste_a_incluir', 'ajuste_a_deducir',
        'iva', 'derecho', 'isc', 'renta', 'servicio',
        'cantidad_subitem', 'precion_unitario_subitem'
    }

    # Construir SELECT dinámico: TRY_CAST para numéricas, texto para el resto
    cols_df = list(df_csv.columns)
    selects = []
    for col in cols_df:
        if col in columnas_numericas:
            selects.append(
                f"COALESCE(TRY_CAST(REPLACE({col}, ',', '.') AS DOUBLE), 0) AS {col}"
            )
        else:
            selects.append(col)

    select_sql = ",\n        ".join(selects)

    con.execute(f"""
        CREATE OR REPLACE TABLE dw.stg_aduana AS
        SELECT
            {select_sql}
        FROM df_crudo
    """)

    log(f"Conversiones completadas en {time.time() - t_conv:.1f}s")

    # ----------------------------------------------------------
    # EXPORTACIÓN A CAPA SILVER (PARQUET)
    # ----------------------------------------------------------

    # 8. Exportar a Parquet directamente desde DuckDB
    ruta_silver_subitems = os.path.join(EXPORT_SILVER, "silver_aduana_subitems.parquet")
    con.execute(f"COPY dw.stg_aduana TO '{ruta_silver_subitems}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE);")

    cantidad = con.execute("SELECT COUNT(*) FROM dw.stg_aduana").fetchone()[0]

    _ok1 = f"OK: {cantidad:,} sub-ítems exportados a silver_aduana_subitems.parquet"
    _ok2 = f"OK: {cantidad:,} registros cargados en dw.stg_aduana."
    sep(_ok1, "*")
    log(_ok1)
    log(_ok2, "*")

except Exception as e:
    print(f"Error en la carga del CSV: {e}")

# ==========================================================
# PASO B: CARGA DEL DICCIONARIO DE DESTINACIONES (Excel)
# ==========================================================
# DuckDB no lee Excel nativo — pandas sigue siendo necesario aquí
if os.path.exists(DEST_PATH):
    try:
        df_dest = pd.read_excel(DEST_PATH)
        df_dest = normalizar_columnas(df_dest)

        # Renombrar columnas al estándar del modelo
        df_dest = df_dest.rename(columns={
            "cd": "cod_destinacion",
            "descripcin": "descripcion_dest",
            "suspensivo__definitivo__temporal": "tipo_regimen_base",
            "import__export": "tipo_operacion_base"
        })

        con.register("df_dest_temp", df_dest)
        con.execute("CREATE OR REPLACE TABLE dw.stg_destinaciones AS SELECT * FROM df_dest_temp;")

        # Exportar a Parquet
        ruta_silver_dest = os.path.join(EXPORT_SILVER, "silver_destinaciones.parquet")
        con.execute(f"COPY dw.stg_destinaciones TO '{ruta_silver_dest}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE);")

        _ok3 = f"OK: {len(df_dest)} registros insertados en dw.stg_destinaciones."
        sep(_ok3, "*")
        log(_ok3, "*")

    except Exception as e:
        print(f"Aviso en la carga de destinaciones: {e}")

# ----------------------------------------------------------
# CIERRE Y TIEMPO TOTAL
# ----------------------------------------------------------
con.close()

tiempo_total = time.time() - tiempo_inicio
minutos  = int(tiempo_total // 60)
segundos = int(tiempo_total % 60)

header(f"Proceso Finalizado en {minutos} min {segundos} seg.")