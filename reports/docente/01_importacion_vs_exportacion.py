# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Distribución Exportaciones vs Importaciones
# OBJETIVO: Comparar cantidad de ítems y FOB total entre
#           exportaciones e importaciones mediante pie charts
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
# COLORES ESPECÍFICOS POR TIPO DE OPERACIÓN
# Verde para exportación, rosa para importación
# ----------------------------------------------------------
COLOR_EXPORTACION = "#016948"
COLOR_IMPORTACION = "#B44365"

# ----------------------------------------------------------
# CONSULTA: Operación y FOB desde Gold
# JOIN con dim_operacion para obtener la descripción
# (EXPORTACION / IMPORTACION) en lugar del ID numérico
# ----------------------------------------------------------
conexion = duckdb.connect()

consulta_sql = f"""
    SELECT
        o.operacion_desc AS operacion,
        f.fob_real_usd
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_operacion.parquet"}' o
        ON f.operacion_key = o.id_operacion
"""
datos = conexion.execute(consulta_sql).fetchdf()

cantidad_registros = len(datos)
resumen_operaciones = datos["operacion"].value_counts().to_dict()

print(f"datos cargados: {cantidad_registros} registros")
print(f"Distribución: {resumen_operaciones}")

# ==========================================================
# GRÁFICO: Dos pie charts lado a lado
# Izquierda → distribución por cantidad de ítems
# Derecha   → distribución por valor FOB total (USD)
# El color se asigna dinámicamente buscando "EXP" en
# la etiqueta, compatible con cualquier variante del nombre.
# ==========================================================
figura, ejes = plt.subplots(1, 2, figsize=(10, 5))
figura.suptitle(
    "Distribución: Exportaciones Vs. Importaciones",
    fontsize=13, fontweight="bold"
)

cantidad_por_operacion = datos["operacion"].value_counts()
fob_por_operacion      = datos.groupby("operacion")["fob_real_usd"].sum()

pares = [
    (ejes[0], cantidad_por_operacion, "Cantidad de Items"),
    (ejes[1], fob_por_operacion,      "FOB Total (USD)")
]

for eje, serie, titulo_sub in pares:
    # Asignación dinámica de color por tipo de operación
    color_sector = [
        COLOR_EXPORTACION if "EXP" in etiqueta else COLOR_IMPORTACION
        for etiqueta in serie.index
    ]

    sectores, textos, porcentajes = eje.pie(
        serie,
        labels     = serie.index,
        autopct    = "%1.1f%%",
        colors     = color_sector,
        startangle = 90,
        wedgeprops = {"edgecolor": "white", "linewidth": 1.5},
        textprops  = {"fontsize": 9},
    )

    # Porcentajes en blanco y negrita para contraste
    for texto_pct in porcentajes:
        texto_pct.set_fontsize(9)
        texto_pct.set_color("white")
        texto_pct.set_fontweight("bold")
    eje.set_title(titulo_sub, fontsize=10, pad=10)

# ----------------------------------------------------------
# EXPORTACIÓN
# ----------------------------------------------------------
plt.tight_layout()
ruta_salida = carpeta_graficos / "Importación vs exportación.png"
plt.savefig(ruta_salida, bbox_inches="tight")
plt.show()