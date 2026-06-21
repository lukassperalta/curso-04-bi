# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Auditoría Integral de Calidad y Estructura
# OBJETIVO: Verificar integridad del modelo estrella en dw.*
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

header("AUDITORÍA INTEGRAL DE CALIDAD Y ESTRUCTURA - ADUANAS DNIT")

# ==========================================================
# 1. ESTADO GENERAL DE LAS TABLAS Y CONTEO DE FILAS
# Permite verificar que todas las tablas fueron creadas
# y que la carga de datos fue exitosa (sin tablas vacías).
# ==========================================================
print("\n1) Resumen de Carga y Conteo de Filas:")
print("*" * 80)

tables = con.execute("""
    SELECT table_schema, table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'dw' 
    ORDER BY table_name;
""").fetchdf()

for t in tables["table_name"]:
    count = con.execute(f"SELECT COUNT(*) FROM dw.{t};").fetchone()[0]
    print(f"   {t:.<40} {count:,} filas")

print("*" * 80)

# ==========================================================
# 2. VALIDACIÓN DE NULOS EN FACT TABLE
# Las FKs nulas rompen la integridad referencial del modelo.
# Un NULL en fecha_key o producto_key significa que ese
# registro no pudo ser relacionado con su dimensión.
# ==========================================================
print("\n2) Verificación de valores NULL en Fact Table (fact_aduana):")
print("*" * 80)

fk_columns = [
    "operacion_key",
    "destino_key",
    "regimen_key",
    "aduana_key",
    "pais_key",
    "producto_key",
    "transporte_key",
    "canal_key",
    "umedida_key",
    "acuerdo_key",
    "marca_key",
    "fecha_key"
]

for col in fk_columns:
    nulls = con.execute(f"SELECT COUNT(*) FROM dw.fact_aduana WHERE {col} IS NULL;").fetchone()[0]
    print(f"   - {col:.<35} {nulls} nulos")

print("*" * 80)

# ==========================================================
# 3. DETECCIÓN DE CLAVES HUÉRFANAS (Fact -> Dim)
# Una clave huérfana es un FK en la fact que no tiene
# correspondencia en su dimensión. Indica datos en staging
# que no pudieron ser mapeados durante los JOINs del ETL.
# ==========================================================
print("\n3) Detección de Claves Huérfanas (Fact -> Dim):")
print("*" * 80)

relaciones = {
    "fecha_key":     ("dim_fecha",      "id_fecha"),
    "producto_key":  ("dim_producto",   "id_producto"),
    "aduana_key":    ("dim_aduana",     "id_aduana"),
    "pais_key":      ("dim_pais",       "id_pais"),
    "operacion_key": ("dim_operacion",  "id_operacion"),
    "regimen_key":   ("dim_regimen",    "id_regimen"),
    "transporte_key":("dim_transporte", "id_transporte"),
    "marca_key":     ("dim_marca",      "id_marca")
}

for fk, (dim, pk) in relaciones.items():
    orphans = con.execute(f"""
        SELECT COUNT(*)
        FROM dw.fact_aduana f
        LEFT JOIN dw.{dim} d ON f.{fk} = d.{pk}
        WHERE f.{fk} IS NOT NULL AND d.{pk} IS NULL;
    """).fetchone()[0]
    status = "OK" if orphans == 0 else f"❌ {orphans} HUÉRFANOS"
    print(f"   {fk} -> {dim:.<30} {status}")

print("*" * 80)

# ==========================================================
# 4. DUPLICADOS EN DIMENSIONES
# Una dimensión con duplicados en su llave natural genera
# multiplicación de registros en la fact (fan-out).
# Cada valor debe aparecer una sola vez por dimensión.
# ==========================================================
print("\n4) Control de Duplicados en Dimensiones (Llaves Naturales):")
print("*" * 80)

dim_keys = {
    "dim_operacion":  "operacion_desc",
    "dim_regimen":    "regimen_cod",
    "dim_aduana":     "aduana_nombre",
    "dim_pais":       "pais_nombre",
    "dim_producto":   "posicion_ncm",
    "dim_transporte": "medio_transporte_desc",
    "dim_marca":      "marca"
}

