# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Verificación General desde CSV Crudo (Año Completo)
# OBJETIVO: Validar los KPIs del dashboard de Power BI
#           leyendo directo del CSV original, sin pasar por
#           Silver/Gold, para descartar errores en el ETL.
# ==========================================================
# IMPORTANTE: se deben cargar los 12 meses, no solo uno.
# El campo 'oficializacion' no respeta los límites del
# archivo mensual — un despacho con oficializacion de enero
# puede estar físicamente guardado en el CSV de febrero o
# marzo (y viceversa). Verificado: cargando solo enero se
# pierden ~16,245 filas que sí tienen oficializacion=enero
# pero están en otros archivos. Por eso este script carga
# TODOS los meses y luego filtra por oficializacion real.
# ==========================================================

import pandas as pd
from pathlib import Path

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
CARPETA_BRONZE = Path(r"C:\curso-04-bi\data_lake\bronze")
ARCHIVOS_CSV   = sorted(CARPETA_BRONZE.glob("2025_*.csv"))   # Carga los 12 meses

# Filtro de operación: None = todas, 'IMPORTACION' o 'EXPORTACION'
FILTRO_OPERACION = None

# Mes específico a verificar (filtro real sobre oficializacion)
ANIO_VERIFICAR = 2025
MES_VERIFICAR  = 1   # 1 = Enero

# ----------------------------------------------------------
# FUNCIÓN: Normalizar nombres de columnas
# Misma lógica que el ETL: minúsculas, sin espacios/símbolos
# ----------------------------------------------------------
def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
    )
    return df

# ----------------------------------------------------------
# FUNCIÓN: Leer y limpiar un CSV mensual
# Replica las transformaciones del ETL (02_etl_cargar_staging.py)
# ----------------------------------------------------------
def leer_csv_limpio(ruta_archivo):
    log(f"Leyendo: {ruta_archivo.name}...")

    df = pd.read_csv(
        ruta_archivo,
        sep=',',
        quotechar='"',
        dtype=str,
        encoding='cp1252',
        on_bad_lines="skip"
    )

    df = normalizar_columnas(df)

    # Limpieza de país (igual que el ETL)
    if 'pais_origen' in df.columns:
        df['pais_origen'] = df['pais_origen'].str.split(' - ').str[-1].str.strip()
        df['pais_origen'] = df['pais_origen'].str.replace('ESPA\\A', 'ESPAÑA', regex=False)

    # Conversión numérica: coma -> punto
    columnas_numericas = ['fob_dolar', 'iva', 'cotizacion']
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].str.replace(",", ".", regex=False), errors="coerce")

    # Conversión de fecha: necesaria para filtrar por oficializacion real,
    # no por el campo 'mes' del CSV. 'mes' representa el período de carga
    # administrativa del DNIT y puede incluir despachos oficializados en
    # meses anteriores (ej: ~19,536 filas de 2025_ENERO.csv tienen
    # oficializacion de diciembre 2024 o años previos).
    if 'oficializacion' in df.columns:
        df['oficializacion'] = pd.to_datetime(df['oficializacion'], errors='coerce', dayfirst=True)

    return df

# ==========================================================
# CARGA DE DATOS
# ==========================================================
header(f"Verificación General desde CSV Crudo ({len(ARCHIVOS_CSV)} archivos)")

dataframes = [leer_csv_limpio(archivo) for archivo in ARCHIVOS_CSV]
df = pd.concat(dataframes, ignore_index=True)
log(f"Total filas cargadas (12 meses): {len(df):,}")

if FILTRO_OPERACION:
    df = df[df['operacion'] == FILTRO_OPERACION]
    log(f"Filtro aplicado: operacion = {FILTRO_OPERACION}")

