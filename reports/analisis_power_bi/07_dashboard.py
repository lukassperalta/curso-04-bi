# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Dashboard Integral - Análisis Aduana DNIT 2025
# OBJETIVO: Consolidar todos los KPIs y gráficos en un
#           único dashboard estático exportado a PNG
# ==========================================================
# Layout del dashboard:
#   Fila 1: [ KPI FOB ] [ KPI IVA ] [ Evolución FOB      ]
#   Fila 2: [ Top 10 Países       ] [ Principales Productos ]
#   Fila 3: [       Dona Aduanera (centrada)               ]
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
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
    "#25989A",
    "#A0C4FF",
    "#BDB2FF",
    "#FFC6FF",
]

# ==========================================================
# CONSULTAS: Carga de datos desde Gold
# Cada consulta alimenta un visual del dashboard.
# Se ejecutan todas antes de renderizar para separar
# la capa de datos de la capa de visualización.
# ==========================================================
conexion = duckdb.connect()

# KPI: FOB total acumulado
total_fob = conexion.execute(f"""
    SELECT SUM(fob_real_usd)
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
""").fetchone()[0]

# KPI: IVA total acumulado
total_iva = conexion.execute(f"""
    SELECT SUM(impuesto_iva_real_usd)
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
""").fetchone()[0]

# Línea temporal: FOB mensual 2025
evolucion = conexion.execute(f"""
    SELECT
        d.anio, d.mes_numero,
        CONCAT(CAST(d.anio AS VARCHAR), '-', LPAD(CAST(d.mes_numero AS VARCHAR), 2, '0')) AS anio_mes,
        SUM(f.fob_real_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_fecha.parquet"}' d ON f.fecha_key = d.id_fecha
    WHERE d.anio = 2025
    GROUP BY d.anio, d.mes_numero
    ORDER BY d.anio, d.mes_numero
""").fetchdf()

# Barras: Top 10 países por FOB (ASC + tail = mayor arriba en barh)
paises = conexion.execute(f"""
    SELECT p.pais_nombre, SUM(f.fob_real_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_pais.parquet"}' p ON f.pais_key = p.id_pais
    WHERE p.pais_nombre IS NOT NULL
    GROUP BY p.pais_nombre
    ORDER BY fob_total ASC
""").fetchdf().tail(10)

# Barras: Top 5 productos por FOB
productos = conexion.execute(f"""
    SELECT p.mercaderia, SUM(f.fob_real_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_producto.parquet"}' p ON f.producto_key = p.id_producto
    WHERE p.mercaderia IS NOT NULL
    GROUP BY p.mercaderia
    ORDER BY fob_total ASC
""").fetchdf().tail(5)

# Dona: Top 5 aduanas por FOB
aduanas = conexion.execute(f"""
    SELECT a.aduana_nombre, SUM(f.fob_real_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_aduana.parquet"}' a ON f.aduana_key = a.id_aduana
    WHERE a.aduana_nombre IS NOT NULL
    GROUP BY a.aduana_nombre
    ORDER BY fob_total DESC
""").fetchdf().head(5)

# ==========================================================
# LAYOUT: GridSpec con proporciones ajustadas
# height_ratios controla el alto relativo de cada fila.
# subgridspec divide la fila de KPIs y la fila de la dona.
# ==========================================================
figura = plt.figure(figsize=(24, 18))
figura.patch.set_facecolor("#F4F6F9")

gs = GridSpec(
    3, 2,
    figure=figura,
    height_ratios=[0.6, 1.5, 2.5],
    hspace=0.55,
    wspace=0.35,
    left=0.07, right=0.97,
    top=0.93, bottom=0.07
)

figura.suptitle(
    "Dashboard - Análisis Aduana DNIT 2025",
    fontsize=18, fontweight="bold", color=PALETA_COLORES[0]
)

# ----------------------------------------------------------
# FILA 0: KPI FOB | KPI IVA | Evolución FOB
# subgridspec divide la fila en 4 columnas:
# KPIs en col 0 y 1, evolución ocupa col 2 y 3
# ----------------------------------------------------------
gs_top = gs[0, :].subgridspec(1, 4, wspace=0.4)

# KPI FOB
eje_kpi1 = figura.add_subplot(gs_top[0, 0])
eje_kpi1.axis("off")
eje_kpi1.add_patch(FancyBboxPatch(
    (0.05, 0.1), 0.9, 0.8,
    boxstyle="round,pad=0.05",
    facecolor="white",
    edgecolor=PALETA_COLORES[0],
    linewidth=2,
    transform=eje_kpi1.transAxes
))
eje_kpi1.text(0.5, 0.65, f"$ {total_fob:,.2f}",
    ha="center", va="center", fontsize=14, fontweight="bold",
    color=PALETA_COLORES[0], transform=eje_kpi1.transAxes)
eje_kpi1.text(0.5, 0.30, "Monto Total FOB (USD)",
    ha="center", va="center", fontsize=10, color="#555555",
    transform=eje_kpi1.transAxes)

