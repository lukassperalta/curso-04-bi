# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Carga de Fact Table (Capa Gold)
# OBJETIVO: Poblar fact_aduana con JOINs desde staging
# ==========================================================

import duckdb
import time

# Cronómetro global
tiempo_inicio = time.time()

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

# ==========================================================
# INICIO DEL PROCESO
# ==========================================================
header("Iniciando la carga de la Fact Table (Hechos)...")

# Limpieza previa de la tabla destino
con.execute("DELETE FROM dw.fact_aduana;")

# ----------------------------------------------------------
# INSERCIÓN CON JOINs MASIVOS
# Relacionamos stg_aduana con cada dimensión para obtener las llaves (Keys)
# ----------------------------------------------------------
try:
    con.execute("""
    INSERT INTO dw.fact_aduana (
        id_fact, fecha_key, producto_key, marca_key, destino_key, aduana_key, 
        pais_key, canal_key, operacion_key, regimen_key, transporte_key, 
        acuerdo_key, umedida_key, despacho_id, item_nro, sub_item_nro, 
        fob_usd, flete_usd, seguro_usd, kilo_neto, kilo_bruto, sub_item_cantidad,
        sub_item_precio_un, ajuste_incluir, ajuste_deducir, impuesto_iva, 
        impuesto_derecho, impuesto_isc, anticipo_renta, tasa_valoracion, 
        fob_real_usd, impuesto_iva_real_usd, batch_id
    )
    SELECT 
        row_number() OVER () as id_fact,
        d_fe.id_fecha,
        d_pr.id_producto,
        d_ma.id_marca,
        d_de.id_destino, 
        d_ad.id_aduana,
        d_pa.id_pais,
        d_ca.id_canal,
        d_op.id_operacion,
        d_re.id_regimen,
        d_tr.id_transporte,
        d_ac.id_acuerdo,
        d_um.id_umedida,
        s.despacho_cifrado,
        s.item,
        s.numero_subitem,
        CAST(s.fob_dolar AS DOUBLE),
        CAST(s.flete_dolar AS DOUBLE),
        CAST(s.seguro_dolar AS DOUBLE),
        CAST(s.kilo_neto AS DOUBLE),
        CAST(s.kilo_bruto AS DOUBLE),
        CAST(s.cantidad_subitem AS DOUBLE),
        CAST(s.precion_unitario_subitem AS DOUBLE),
        CAST(s.ajuste_a_incluir AS DOUBLE),
        CAST(s.ajuste_a_deducir AS DOUBLE),
        CAST(s.iva AS DOUBLE),
        CAST(s.derecho AS DOUBLE),
        CAST(s.isc AS DOUBLE),
        CAST(s.renta AS DOUBLE),
        CAST(s.cotizacion AS DOUBLE),
        
        -- Cálculos normalizados: convierte Guaraníes a USD usando cotización del día
        s.fob_dolar::DOUBLE / s.cotizacion::DOUBLE as fob_real_usd,
        s.iva::DOUBLE / s.cotizacion::DOUBLE as impuesto_iva_real_usd,
        
        'BATCH_001'
    FROM dw.stg_aduana s
    -- Columnas normalizadas (minúsculas con guiones bajos)
    LEFT JOIN dw.dim_fecha      d_fe ON s.oficializacion            = d_fe.fecha
    LEFT JOIN dw.dim_producto   d_pr ON s.posicion                  = d_pr.posicion_ncm
    LEFT JOIN dw.dim_marca      d_ma ON s.marca_item                = d_ma.marca
    LEFT JOIN dw.dim_destino    d_de ON s.uso                       = d_de.uso_estado
    LEFT JOIN dw.dim_aduana     d_ad ON s.aduana                    = d_ad.aduana_nombre
    LEFT JOIN dw.dim_pais       d_pa ON s.pais_origen               = d_pa.pais_nombre
    LEFT JOIN dw.dim_canal      d_ca ON s.canal                     = d_ca.canal_cod
    LEFT JOIN dw.dim_operacion  d_op ON s.operacion                 = d_op.operacion_desc
    LEFT JOIN dw.dim_regimen    d_re ON s.regimen                   = d_re.regimen_cod
    LEFT JOIN dw.dim_transporte d_tr ON s.medio_transporte          = d_tr.medio_transporte_desc
    LEFT JOIN dw.dim_acuerdo    d_ac ON s.acuerdo                   = d_ac.acuerdo_desc
    LEFT JOIN dw.dim_umedida    d_um ON s.unidad_medida_estadistica  = d_um.unidad_medida_desc;
    """)

    count_fact = con.execute("SELECT COUNT(*) FROM dw.fact_aduana").fetchone()[0]
    log(f"Fact Table cargada exitosamente con {count_fact:,} registros.")

except Exception as e:
    log(f"Error en el proceso: {e}")

finally:
    con.close()

# ----------------------------------------------------------
# CIERRE Y TIEMPO TOTAL
# ----------------------------------------------------------
tiempo_total = time.time() - tiempo_inicio
minutos  = int(tiempo_total // 60)
segundos = int(tiempo_total % 60)

header(f"Proceso Finalizado en {minutos} min {segundos} seg.")