# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Tarjeta KPI - Monto Total FOB
# OBJETIVO: Visualizar el FOB total acumulado como tarjeta
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
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
# CONSULTA: Total FOB desde Gold
# fob_usd ya viene en USD real en el CSV original (no se divide
# por cotizacion). Filtramos es_primer_subitem = TRUE porque el
# FOB es un valor de cabecera del ítem que se repite en cada
# sub-ítem; sin este filtro el total quedaría duplicado (~2x).
# También filtramos por oficializacion en 2025: el dataset
# incluye despachos con oficializacion de 2024 o años
# anteriores (arrastre administrativo de los CSV mensuales),
# que deben excluirse para representar estrictamente el año.
# ----------------------------------------------------------
conexion = duckdb.connect()

total_fob = conexion.execute(f"""
    SELECT SUM(fob_usd)
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
    WHERE es_primer_subitem = TRUE
    AND oficializacion >= '2025-01-01'
    AND oficializacion <= '2025-12-31'
""").fetchone()[0]

# ==========================================================
# GRÁFICO: Tarjeta KPI estilo Power BI
# FancyBboxPatch simula el contenedor redondeado de la tarjeta
# ==========================================================
figura, eje = plt.subplots(figsize=(6, 3.5))
figura.suptitle(
    "Monto Total FOB USD 2025",
    fontsize=13, fontweight="bold"
)

# Ocultamos ejes para simular tarjeta limpia
eje.axis("off")

# Contenedor redondeado de la tarjeta
rectangulo = FancyBboxPatch(
    (-0.8, -0.5), 1.6, 1.0,
    boxstyle="round,pad=0.05",
    facecolor="#F4F6F9",
    edgecolor=PALETA_COLORES[0],
    linewidth=2
)
eje.add_patch(rectangulo)

# Valor principal centrado
eje.text(
    0, 0.1,
    f"$ {total_fob:,.2f}",
    ha="center", va="center",
    fontsize=22, fontweight="bold",
    color=PALETA_COLORES[0]
)

# Etiqueta descriptiva debajo del valor
eje.text(
    0, -0.25,
    "FOB Total Acumulado (USD)",
    ha="center", va="center",
    fontsize=10, color="#555555"
)

eje.set_xlim(-1, 1)
eje.set_ylim(-1, 1)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Tarjeta Monto Total FOB.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()