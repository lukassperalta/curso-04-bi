# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Top 10 Países de Origen por FOB
# OBJETIVO: Visualizar los principales países exportadores
#           hacia Paraguay según valor FOB acumulado
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
# CONSULTA: FOB por país desde Gold
# JOIN con dim_pais para obtener el nombre del país.
# ORDER BY ASC + tail(10) → los 10 mayores al final,
# barh los muestra de abajo hacia arriba (mayor arriba).
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
        p.pais_nombre,
        SUM(f.fob_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_pais.parquet"}' p
        ON f.pais_key = p.id_pais
    WHERE p.pais_nombre IS NOT NULL
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
    GROUP BY p.pais_nombre
    ORDER BY fob_total ASC
""").fetchdf()

# Top 10 países con mayor FOB
fob_por_pais = datos.tail(10)

# ==========================================================
# GRÁFICO: Barras horizontales
# Etiqueta de valor al final de cada barra con offset del 1%
# del máximo para que no quede pegada a la barra.
# ==========================================================
figura, eje = plt.subplots(figsize=(10, 5))
figura.suptitle(
    "Top 10 Países de Origen",
    fontsize=13, fontweight="bold"
)

barras = eje.barh(
    fob_por_pais["pais_nombre"],
    fob_por_pais["fob_total"],
    color=PALETA_COLORES[2],
    edgecolor="white",
    height=0.65
)

# Etiqueta de valor al final de cada barra
for barra in barras:
    ancho = barra.get_width()
    eje.text(
        ancho + (fob_por_pais["fob_total"].max() * 0.01),
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
ruta_salida = carpeta_graficos / "Top 10 Paises Origen.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()