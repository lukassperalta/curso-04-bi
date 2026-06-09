# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Evolución Histórica del Valor FOB
# OBJETIVO: Visualizar el FOB mensual acumulado en 2025
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
# CONSULTA: FOB mensual desde Gold
# JOIN entre fact y dim_fecha para agrupar por mes.
# anio_mes se construye en SQL para garantizar orden correcto.
# Filtro WHERE anio = 2025 — dinámico al agregar más meses.
# ----------------------------------------------------------
conexion = duckdb.connect()

evolucion = conexion.execute(f"""
    SELECT
        d.anio,
        d.mes_numero,
        d.mes_nombre,
        CONCAT(CAST(d.anio AS VARCHAR), '-', LPAD(CAST(d.mes_numero AS VARCHAR), 2, '0')) AS anio_mes,
        SUM(f.fob_real_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_fecha.parquet"}' d
        ON f.fecha_key = d.id_fecha
    WHERE d.anio = 2025
    GROUP BY d.anio, d.mes_numero, d.mes_nombre
    ORDER BY d.anio, d.mes_numero
""").fetchdf()

# ==========================================================
# GRÁFICO: Línea de evolución temporal
# Cada punto es un mes — las anotaciones muestran el valor
# exacto sobre cada punto para facilitar la lectura.
# ==========================================================
figura, eje = plt.subplots(figsize=(12, 5))
figura.suptitle(
    "Evolución Histórica del Valor FOB",
    fontsize=13, fontweight="bold"
)

eje.plot(
    evolucion["anio_mes"],
    evolucion["fob_total"],
    color=PALETA_COLORES[2],
    linewidth=2,
    marker="o",
    markersize=5
)

# Anotación del valor sobre cada punto del gráfico
for _, fila in evolucion.iterrows():
    eje.annotate(
        f"${fila['fob_total'] / 1e6:.1f}mill.",
        xy=(fila["anio_mes"], fila["fob_total"]),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center", fontsize=8, color="#333333"
    )

# Eje Y en millones para mejor legibilidad
eje.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v / 1e6:.0f} mill."))
eje.tick_params(axis="x", labelsize=8, rotation=45)
eje.tick_params(axis="y", labelsize=8)
eje.grid(axis="y", linestyle="--", alpha=0.4)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Evolucion FOB.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()