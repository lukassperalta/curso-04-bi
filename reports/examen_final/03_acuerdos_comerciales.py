# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Análisis 3 - Impacto de Acuerdos Comerciales en el FOB
# OBJETIVO: Visualizar la participación de cada acuerdo comercial
#           (MERCOSUR, AAP.CE 74, Sin acuerdo, etc.) en el valor
#           total FOB exportado e importado durante 2025
# ==========================================================
# Nota metodológica:
#   - es_primer_subitem = TRUE → evita duplicar fob_usd
#   - oficializacion 2025 → excluye arrastre administrativo
#   - acuerdo_key IS NULL → registros sin acuerdo en el CSV
#     (campo vacío, distinto de "Sin Acuerdo" explícito),
#     se agrupan bajo "Sin Acuerdo" con COALESCE
#   - Acuerdos con participación < 1% del total se agrupan
#     en "Otros" para no sobrecargar el gráfico
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ----------------------------------------------------------
# RUTAS
# ----------------------------------------------------------
carpeta_proyecto = Path(__file__).parent.parent.parent
carpeta_gold     = carpeta_proyecto / "data_lake" / "gold"
carpeta_graficos = Path(__file__).parent.parent / "output_images" / "examen_final"
carpeta_graficos.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# PALETA
# ----------------------------------------------------------
PALETA_COLORES = [
    "#012169",
    "#d42858",
    "#009EFF",
    "#25989A",
    "#A0C4FF",
    "#BDB2FF",
    "#FFC6FF",
    "#FFADAD",
    "#FFD6A5",
    "#CAFFBF",
]

GRIS_BG = "#F8F8F7"
MUTED   = "#898781"
TEXTO   = "#0b0b0b"

# ----------------------------------------------------------
# CONSULTA GOLD
# ----------------------------------------------------------
print("Conectando a los Parquet Gold...")
con = duckdb.connect()

sql = f"""
    SELECT
        o.operacion_desc AS operacion,
        COALESCE(a.acuerdo_desc, 'Sin Acuerdo') AS acuerdo,
        SUM(f.fob_usd) AS fob_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_operacion.parquet"}' o
        ON f.operacion_key = o.id_operacion
    LEFT JOIN '{carpeta_gold / "dim_acuerdo.parquet"}' a
        ON f.acuerdo_key = a.id_acuerdo
    WHERE f.es_primer_subitem = TRUE
    AND f.oficializacion >= '2025-01-01'
    AND f.oficializacion <= '2025-12-31'
    GROUP BY o.operacion_desc, COALESCE(a.acuerdo_desc, 'Sin Acuerdo')
    ORDER BY operacion, fob_total DESC
"""
datos = con.execute(sql).fetchdf()
con.close()

# ----------------------------------------------------------
# FUNCIÓN: Agrupar acuerdos con < 1% en "Otros"
# ----------------------------------------------------------
def agrupar_otros(df_op):
    import pandas as pd
    total = df_op["fob_total"].sum()
    df_op = df_op.copy()
    df_op["pct"] = df_op["fob_total"] / total * 100
    principales = df_op[df_op["pct"] >= 1].copy()
    otros_fob   = df_op[df_op["pct"] < 1]["fob_total"].sum()
    if otros_fob > 0:
        otros_row = pd.DataFrame([{
            "acuerdo": "Otros acuerdos",
            "fob_total": otros_fob,
            "pct": otros_fob / total * 100
        }])
        principales = pd.concat([principales, otros_row], ignore_index=True)
    return principales.sort_values("fob_total", ascending=False)

# Separar por operación
df_imp = datos[datos["operacion"] == "IMPORTACION"].rename(columns={"acuerdo": "acuerdo"})
df_exp = datos[datos["operacion"] == "EXPORTACION"].rename(columns={"acuerdo": "acuerdo"})

df_imp_g = agrupar_otros(df_imp[["acuerdo", "fob_total"]])
df_exp_g = agrupar_otros(df_exp[["acuerdo", "fob_total"]])

# ----------------------------------------------------------
# IMPRIMIR RESUMEN
# ----------------------------------------------------------
print("\n" + "=" * 65)
print("IMPACTO DE ACUERDOS COMERCIALES EN EL FOB 2025")
print("=" * 65)

for operacion, df_g in [("IMPORTACION", df_imp_g), ("EXPORTACION", df_exp_g)]:
    print(f"\n  {operacion}:")
    for _, fila in df_g.iterrows():
        print(f"    {fila['acuerdo']:.<40} $ {fila['fob_total']:>18,.2f}  ({fila['pct']:.1f}%)")

print("=" * 65)

# ----------------------------------------------------------
# GRÁFICO: 2 donas lado a lado (Importación | Exportación)
# ----------------------------------------------------------
fig, (eje_imp, eje_exp) = plt.subplots(1, 2, figsize=(16, 7), facecolor=GRIS_BG)
fig.suptitle(
    "Impacto de Acuerdos Comerciales en el FOB — Aduanas DNIT 2025",
    fontsize=14, fontweight="bold", color=TEXTO, y=1.01
)

def graficar_dona(eje, df_g, titulo, operacion):
    n = len(df_g)
    colores = PALETA_COLORES[:n]

    sectores, textos, porcentajes = eje.pie(
        df_g["fob_total"],
        labels=None,
        autopct="%1.1f%%",
        colors=colores,
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5, "width": 0.6},
        textprops={"fontsize": 9},
        pctdistance=0.75
    )

    for pct in porcentajes:
        pct.set_fontweight("bold")
        pct.set_color("white")
        pct.set_fontsize(8.5)

    # FOB total en el centro de la dona
    total = df_g["fob_total"].sum()
    eje.text(0, 0, f"${total/1e9:.1f}\nmil M",
             ha="center", va="center",
             fontsize=11, fontweight="bold", color=TEXTO)

    eje.set_title(titulo, fontsize=12, fontweight="bold",
                  color=TEXTO, pad=15)

    # Leyenda con nombre y monto
    etiquetas = [
        f"{row['acuerdo']} — ${row['fob_total']/1e9:.2f} mil M ({row['pct']:.1f}%)"
        for _, row in df_g.iterrows()
    ]
    eje.legend(
        [mpatches.Patch(color=c) for c in colores],
        etiquetas,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.28),
        fontsize=8,
        ncol=1,
        framealpha=0.9
    )

graficar_dona(eje_imp, df_imp_g, "Importación", "IMPORTACION")
graficar_dona(eje_exp, df_exp_g, "Exportación", "EXPORTACION")

# Nota metodológica
nota = (
    "Nota metodológica: es_primer_subitem = TRUE · "
    "oficializacion 2025-01-01 a 2025-12-31 · "
    "acuerdos con participación < 1% agrupados en 'Otros acuerdos' · "
    "registros sin acuerdo en el CSV agrupados en 'Sin Acuerdo'"
)
fig.text(0.5, -0.02, nota, ha="center", fontsize=7, color=MUTED, style="italic")

plt.tight_layout()
ruta = carpeta_graficos / "03_acuerdos_comerciales.png"
plt.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=GRIS_BG)
plt.show()
print(f"\n[OK] Gráfico exportado → {ruta}")