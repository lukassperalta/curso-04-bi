# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Tarjeta KPI - IVA Total
# OBJETIVO: Visualizar el IVA total acumulado como tarjeta
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
# CONSULTA: Total IVA real desde Gold
# impuesto_iva_real_usd = iva / cotizacion (Guaraníes → USD)
# ----------------------------------------------------------
conexion = duckdb.connect()

total_iva = conexion.execute(f"""
    SELECT SUM(impuesto_iva_real_usd)
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
""").fetchone()[0]

# ==========================================================
# GRÁFICO: Tarjeta KPI estilo Power BI
# Usa PALETA_COLORES[1] (rojo) para diferenciar del FOB
# ==========================================================
figura, eje = plt.subplots(figsize=(6, 3.5))
figura.suptitle(
    "IVA Total 2025",
    fontsize=13, fontweight="bold"
)

# Ocultamos ejes para simular tarjeta limpia
eje.axis("off")

# Contenedor redondeado de la tarjeta
rectangulo = FancyBboxPatch(
    (-0.8, -0.5), 1.6, 1.0,
    boxstyle="round,pad=0.05",
    facecolor="#F4F6F9",
    edgecolor=PALETA_COLORES[1],
    linewidth=2
)
eje.add_patch(rectangulo)

# Valor principal centrado
eje.text(
    0, 0.1,
    f"$ {total_iva:,.2f}",
    ha="center", va="center",
    fontsize=22, fontweight="bold",
    color=PALETA_COLORES[1]
)

# Etiqueta descriptiva debajo del valor
eje.text(
    0, -0.25,
    "IVA Total Acumulado (USD)",
    ha="center", va="center",
    fontsize=10, color="#555555"
)

eje.set_xlim(-1, 1)
eje.set_ylim(-1, 1)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Tarjeta IVA Total.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()