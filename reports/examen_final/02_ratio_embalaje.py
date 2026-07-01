# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Análisis 2 - Ratio de Embalaje por Rubro
# OBJETIVO: Diferenciar Kilo Bruto vs Kilo Neto por rubro para
#           visualizar el peso del embalaje como diferencia
#           entre ambos.
# ==========================================================
# Layout del dashboard:
#   Fila 1: [ KPI mayor ratio ] [ KPI promedio ] [ KPI mayor embalaje abs ]
#   Fila 2: [ Barras agrupadas Bruto vs Neto — ancho completo ]
#   Fila 3: [ Ratio % por rubro ] [ Peso embalaje absoluto ]
# ==========================================================
# Nota metodológica:
#   - es_primer_subitem = TRUE → evita duplicar kilo_bruto/neto
#     (valores de cabecera del ítem repetidos en cada sub-ítem)
#   - oficializacion 2025 → excluye arrastre administrativo
#   - kilo_bruto > 0 y kilo_neto > 0 → evita división por 0
#   - Ratio de embalaje = (kg_bruto − kg_neto) / kg_bruto × 100
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
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
AZUL     = "#2a78d6"
VERDE    = "#1baf7a"
ROJO     = "#e34948"
AMBAR    = "#eda100"
VIOLETA  = "#4a3aa7"
GRIS_BG  = "#F8F8F7"
GRIS_LN  = "#E1E0D9"
TEXTO    = "#0b0b0b"
MUTED    = "#898781"

def color_ratio(v):
    if v > 20: return ROJO
    if v > 10: return AMBAR
    return AZUL

def fmt_m(v):
    return f"{v:.1f}M" if v >= 1 else f"{v*1000:.0f}K"

# ----------------------------------------------------------
# CONSULTA GOLD
# ----------------------------------------------------------
print("Conectando a los Parquet Gold...")
con = duckdb.connect()
sql = f"""
    SELECT
        p.rubro,
        SUM(f.kilo_bruto)  AS total_kilo_bruto,
        SUM(f.kilo_neto)   AS total_kilo_neto,
        SUM(f.flete_usd)   AS total_flete_usd,
        COUNT(f.id_fact)   AS cantidad_despachos
    FROM '{carpeta_gold / "fact_aduana.parquet"}' f
    LEFT JOIN '{carpeta_gold / "dim_producto.parquet"}' p
        ON f.producto_key = p.id_producto
    WHERE p.rubro IS NOT NULL
      AND f.es_primer_subitem   = TRUE
      AND f.oficializacion     >= '2025-01-01'
      AND f.oficializacion     <= '2025-12-31'
      AND f.kilo_bruto          > 0
      AND f.kilo_neto           > 0
    GROUP BY p.rubro
    ORDER BY total_kilo_bruto DESC
"""
datos = con.execute(sql).fetchdf()
con.close()

datos["peso_embalaje_kg"]   = datos["total_kilo_bruto"] - datos["total_kilo_neto"]
datos["ratio_embalaje"]     = (datos["peso_embalaje_kg"] / datos["total_kilo_bruto"]) * 100
datos["flete_por_kg_bruto"] = datos["total_flete_usd"] / datos["total_kilo_bruto"]

# ----------------------------------------------------------
# SE ELIMINA EL FILTRO DE VOLUMEN MÍNIMO
# ----------------------------------------------------------
# Ahora se asignan todos los datos directamente para incluir rubros con menos de 1,000 kg.
datos_sig = datos.copy()

# Subsets
d_main  = datos_sig.sort_values("total_kilo_bruto", ascending=False).head(12)
d_ratio = datos_sig.sort_values("ratio_embalaje", ascending=True).tail(12)
d_peso  = datos_sig.sort_values("peso_embalaje_kg", ascending=True).tail(10)

max_ratio  = datos_sig.loc[datos_sig["ratio_embalaje"].idxmax()]
prom_ratio = datos_sig["ratio_embalaje"].mean()
max_emb    = datos_sig.loc[datos_sig["peso_embalaje_kg"].idxmax()]

