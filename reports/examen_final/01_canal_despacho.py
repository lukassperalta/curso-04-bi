# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Top Rubros por FOB USD
# OBJETIVO: Visualizar los 8 rubros con mayor valor FOB
#           mediante barras horizontales
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
carpeta_graficos = Path(__file__).parent.parent / "output_images" / "docente"

carpeta_graficos.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# PALETA DE COLORES DEL PROYECTO
# Usa los 4 colores rotativamente en las barras
# ----------------------------------------------------------
PALETA_COLORES = [
    "#012169",
    "#d42858",
    "#009EFF",
    "#25989A"
]

# ----------------------------------------------------------
# CONSULTA: Rubro y FOB desde Gold
# JOIN con dim_producto para obtener la categoría (rubro).
# Se trae el detalle completo y se agrupa en Python
# siguiendo la lógica del docente.
# Filtramos es_primer_subitem = TRUE porque fob_usd es un
# valor de cabecera del ítem que se repite en cada sub-ítem.
# También filtramos por oficializacion en 2025: el dataset
# incluye despachos con oficializacion de 2024 o años
# anteriores (arrastre administrativo de los CSV mensuales),
# que deben excluirse para representar estrictamente el año.
# ----------------------------------------------------------
conexion = duckdb.connect()

consulta_sql = f"""
    SELECT 
        p.rubro,
        f.fob_usd
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_producto.parquet"}' p
        ON f.producto_key = p.id_producto
    WHERE p.rubro IS NOT NULL
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
"""
datos = conexion.execute(consulta_sql).fetchdf()

# ==========================================================
# GRÁFICO: Barras horizontales — Top 8 rubros por FOB
# sort_values ASC + tail(8) → los 8 mayores al final,
# barh los muestra de abajo hacia arriba (mayor arriba).
# Paleta rotativa de 4 colores para diferenciar barras.
# ==========================================================
figura, eje = plt.subplots(figsize=(10, 5))
figura.suptitle(
    "Top Rubros por FOB USD Febrero 2025",
    fontsize=13, fontweight="bold"
)

fob_por_rubro = (
    datos
    .groupby("rubro")["fob_usd"]
    .sum()
    .sort_values(ascending=True)
    .tail(8)
)

# Acortar etiquetas largas para que no desborden el gráfico
etiquetas_cortas = [
    nombre[:45] + "..." if len(nombre) > 45 else nombre
    for nombre in fob_por_rubro.index
]

barras = eje.barh(
    etiquetas_cortas,
    fob_por_rubro.values,
    color     = PALETA_COLORES[:len(fob_por_rubro)],
    edgecolor = "white",
    height    = 0.65
)

# Etiqueta de valor al final de cada barra
for barra in barras:
    ancho = barra.get_width()
    eje.text(
        ancho + (fob_por_rubro.max() * 0.01),
        barra.get_y() + barra.get_height() / 2,
        f"${ancho / 1e6:.1f}M",
        va="center", fontsize=8
    )

# Eje X en millones para mejor legibilidad
eje.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v / 1e6:.0f}M"))
eje.set_xlabel("FOB (USD)", fontsize=9)
eje.tick_params(axis="y", labelsize=8)
eje.grid(axis="x", linestyle="--", alpha=0.4)

# ----------------------------------------------------------
# EXPORTACIÓN Y VERIFICACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "FOB por rubro.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()

# Total general como verificación rápida contra Power BI
print(f"Total FOB real: ${datos['fob_usd'].sum() / 1e6:.2f}M")