for dim, key in dim_keys.items():
    dup = con.execute(f"""
        SELECT COUNT(*) 
        FROM (
            SELECT {key}, COUNT(*) 
            FROM dw.{dim} 
            GROUP BY {key} 
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    status = "Único" if dup == 0 else f"❌ {dup} DUPLICADOS"
    print(f"   {dim:.<40} {status}")

print("*" * 80)

# ==========================================================
# 5. VALIDACIÓN DE FECHAS
# Fechas nulas en dim_fecha impiden unir hechos con el
# calendario. Son críticas para análisis temporales y
# para los gráficos de evolución histórica.
# ==========================================================
print("\n5) Verificación de Calidad en Dimensión Fecha:")
print("*" * 80)

invalid_dates = con.execute("""
    SELECT COUNT(*) 
    FROM dw.dim_fecha
    WHERE fecha IS NULL;
""").fetchone()[0]

print(f"   - Fechas con formato inválido en dim_fecha: {invalid_dates}")

# Rango de fechas cargadas
rango = con.execute("""
    SELECT MIN(fecha), MAX(fecha), COUNT(DISTINCT anio)
    FROM dw.dim_fecha
    WHERE fecha IS NOT NULL;
""").fetchone()

print(f"   - Fecha mínima: {rango[0]}")
print(f"   - Fecha máxima: {rango[1]}")
print(f"   - Años distintos en el calendario: {rango[2]}")

print("*" * 80)

# ==========================================================
# 6. INTEGRIDAD EN CAPA SILVER (STAGING)
# Si despacho_cifrado o item son nulos, el registro no
# puede ser trazado hasta su origen en el CSV. Es una
# señal de que el archivo fuente tiene filas corruptas.
# ==========================================================
print("\n6) Verificación de Integridad en Capa Silver (Staging):")
print("*" * 80)

stg_nulls = con.execute("""
    SELECT 
        SUM(CASE WHEN despacho_cifrado IS NULL THEN 1 ELSE 0 END) AS null_despacho,
        SUM(CASE WHEN item IS NULL THEN 1 ELSE 0 END) AS null_item
    FROM dw.stg_aduana;
""").fetchone()

print(f"   - Despachos nulos en Staging: {stg_nulls[0]}")
print(f"   - Items nulos en Staging: {stg_nulls[1]}")

# Total de registros en staging vs fact (diferencia esperada = 0)
total_stg  = con.execute("SELECT COUNT(*) FROM dw.stg_aduana").fetchone()[0]
total_fact = con.execute("SELECT COUNT(*) FROM dw.fact_aduana").fetchone()[0]
diferencia = total_stg - total_fact
print(f"   - Registros en staging:   {total_stg:,}")
print(f"   - Registros en fact:      {total_fact:,}")
print(f"   - Diferencia (esperada 0): {diferencia:,}")

print("*" * 80)

# ==========================================================
# 7. CAMPOS DE INGENIERÍA (AJUSTES Y BANDERAS)
# Verifica que los campos calculados tienen valores
# coherentes: ajustes positivos, y exactamente 1
# importación y 1 exportación en dim_operacion.
# ==========================================================
print("\n7) Verificación de Campos de Ingeniería (Ajustes/Banderas):")
print("*" * 80)

ajustes = con.execute("""
    SELECT SUM(ajuste_incluir),
           SUM(ajuste_deducir) 
    FROM dw.fact_aduana
""").fetchone()

ops = con.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE es_importacion = TRUE),
        COUNT(*) FILTER (WHERE es_exportacion = TRUE)
    FROM dw.dim_operacion
""").fetchone()

# Verificar que fob_usd tiene valores > 0
# (fob_real_usd fue eliminado del modelo: tras la corrección era
# idéntico a fob_usd en el 100% de las filas, 0 discrepancias
# verificadas sobre 5.054.024 registros)
fob_validos = con.execute("""
    SELECT COUNT(*) FROM dw.fact_aduana
    WHERE fob_usd > 0
""").fetchone()[0]

print(f"   Total Ajustes Incluir:      {ajustes[0]:,.2f} USD")
print(f"   Total Ajustes Deducir:      {ajustes[1]:,.2f} USD")
print(f"   Banderas: {ops[0]} Importaciones / {ops[1]} Exportaciones")
print(f"   Registros con FOB > 0:      {fob_validos:,}")

print("*" * 80)

# ==========================================================
# 8. VALIDACIÓN DE DEDUPLICACIÓN POR ÍTEM
# Verifica que es_primer_subitem identifica correctamente
# una sola fila por cada combinación despacho+item, y que
# el FOB total deduplicado coincide con la fuente original
# (validado contra los CSV crudos: ~$44,072 millones).
# ==========================================================
print("\n8) Verificación de Deduplicación Item/Sub-ítem:")
print("*" * 80)

dedup_check = con.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE es_primer_subitem = TRUE) AS filas_primer_subitem,
        COUNT(DISTINCT despacho_id || '-' || CAST(item_nro AS VARCHAR)) AS items_unicos
    FROM dw.fact_aduana
""").fetchone()

print(f"   - Filas marcadas como primer sub-ítem: {dedup_check[0]:,}")
print(f"   - Combinaciones únicas despacho+item:  {dedup_check[1]:,}")
coincide = "OK" if dedup_check[0] == dedup_check[1] else "❌ NO COINCIDE"
print(f"   - Validación: {coincide}")

# FOB total deduplicado (el correcto para reportes financieros)
fob_dedup = con.execute("""
    SELECT SUM(fob_usd)
    FROM dw.fact_aduana
    WHERE es_primer_subitem = TRUE
""").fetchone()[0]

print(f"   - FOB Total deduplicado (correcto): $ {fob_dedup:,.2f}")

print("*" * 80)

# ----------------------------------------------------------
# CIERRE
# ----------------------------------------------------------
con.close()
header("AUDITORÍA FINALIZADA EXITOSAMENTE")