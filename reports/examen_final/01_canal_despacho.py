# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Análisis 1 - Canal de Control y Tiempos de Despacho
# OBJETIVO: Visualizar la distribución de operaciones por canal
#           y los días promedio de despacho diferenciados por color
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
from pathlib import Path

# ----------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ----------------------------------------------------------
carpeta_proyecto = Path(__file__).parent.parent.parent
carpeta_gold     = carpeta_proyecto / "data_lake" / "gold"
carpeta_graficos = Path(__file__).parent.parent / "output_images" / "examen_final"

carpeta_graficos.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# COLORES POR CANAL — representan el semáforo aduanero
# ----------------------------------------------------------
COLORES_CANAL = {
    "V": "#2ecc71",
    "N": "#e67e22",
    "R": "#e74c3c",
}

NOMBRES_CANAL = {
    "V": "Verde",
    "N": "Naranja",
    "R": "Rojo",
}

# ----------------------------------------------------------
# CONSULTA: Canal, cantidad y días promedio desde Gold
# Ahora oficializacion, cancelacion y dias_despacho están
# directos en fact_aduana (ya no se necesita Silver ni una
# tabla auxiliar). canal_key se resuelve con JOIN a dim_canal.
# Filtramos es_primer_subitem = TRUE porque dias_despacho es
# un valor de cabecera del ítem que se repite en cada sub-ítem
# (igual que el FOB); sin este filtro el promedio y el conteo
# de operaciones quedarían distorsionados.
# ----------------------------------------------------------
conexion = duckdb.connect()

datos = conexion.execute(f"""
    SELECT 
        c.canal_cod AS canal,
        COUNT(*) as cantidad,
        AVG(f.dias_despacho) as dias_promedio,
        MIN(f.dias_despacho) as dias_min,
        MAX(f.dias_despacho) as dias_max
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_canal.parquet"}' c
        ON f.canal_key = c.id_canal
    WHERE f.cancelacion IS NOT NULL 
    AND f.oficializacion IS NOT NULL
    AND f.cancelacion >= f.oficializacion
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
    AND f.dias_despacho > 0
    GROUP BY c.canal_cod
    ORDER BY dias_promedio ASC
""").fetchdf()

# Mapear nombres y colores legibles a partir del código de canal
datos["nombre"] = datos["canal"].map(NOMBRES_CANAL)
datos["color"]  = datos["canal"].map(COLORES_CANAL)
datos["pct"]    = (datos["cantidad"] / datos["cantidad"].sum() * 100).round(1)

# ==========================================================
# GRÁFICO: Dos paneles
# Izquierdo → barras de días promedio por canal
# Derecho   → dona de distribución de operaciones por canal
# ==========================================================
figura, (eje_izq, eje_der) = plt.subplots(1, 2, figsize=(14, 6))
figura.suptitle(
    "Distribución de Operaciones por Canal de Control Aduanero\ny Tiempos de Despacho 2025",
    fontsize=13, fontweight="bold"
)

# --- Panel izquierdo: barras de días promedio ---
barras = eje_izq.bar(
    datos["nombre"],
    datos["dias_promedio"],
    color=datos["color"],
    edgecolor="white",
    width=0.5
)

# Etiqueta sobre cada barra con 1 decimal y sufijo días
for barra, dias in zip(barras, datos["dias_promedio"]):
    eje_izq.text(
        barra.get_x() + barra.get_width() / 2,
        barra.get_height() + 0.5,
        f"{dias:.1f} días",
        ha="center", va="bottom",
        fontsize=10, fontweight="bold"
    )

eje_izq.set_title("Días Promedio de Despacho por Canal", fontsize=11, fontweight="bold")
eje_izq.set_ylabel("Días promedio", fontsize=9)
eje_izq.set_ylim(0, datos["dias_promedio"].max() * 1.2)
eje_izq.tick_params(axis="x", labelsize=10)
eje_izq.tick_params(axis="y", labelsize=8)
eje_izq.grid(axis="y", linestyle="--", alpha=0.4)

# --- Panel derecho: dona de distribución ---
sectores, textos, porcentajes = eje_der.pie(
    datos["cantidad"],
    labels=None,
    autopct="%1.1f%%",
    colors=datos["color"].tolist(),
    startangle=90,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5, "width": 0.6},
    textprops={"fontsize": 9}
)

# Porcentajes en blanco y negrita para contraste
for pct in porcentajes:
    pct.set_fontweight("bold")
    pct.set_color("white")

# Leyenda con nombre y cantidad de operaciones
etiquetas = [
    f"Canal {row['nombre']} ({row['cantidad']:,} ops.)"
    for _, row in datos.iterrows()
]
eje_der.legend(
    etiquetas,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.15),
    fontsize=9,
    ncol=1
)
eje_der.set_title("Distribución de Operaciones por Canal", fontsize=11, fontweight="bold")

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "01_canal_despacho.png"
plt.savefig(ruta_salida, bbox_inches="tight", dpi=150)
plt.show()

print("\nResultados:")
for _, fila in datos.iterrows():
    print(f"Canal {fila['nombre']:8} | {fila['cantidad']:>10,} ops | {fila['dias_promedio']:.1f} días promedio")