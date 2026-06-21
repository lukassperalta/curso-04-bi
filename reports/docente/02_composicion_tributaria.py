# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Composición Tributaria - Importaciones
# OBJETIVO: Visualizar la distribución de tributos
#           (Derecho, IVA, ISC, Renta) en importaciones
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
from pathlib import Path

# ----------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ----------------------------------------------------------
carpeta_proyecto = Path(__file__).parent.parent.parent
carpeta_gold     = carpeta_proyecto / "data_lake" / "gold"
carpeta_graficos = Path(__file__).parent.parent / "output_images" / "docente"

carpeta_graficos.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# PALETA DE COLORES DEL PROYECTO
# ----------------------------------------------------------
PALETA_COLORES = [
    "#012169",
    "#d42858",
    "#009EFF",
    "#25989A"
]

# ----------------------------------------------------------
# CONSULTA: Tributos de importaciones desde Gold
# Divide cada tributo por la cotización del día para
# obtener el valor real en USD por operación.
# Se excluyen registros con cotización 0 para evitar
# división por cero.
# Filtramos es_primer_subitem = TRUE porque los 4 tributos
# son valores de cabecera del ítem que se repiten en cada
# sub-ítem; sin este filtro, los totales quedarían duplicados.
# También filtramos por oficializacion en 2025: el dataset
# incluye despachos con oficializacion de 2024 o años
# anteriores (arrastre administrativo de los CSV mensuales),
# que deben excluirse para representar estrictamente el año.
# ----------------------------------------------------------
conexion = duckdb.connect()

consulta_sql = f"""
    SELECT
        SUM(f.impuesto_derecho / f.tasa_valoracion) AS derecho,
        SUM(f.impuesto_iva     / f.tasa_valoracion) AS iva,
        SUM(f.impuesto_isc     / f.tasa_valoracion) AS isc,
        SUM(f.anticipo_renta   / f.tasa_valoracion) AS renta
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_operacion.parquet"}' o
        ON f.operacion_key = o.id_operacion
    WHERE o.operacion_desc = 'IMPORTACION'
    AND f.tasa_valoracion > 0
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
"""
datos = conexion.execute(consulta_sql).fetchone()

# Suma total por tipo de tributo en USD real
tributos = {
    "Derecho": datos[0],
    "IVA":     datos[1],
    "ISC":     datos[2],
    "Renta":   datos[3],
}

# Excluir tributos sin recaudación (monto = 0)
tributos = {nombre: monto for nombre, monto in tributos.items() if monto and monto > 0}

# ==========================================================
# GRÁFICO: Pie chart de composición tributaria
# Cada sector representa la proporción de un tributo
# sobre el total recaudado en importaciones.
# El total se muestra como texto debajo del gráfico.
# ==========================================================
figura, eje = plt.subplots(figsize=(7, 5))
figura.suptitle(
    "Composición tributaria - Importaciones 2025",
    fontsize=13, fontweight="bold"
)

sectores, textos, porcentajes = eje.pie(
    list(tributos.values()),
    labels     = list(tributos.keys()),
    autopct    = "%1.1f%%",
    colors     = PALETA_COLORES[:len(tributos)],
    startangle = 140,
    wedgeprops = {"edgecolor": "white", "linewidth": 1.5},
    textprops  = {"fontsize": 10},
)

# Porcentajes en negrita para mejor legibilidad
for texto_pct in porcentajes:
    texto_pct.set_fontsize(9)
    texto_pct.set_fontweight("bold")

# Total recaudado en USD real como texto debajo del gráfico
total_recaudado = sum(tributos.values())
eje.text(
    0, -1.45,
    f"Total recaudado: $ {total_recaudado:,.2f} USD",
    ha="center", fontsize=9, color="#444444"
)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Composición y categorias.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()