# ----------------------------------------------------------
# IMPRIMIR RESUMEN
# ----------------------------------------------------------
def fmt_kg(v):
    if v >= 1_000_000:
        return f"{v/1e6:.2f}M kg"
    elif v >= 1_000:
        return f"{v/1e3:.1f}K kg"
    else:
        return f"{v:.0f} kg"

print("\n" + "=" * 65)
print("RESUMEN — RATIO DE EMBALAJE POR RUBRO")
print("=" * 65)
resumen = datos_sig.sort_values("ratio_embalaje", ascending=False).head(12)[[
    "rubro", "total_kilo_bruto", "total_kilo_neto",
    "peso_embalaje_kg", "ratio_embalaje"
]].copy()
resumen["total_kilo_bruto"] = resumen["total_kilo_bruto"].apply(fmt_kg)
resumen["total_kilo_neto"]  = resumen["total_kilo_neto"].apply(fmt_kg)
resumen["peso_embalaje_kg"] = resumen["peso_embalaje_kg"].apply(fmt_kg)
resumen["ratio_embalaje"]   = resumen["ratio_embalaje"].apply(lambda x: f"{x:.1f}%")
print(resumen.to_string(index=False))
print("=" * 65)

# ----------------------------------------------------------
# FIGURA
# ----------------------------------------------------------
fig = plt.figure(figsize=(17, 16), facecolor=GRIS_BG)
fig.suptitle(
    "Análisis de Ratio de Embalaje por Rubro — Aduanas DNIT 2025",
    fontsize=14, fontweight="bold", color=TEXTO, y=0.985
)

gs = fig.add_gridspec(
    3, 2,
    height_ratios=[0.09, 0.53, 0.38],
    hspace=0.42, wspace=0.28,
    left=0.04, right=0.97,
    top=0.96, bottom=0.04
)

ax_kpi  = fig.add_subplot(gs[0, :])
ax_main = fig.add_subplot(gs[1, :])
ax_rat  = fig.add_subplot(gs[2, 0])
ax_emb  = fig.add_subplot(gs[2, 1])

# -------------------------------------------------------
# FILA 1: KPI CARDS
# -------------------------------------------------------
ax_kpi.axis("off")
kpis = [
    (f"{max_ratio['ratio_embalaje']:.1f}%",
     f"mayor ratio: {max_ratio['rubro'][:32]}",
     ROJO),
    (f"{prom_ratio:.1f}%",
     "ratio promedio entre rubros",
     AMBAR),
    (f"{max_emb['peso_embalaje_kg']/1e6:.1f}M kg",
     f"mayor embalaje abs.: {max_emb['rubro'][:28]}",
     AZUL),
]
for i, (val, lbl, col) in enumerate(kpis):
    x = i / 3 + 0.02
    ax_kpi.add_patch(mpatches.FancyBboxPatch(
        (x, 0.04), 0.29, 0.92,
        boxstyle="round,pad=0.02",
        facecolor="white", edgecolor=col,
        linewidth=1.5, transform=ax_kpi.transAxes
    ))
    ax_kpi.text(x + 0.145, 0.66, val,
                ha="center", va="center",
                fontsize=16, fontweight="bold",
                color=col, transform=ax_kpi.transAxes)
    ax_kpi.text(x + 0.145, 0.20, lbl,
                ha="center", va="center",
                fontsize=8, color=MUTED,
                transform=ax_kpi.transAxes)

# -------------------------------------------------------
# GRÁFICO PRINCIPAL: Barras agrupadas Bruto vs Neto
# -------------------------------------------------------
ax_main.set_facecolor("white")

rubros_main = [r[:38] + "…" if len(r) > 38 else r for r in d_main["rubro"]]
n     = len(rubros_main)
x_pos = np.arange(n)
ancho = 0.38

b_bruto = d_main["total_kilo_bruto"].values / 1e6
b_neto  = d_main["total_kilo_neto"].values  / 1e6
b_emb   = b_bruto - b_neto
ratio_m = d_main["ratio_embalaje"].values

bars_bruto = ax_main.bar(x_pos - ancho/2, b_bruto, ancho,
                         color=AZUL, label="Kg bruto", zorder=3,
                         edgecolor="white", linewidth=0.5)