# Filtro por oficializacion real (no por el campo 'mes' del CSV)
# Esto excluye despachos que llegaron en otro archivo mensual
# pero fueron oficializados fuera del período a verificar.
total_antes = len(df)
df = df[
    (df['oficializacion'].dt.year == ANIO_VERIFICAR) &
    (df['oficializacion'].dt.month == MES_VERIFICAR)
]
log(f"Filtro oficializacion = {MES_VERIFICAR}/{ANIO_VERIFICAR}: {len(df):,} filas (de {total_antes:,} totales cargadas)")

# ----------------------------------------------------------
# DEDUPLICACIÓN: una fila por despacho+item
# El FOB e IVA son valores de cabecera del item que se
# repiten en cada sub-item — se debe tomar uno solo por item.
# ----------------------------------------------------------
df_dedup = df.drop_duplicates(subset=["despacho_cifrado", "item"]).copy()
df_dedup["iva_usd"] = df_dedup["iva"] / df_dedup["cotizacion"]

# ==========================================================
# KPI 1: VOLUMEN DE OPERACIONES
# ==========================================================
print("\n1) Volumen de Operaciones (items únicos):")
print("*" * 80)
print(f"   {len(df_dedup):,} operaciones")
print("*" * 80)

# ==========================================================
# KPI 2: MONTO TOTAL FOB USD
# ==========================================================
print("\n2) Monto Total FOB (USD):")
print("*" * 80)
total_fob = df_dedup["fob_dolar"].sum()
print(f"   $ {total_fob:,.2f}")
print("*" * 80)

# ==========================================================
# KPI 3: IVA TOTAL (USD)
# ==========================================================
print("\n3) IVA Total (USD):")
print("*" * 80)
total_iva = df_dedup["iva_usd"].sum()
print(f"   $ {total_iva:,.2f}")
print("*" * 80)

# ==========================================================
# KPI 4: FOB ENERO (idéntico al KPI 2 en este script de un
# solo mes — se mantiene como punto de control nombrado para
# cuando se extienda el script a más meses)
# ==========================================================
print("\n4) FOB Enero (punto de control):")
print("*" * 80)
print(f"   $ {total_fob:,.2f}")
print("*" * 80)

# ==========================================================
# KPI 5: TOP 10 PAÍSES DE ORIGEN
# ==========================================================
print("\n5) Top 10 Países de Origen (FOB USD):")
print("*" * 80)
top_paises = (
    df_dedup.groupby("pais_origen")["fob_dolar"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)
for pais, monto in top_paises.items():
    print(f"   {pais:.<35} $ {monto:,.2f}")
print("*" * 80)

# ==========================================================
# KPI 6: PRINCIPALES PRODUCTOS (agrupado por posición NCM)
# Se agrupa por 'posicion' (código arancelario), no por
# descripción de texto, para replicar exactamente la lógica
# de dim_producto en Power BI: múltiples despachos con
# descripciones de texto distintas pero el mismo código NCM
# se consideran "el mismo producto" y se suman juntos.
# ==========================================================
print("\n6) Principales Productos por Posición NCM (FOB USD):")
print("*" * 80)
top_productos = (
    df_dedup.groupby("posicion")
    .agg(fob_total=("fob_dolar", "sum"), mercaderia=("mercaderia", "first"))
    .sort_values("fob_total", ascending=False)
    .head(5)
)
for posicion, fila in top_productos.iterrows():
    desc_corta = str(fila["mercaderia"])[:50]
    print(f"   [{posicion}] {desc_corta:.<45} $ {fila['fob_total']:,.2f}")
print("*" * 80)

# ==========================================================
# KPI 7: PARTICIPACIÓN POR PUESTO ADUANERO
# ==========================================================
print("\n7) Participación por Puesto Aduanero (FOB USD):")
print("*" * 80)
top_aduanas = (
    df_dedup.groupby("aduana")["fob_dolar"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)
total_top5 = top_aduanas.sum()
for aduana, monto in top_aduanas.items():
    pct = monto / total_top5 * 100
    print(f"   {aduana:.<35} $ {monto:,.2f}  ({pct:.1f}%)")
print("*" * 80)

header("Verificación finalizada")