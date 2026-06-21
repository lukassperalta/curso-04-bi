# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Principales Productos Importados
# OBJETIVO: Visualizar el Top 5 de productos por FOB
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ----------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ----------------------------------------------------------
carpeta_proyecto = Path(__file__).parent.parent.parent
carpeta_gold     = carpeta_proyecto / "data_lake" / "gold"
carpeta_graficos = Path(__file__).parent.parent / "output_images" / "analisis_power_bi"

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
# CONSULTA: FOB por producto desde Gold
# JOIN con dim_producto para obtener la descripción.
# mercaderia ya fue acortada a 50 chars en el ETL de staging.
# Filtramos es_primer_subitem = TRUE para evitar duplicar el
# FOB de cabecera del ítem en cada sub-ítem.
# También filtramos por oficializacion en 2025: el dataset
# incluye despachos con oficializacion de 2024 o años
# anteriores (arrastre administrativo de los CSV mensuales),
# que deben excluirse para representar estrictamente el año.
# ----------------------------------------------------------
conexion = duckdb.connect()

datos = conexion.execute(f"""
    SELECT
        p.mercaderia,
        SUM(f.fob_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_producto.parquet"}' p
        ON f.producto_key = p.id_producto
    WHERE p.mercaderia IS NOT NULL
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
    GROUP BY p.mercaderia
    ORDER BY fob_total ASC
""").fetchdf()

# Top 5 productos con mayor FOB
fob_por_producto = datos.tail(5)

# Acortamos etiquetas largas para que no desborden el gráfico
etiquetas_cortas = [
    nombre[:45] + "..." if len(nombre) > 45 else nombre
    for nombre in fob_por_producto["mercaderia"]
]

# ==========================================================
# GRÁFICO: Barras horizontales
# Misma estructura que top países — etiquetas al final
# de cada barra con offset del 1% del máximo.
# ==========================================================
figura, eje = plt.subplots(figsize=(10, 5))
figura.suptitle(
    "Principales Productos Importados",
    fontsize=13, fontweight="bold"
)

barras = eje.barh(
    etiquetas_cortas,
    fob_por_producto["fob_total"].values,
    color=PALETA_COLORES[2],
    edgecolor="white",
    height=0.65
)

# Etiqueta de valor al final de cada barra
for barra in barras:
    ancho = barra.get_width()
    eje.text(
        ancho + (fob_por_producto["fob_total"].max() * 0.01),
        barra.get_y() + barra.get_height() / 2,
        f"${ancho / 1e6:.1f}mill.",
        va="center", fontsize=8
    )

# Eje X en millones para mejor legibilidad
eje.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v / 1e6:.0f} mill."))
eje.set_xlabel("FOB (USD)", fontsize=9)
eje.tick_params(axis="y", labelsize=8)
eje.grid(axis="x", linestyle="--", alpha=0.4)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Principales Productos Importados.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()