bars_neto  = ax_main.bar(x_pos + ancho/2, b_neto,  ancho,
                         color=VERDE, label="Kg neto",  zorder=3,
                         edgecolor="white", linewidth=0.5)

# Área de embalaje: zona entre la barra neto y la altura del bruto, sobre la barra neto
for xi, vb, vn, r in zip(x_pos, b_bruto, b_neto, ratio_m):
    # Rectángulo semitransparente del "espacio" de embalaje encima de la barra neto
    ax_main.bar(xi + ancho/2, vb - vn, ancho,
                bottom=vn,
                color=ROJO, alpha=0.18, zorder=2,
                edgecolor=ROJO, linewidth=0.6)

# Anotaciones del ratio
offset_y = (ax_main.get_ylim()[1] - ax_main.get_ylim()[0]) * 0.012
for xi, vb, r in zip(x_pos, b_bruto, ratio_m):
    ax_main.text(xi - ancho/2, vb + offset_y,
                 f"{r:.0f}%",
                 ha="center", va="bottom",
                 fontsize=7.5, color=color_ratio(r), fontweight="bold")

ax_main.set_xticks(x_pos)
ax_main.set_xticklabels(rubros_main, rotation=28, ha="right",
                        fontsize=8.5, color=TEXTO)
ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fmt_m(v)))
ax_main.set_ylabel("Peso (millones de kg)", fontsize=9, color=MUTED)
ax_main.set_title(
    "Kg bruto vs kg neto por rubro\n"
    "La zona roja sobre cada par muestra el peso del embalaje — brecha entre peso total y peso real de la mercadería",
    fontsize=11, fontweight="bold", color=TEXTO, loc="left", pad=8
)
ax_main.tick_params(axis="y", labelsize=8.5, colors=MUTED)
ax_main.grid(axis="y", linestyle=":", alpha=0.4, color=GRIS_LN, zorder=0)
ax_main.spines[["top", "right"]].set_visible(False)
ax_main.spines[["left", "bottom"]].set_color(GRIS_LN)

leyenda = [
    mpatches.Patch(color=AZUL,  label="Kg bruto (peso total transportado)"),
    mpatches.Patch(color=VERDE, label="Kg neto  (peso de la mercadería)"),
    mpatches.Patch(color=ROJO,  alpha=0.4, label="Embalaje (brecha bruto − neto)"),
]
ax_main.legend(handles=leyenda, loc="upper right",
               fontsize=8.5, framealpha=0.9, edgecolor=GRIS_LN)

# -------------------------------------------------------
# GRÁFICO 3: Ratio de embalaje (%) — barras horizontales
# -------------------------------------------------------
ax_rat.set_facecolor("white")
lbl_rat = [r[:38] + "…" if len(r) > 38 else r for r in d_ratio["rubro"]]
val_rat = d_ratio["ratio_embalaje"].values
cols_rat = [color_ratio(v) for v in val_rat]

bars_r = ax_rat.barh(lbl_rat, val_rat, color=cols_rat,
                     height=0.60, edgecolor="white", linewidth=0.5)
for b, v in zip(bars_r, val_rat):
    ax_rat.text(v + val_rat.max() * 0.02,
                b.get_y() + b.get_height() / 2,
                f"{v:.1f}%", va="center",
                fontsize=7.5, color=color_ratio(v), fontweight="bold")

ax_rat.axvline(10, color=AMBAR, linestyle="--", linewidth=0.9, alpha=0.6)
ax_rat.axvline(20, color=ROJO,  linestyle="--", linewidth=0.9, alpha=0.6)
ax_rat.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax_rat.set_xlabel("Ratio de embalaje (%)", fontsize=8, color=MUTED)
ax_rat.set_title("Ratio de embalaje por rubro\n(kg bruto − kg neto) / kg bruto × 100",
                 fontsize=10, fontweight="bold", color=TEXTO, loc="left", pad=6)
