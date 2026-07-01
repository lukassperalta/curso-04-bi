# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Validación de Deduplicación Item/Sub-ítem
# OBJETIVO: Demostrar el impacto de la duplicación de valores
#           de cabecera del ítem en cada sub-ítem, y validar
#           que es_primer_subitem = TRUE corrige correctamente
#           los totales financieros.
# ==========================================================
# Estructura del reporte:
#   1. Caso extremo: despacho con más sub-ítems
#   2. Tabla comparativa de totales con/sin deduplicar
#   3. Gráfico de barras comparativo (visual del impacto)
# ==========================================================

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# ----------------------------------------------------------
# RUTAS
# ----------------------------------------------------------
carpeta_proyecto = Path(__file__).parent.parent.parent
carpeta_gold     = carpeta_proyecto / "data_lake" / "gold"
carpeta_graficos = Path(__file__).parent / "output_validaciones"
carpeta_graficos.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# PALETA
# ----------------------------------------------------------
COLOR_SIN  = "#e74c3c"   # Rojo — sin deduplicar (incorrecto)
COLOR_CON  = "#2ecc71"   # Verde — con deduplicar (correcto)
GRIS_BG    = "#F8F8F7"
MUTED      = "#898781"
TEXTO      = "#0b0b0b"

con = duckdb.connect()

# ==========================================================
# 1. CASO EXTREMO: despacho con más sub-ítems
# ==========================================================
print("\n" + "=" * 65)
print("1. CASO EXTREMO — DESPACHO CON MÁS SUB-ÍTEMS")
print("=" * 65)

caso_extremo = con.execute(f"""
    SELECT
        despacho_id,
        item_nro,
        COUNT(*) as cantidad_subitems,
        MAX(fob_usd) as fob_real,
        SUM(fob_usd) as fob_inflado
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
    GROUP BY despacho_id, item_nro
    ORDER BY cantidad_subitems DESC
    LIMIT 5
""").fetchdf()

print("\nTop 5 ítems con más sub-ítems:")
print(f"{'Despacho':<25} {'Ítem':>5} {'Sub-ítems':>10} {'FOB Real':>20} {'FOB Inflado (sin dedup)':>25} {'Factor':>8}")
print("-" * 95)
for _, fila in caso_extremo.iterrows():
    factor = fila['fob_inflado'] / fila['fob_real'] if fila['fob_real'] > 0 else 0
    print(f"{fila['despacho_id']:<25} {int(fila['item_nro']):>5} {int(fila['cantidad_subitems']):>10,} "
          f"${fila['fob_real']:>18,.2f} ${fila['fob_inflado']:>23,.2f} {factor:>7.0f}x")

# Tomar el caso más extremo para el ejemplo
peor_caso = caso_extremo.iloc[0]
print(f"\n→ Caso más extremo: despacho {peor_caso['despacho_id']}, ítem {int(peor_caso['item_nro'])}")
print(f"  FOB real del ítem:          $ {peor_caso['fob_real']:>20,.2f}")
print(f"  FOB sin deduplicar:         $ {peor_caso['fob_inflado']:>20,.2f}")
print(f"  Factor de inflación:          {peor_caso['fob_inflado']/peor_caso['fob_real']:.0f}x")
print(f"  Sub-ítems en ese ítem:        {int(peor_caso['cantidad_subitems']):,}")

# ==========================================================
# 2. TABLA COMPARATIVA DE TOTALES
# ==========================================================
print("\n" + "=" * 65)
print("2. TABLA COMPARATIVA — CON vs SIN DEDUPLICACIÓN")
print("=" * 65)

# Sin deduplicar (todas las filas)
sin_dedup = con.execute(f"""
    SELECT
        COUNT(*) as operaciones,
        SUM(fob_usd) as fob_total,
        SUM(impuesto_iva_real_usd) as iva_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
    WHERE oficializacion >= '2025-01-01'
    AND oficializacion <= '2025-12-31'
""").fetchone()

# Con deduplicar (es_primer_subitem = TRUE)
con_dedup = con.execute(f"""
    SELECT
        COUNT(*) as operaciones,
        SUM(fob_usd) as fob_total,
        SUM(impuesto_iva_real_usd) as iva_total
    FROM '{carpeta_gold / "fact_aduana.parquet"}'
    WHERE es_primer_subitem = TRUE
    AND oficializacion >= '2025-01-01'
    AND oficializacion <= '2025-12-31'
""").fetchone()