# KPI IVA
eje_kpi2 = figura.add_subplot(gs_top[0, 1])
eje_kpi2.axis("off")
eje_kpi2.add_patch(FancyBboxPatch(
    (0.05, 0.1), 0.9, 0.8,
    boxstyle="round,pad=0.05",
    facecolor="white",
    edgecolor=PALETA_COLORES[1],
    linewidth=2,
    transform=eje_kpi2.transAxes
))
eje_kpi2.text(0.5, 0.65, f"$ {total_iva:,.2f}",
    ha="center", va="center", fontsize=14, fontweight="bold",
    color=PALETA_COLORES[1], transform=eje_kpi2.transAxes)
eje_kpi2.text(0.5, 0.30, "IVA Total (USD)",
    ha="center", va="center", fontsize=10, color="#555555",
    transform=eje_kpi2.transAxes)

# Evolución FOB — ocupa columnas 2 y 3 del subgridspec
eje_evol = figura.add_subplot(gs_top[0, 2:])
eje_evol.set_title("Evolución Histórica del Valor FOB", fontsize=11, fontweight="bold")
eje_evol.plot(
    evolucion["anio_mes"], evolucion["fob_total"],
    color=PALETA_COLORES[2], linewidth=2, marker="o", markersize=6
)
for _, fila in evolucion.iterrows():
    eje_evol.annotate(
        f"${fila['fob_total']/1e6:.1f}mill.",
        xy=(fila["anio_mes"], fila["fob_total"]),
        xytext=(0, 10), textcoords="offset points",
        ha="center", fontsize=8, color="#333333"
    )
eje_evol.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e6:.0f}mill."))
eje_evol.tick_params(axis="x", labelsize=8, rotation=20)
eje_evol.tick_params(axis="y", labelsize=8)
eje_evol.grid(axis="y", linestyle="--", alpha=0.4)

# ----------------------------------------------------------
# FILA 1: Top Países | Principales Productos
# set_xlim con 1.2x evita que las etiquetas se corten
# ----------------------------------------------------------

# Top 10 países
eje_paises = figura.add_subplot(gs[1, 0])
eje_paises.set_title("Top 10 Países de Origen", fontsize=11, fontweight="bold")
eje_paises.barh(
    paises["pais_nombre"], paises["fob_total"],
    color=PALETA_COLORES[2], edgecolor="white", height=0.65
)
for barra in eje_paises.patches:
    ancho = barra.get_width()
    eje_paises.text(
        ancho + (paises["fob_total"].max() * 0.01),
        barra.get_y() + barra.get_height() / 2,
        f"${ancho/1e6:.1f}mill.", va="center", fontsize=8
    )
eje_paises.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e6:.0f}mill."))
eje_paises.tick_params(axis="y", labelsize=8)
eje_paises.tick_params(axis="x", labelsize=8)
eje_paises.grid(axis="x", linestyle="--", alpha=0.4)
eje_paises.set_xlim(0, paises["fob_total"].max() * 1.2)

# Top 5 productos
eje_prod = figura.add_subplot(gs[1, 1])
eje_prod.set_title("Principales Productos Importados", fontsize=11, fontweight="bold")
etiquetas_cortas = [
    n[:40] + "..." if len(n) > 40 else n
    for n in productos["mercaderia"]
]
eje_prod.barh(
    etiquetas_cortas, productos["fob_total"].values,
    color=PALETA_COLORES[2], edgecolor="white", height=0.65
)
for barra in eje_prod.patches:
    ancho = barra.get_width()
    eje_prod.text(
        ancho + (productos["fob_total"].max() * 0.01),
        barra.get_y() + barra.get_height() / 2,
        f"${ancho/1e6:.1f}mill.", va="center", fontsize=8
    )
eje_prod.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e6:.0f}mill."))
eje_prod.tick_params(axis="y", labelsize=8)
eje_prod.tick_params(axis="x", labelsize=8)
eje_prod.grid(axis="x", linestyle="--", alpha=0.4)
eje_prod.set_xlim(0, productos["fob_total"].max() * 1.2)

# ----------------------------------------------------------
# FILA 2: Dona centrada
# subgridspec de 5 columnas — dona ocupa col 1 a 3
# width=0.6 en wedgeprops genera el hueco central de la dona
# ----------------------------------------------------------
gs_bot = gs[2, :].subgridspec(1, 5, wspace=0.3)
eje_aduana = figura.add_subplot(gs_bot[0, 1:4])
eje_aduana.set_title("Participación por Puesto Aduanero", fontsize=11, fontweight="bold")
sectores, textos, porcentajes = eje_aduana.pie(
    aduanas["fob_total"],
    labels=None,
    autopct="%1.0f%%",
    colors=PALETA_COLORES[:len(aduanas)],
    startangle=90,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5, "width": 0.6},
    textprops={"fontsize": 9}
)
# Porcentajes en blanco y negrita para contraste
for p in porcentajes:
    p.set_fontweight("bold")
    p.set_color("white")
eje_aduana.legend(
    aduanas["aduana_nombre"], loc="lower center",
    bbox_to_anchor=(0.5, -0.25), fontsize=8, ncol=2
)

# ----------------------------------------------------------
# EXPORTACIÓN — dpi=150 para buena resolución del PNG
# ----------------------------------------------------------
plt.savefig(carpeta_graficos / "Dashboard Aduana 2025.png", bbox_inches="tight", dpi=150)
plt.show()