ax_rat.set_xlim(0, val_rat.max() * 1.20)
ax_rat.tick_params(axis="y", labelsize=8, colors=TEXTO)
ax_rat.tick_params(axis="x", labelsize=7.5, colors=MUTED)
ax_rat.grid(axis="x", linestyle=":", alpha=0.4, color=GRIS_LN)
ax_rat.spines[["top", "right", "left"]].set_visible(False)
ax_rat.spines["bottom"].set_color(GRIS_LN)

leyenda_r = [
    mpatches.Patch(color=AZUL,  label="< 10% ligero"),
    mpatches.Patch(color=AMBAR, label="10–20% moderado"),
    mpatches.Patch(color=ROJO,  label="> 20% intensivo"),
]
ax_rat.legend(handles=leyenda_r, loc="lower right",
              fontsize=7.5, framealpha=0.9, edgecolor=GRIS_LN)

# -------------------------------------------------------
# GRÁFICO 4: Peso absoluto de embalaje
# -------------------------------------------------------
ax_emb.set_facecolor("white")
lbl_emb = [r[:38] + "…" if len(r) > 38 else r for r in d_peso["rubro"]]
val_emb = d_peso["peso_embalaje_kg"].values / 1e6
cols_emb = [AZUL if i % 2 == 0 else VIOLETA for i in range(len(val_emb))]

bars_e = ax_emb.barh(lbl_emb, val_emb, color=cols_emb,
                     height=0.60, edgecolor="white", linewidth=0.5)
for b, v in zip(bars_e, val_emb):
    ax_emb.text(v + val_emb.max() * 0.02,
                b.get_y() + b.get_height() / 2,
                fmt_m(v), va="center", fontsize=7.5, color=MUTED)

ax_emb.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fmt_m(v)))
ax_emb.set_xlabel("Peso de embalaje (millones de kg)", fontsize=8, color=MUTED)
ax_emb.set_title("Peso absoluto de embalaje\npor rubro — impacto logístico real",
                 fontsize=10, fontweight="bold", color=TEXTO, loc="left", pad=6)
ax_emb.set_xlim(0, val_emb.max() * 1.18)
ax_emb.tick_params(axis="y", labelsize=8, colors=TEXTO)
ax_emb.tick_params(axis="x", labelsize=7.5, colors=MUTED)
ax_emb.grid(axis="x", linestyle=":", alpha=0.4, color=GRIS_LN)
ax_emb.spines[["top", "right", "left"]].set_visible(False)
ax_emb.spines["bottom"].set_color(GRIS_LN)

# -------------------------------------------------------
# NOTA METODOLÓGICA
# -------------------------------------------------------
nota = (
    "Nota metodológica: filtros aplicados — es_primer_subitem = TRUE · "
    "oficializacion entre 2025-01-01 y 2025-12-31 · kilo_bruto > 0 · kilo_neto > 0"
)
fig.text(0.5, 0.01, nota, ha="center", fontsize=7, color=MUTED, style="italic")

# -------------------------------------------------------
# EXPORTACIÓN
# -------------------------------------------------------
ruta = carpeta_graficos / "02_ratio_embalaje.png"
plt.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=GRIS_BG)
plt.show()
print(f"\n[OK] Dashboard exportado → {ruta}")

# -------------------------------------------------------
# PARA SABER...
# -------------------------------------------------------
print("\n" + "=" * 65)
print("INFORMACION IMPORTANTE")
print("=" * 65)
print(f"\n1. Rubro con MAYOR ratio de embalaje:")
print(f"    → {max_ratio['rubro']}")
print(f"    → Ratio: {max_ratio['ratio_embalaje']:.2f}%")
print(f"    → Kg bruto: {fmt_kg(max_ratio['total_kilo_bruto'])}")
print(f"    → Kg neto:  {fmt_kg(max_ratio['total_kilo_neto'])}")
print(f"    → Embalaje: {fmt_kg(max_ratio['peso_embalaje_kg'])}")
print(f"\n2. Rubro con MAYOR peso absoluto de embalaje:")
print(f"    → {max_emb['rubro']}")
print(f"    → {fmt_kg(max_emb['peso_embalaje_kg'])} de embalaje (ratio: {max_emb['ratio_embalaje']:.1f}%)")
print("=" * 65)