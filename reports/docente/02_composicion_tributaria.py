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
# Filtra solo IMPORTACION para análisis tributario.
# Los valores vienen en Guaraníes (sin conversión a USD)
# ya que los tributos se liquidan en moneda local.
# ----------------------------------------------------------
conexion = duckdb.connect()

consulta_sql = f"""
    SELECT
        o.operacion_desc,
        f.impuesto_derecho,
        f.impuesto_iva,
        f.impuesto_isc,
        f.anticipo_renta
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_operacion.parquet"}' o
        ON f.operacion_key = o.id_operacion
    WHERE o.operacion_desc = 'IMPORTACION'
"""
datos = conexion.execute(consulta_sql).fetchdf()

# Suma total por tipo de tributo
tributos = {
    "Derecho": datos["impuesto_derecho"].sum(),
    "IVA":     datos["impuesto_iva"].sum(),
    "ISC":     datos["impuesto_isc"].sum(),
    "Renta":   datos["anticipo_renta"].sum(),
}

# Excluir tributos sin recaudación (monto = 0)
tributos = {nombre: monto for nombre, monto in tributos.items() if monto > 0}

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

# Total recaudado como texto debajo del gráfico
total_recaudado = sum(tributos.values())
eje.text(
    0, -1.45,
    f"Total recaudado: Gs {total_recaudado:,.0f}",
    ha="center", fontsize=9, color="#444444"
)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Composición y categorias.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()