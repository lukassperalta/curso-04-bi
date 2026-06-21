# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Participación por Puesto Aduanero
# OBJETIVO: Visualizar el peso de cada aduana en el FOB total
#           mediante un gráfico de dona
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
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
# Usa más colores que los otros gráficos porque la dona
# puede tener hasta 5 sectores distintos.
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

# ----------------------------------------------------------
# CONSULTA: FOB por aduana desde Gold
# JOIN con dim_aduana para obtener el nombre del puesto.
# Top 5 aduanas con mayor FOB acumulado.
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
        a.aduana_nombre,
        SUM(f.fob_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_aduana.parquet"}' a
        ON f.aduana_key = a.id_aduana
    WHERE a.aduana_nombre IS NOT NULL
    AND f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
    GROUP BY a.aduana_nombre
    ORDER BY fob_total DESC
""").fetchdf()

# Top 5 aduanas con mayor participación
fob_por_aduana = datos.head(5)

# ==========================================================
# GRÁFICO: Dona (pie con hueco central)
# width=0.6 en wedgeprops genera el hueco de la dona.
# labels=None evita texto superpuesto — se usa leyenda lateral.
# Porcentajes en blanco y bold para contraste sobre colores.
# ==========================================================
figura, eje = plt.subplots(figsize=(8, 5))
figura.suptitle(
    "Participación por Puesto Aduanero",
    fontsize=13, fontweight="bold"
)

sectores, textos, porcentajes = eje.pie(
    fob_por_aduana["fob_total"],
    labels=None,
    autopct="%1.0f%%",
    colors=PALETA_COLORES[:len(fob_por_aduana)],
    startangle=90,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5, "width": 0.6},
    textprops={"fontsize": 9},
)

# Porcentajes en negrita para mejor legibilidad
for texto_pct in porcentajes:
    texto_pct.set_fontsize(9)
    texto_pct.set_fontweight("bold")

# Leyenda lateral con nombres de las aduanas
eje.legend(
    fob_por_aduana["aduana_nombre"],
    loc="center left",
    bbox_to_anchor=(1, 0.5),
    fontsize=9
)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Participacion por Aduana.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()