print(f"\n{'Métrica':<30} {'SIN deduplicar':>22} {'CON deduplicar':>22} {'Factor inflación':>18}")
print("-" * 94)
print(f"{'Operaciones (filas)':<30} {sin_dedup[0]:>22,} {con_dedup[0]:>22,} {sin_dedup[0]/con_dedup[0]:>17.2f}x")
print(f"{'FOB Total (USD)':<30} ${sin_dedup[1]:>21,.2f} ${con_dedup[1]:>21,.2f} {sin_dedup[1]/con_dedup[1]:>17.2f}x")
print(f"{'IVA Total (USD)':<30} ${sin_dedup[2]:>21,.2f} ${con_dedup[2]:>21,.2f} {sin_dedup[2]/con_dedup[2]:>17.2f}x")
print(f"\n→ Sin deduplicar, el FOB total queda inflado {sin_dedup[1]/con_dedup[1]:.2f}x respecto al valor real")
print(f"→ Promedio de sub-ítems por ítem: {sin_dedup[0]/con_dedup[0]:.2f}")

# ==========================================================
# 3. GRÁFICO COMPARATIVO
# ==========================================================
fig, ejes = plt.subplots(1, 3, figsize=(16, 6), facecolor=GRIS_BG)
fig.suptitle(
    "Impacto de la Deduplicación por Ítem/Sub-ítem — Aduanas DNIT 2025\n"
    "Comparación de totales con y sin aplicar es_primer_subitem = TRUE",
    fontsize=13, fontweight="bold", color=TEXTO, y=1.02
)

metricas = [
    ("Operaciones", float(sin_dedup[0]), float(con_dedup[0]), "unidades", 1e6, "mill."),
    ("FOB Total (USD)", float(sin_dedup[1]), float(con_dedup[1]), "USD", 1e9, "mil M"),
    ("IVA Total (USD)", float(sin_dedup[2]), float(con_dedup[2]), "USD", 1e9, "mil M"),
]

for eje, (titulo, val_sin, val_con, unidad, divisor, sufijo) in zip(ejes, metricas):
    eje.set_facecolor("white")

    barras = eje.bar(
        ["Sin\ndeduplicar", "Con\ndeduplicar"],
        [val_sin / divisor, val_con / divisor],
        color=[COLOR_SIN, COLOR_CON],
        width=0.5,
        edgecolor="white"
    )

    # Etiquetas sobre cada barra
    for barra, val in zip(barras, [val_sin, val_con]):
        eje.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + (val_sin / divisor) * 0.02,
            f"{val / divisor:.2f} {sufijo}",
            ha="center", va="bottom",
            fontsize=10, fontweight="bold", color=TEXTO
        )

    # Factor de inflación como anotación
    factor = val_sin / val_con
    eje.text(
        0.5, 0.92,
        f"Factor inflación: {factor:.2f}x",
        ha="center", transform=eje.transAxes,
        fontsize=9, color=COLOR_SIN,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffeaea", edgecolor=COLOR_SIN)
    )

    eje.set_title(titulo, fontsize=11, fontweight="bold", color=TEXTO, pad=10)
    eje.set_ylabel(f"({sufijo})", fontsize=8, color=MUTED)
    eje.tick_params(axis="x", labelsize=10)
    eje.tick_params(axis="y", labelsize=8, colors=MUTED)
    eje.grid(axis="y", linestyle=":", alpha=0.4)
    eje.spines[["top", "right"]].set_visible(False)

# Nota metodológica
nota = (
    "El portal DNIT documenta explícitamente: 'Los valores pueden repetirse de forma proporcional "
    "a la cantidad de Items y Sub Items.' — es_primer_subitem = TRUE corrige este comportamiento."
)
fig.text(0.5, -0.02, nota, ha="center", fontsize=8, color=MUTED, style="italic")

plt.tight_layout()
ruta = carpeta_graficos / "validacion_deduplicacion.png"
plt.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=GRIS_BG)
plt.show()
print(f"\n[OK] Gráfico exportado → {ruta}")
print("=" * 65)

con.close()