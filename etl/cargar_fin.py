# ==========================================================
# PROYECTO: BI - DNIT (Aduanas)
# SCRIPT:   Pipeline Integral de Datos
# OBJETIVO: Ejecutar todos los pasos del ETL en orden,
#           desde el reseteo hasta la exportación a Gold
# ==========================================================
# Uso: python cargar_fin.py
# Detiene el pipeline automáticamente si algún paso falla.
# ==========================================================

import subprocess
import sys
import time

# ----------------------------------------------------------
# FUNCIONES AUXILIARES DE LOG
# ----------------------------------------------------------

def sep(msg, char="-"):
    print(char * len(msg))

def log(msg, char="-"):
    print(msg)
    sep(msg, char)

def header(msg):
    sep(msg, "=")
    print(msg)
    sep(msg, "=")

# ----------------------------------------------------------
# FUNCIÓN: Ejecutar un script del pipeline
# Captura stdout/stderr y reporta tiempo de ejecución.
# Retorna True si el script terminó sin errores.
# ----------------------------------------------------------
def ejecutar_script(nombre_script, ruta_archivo):
    log(f"Ejecutando: {nombre_script}...")
    inicio = time.time()

    try:
        resultado = subprocess.run(
            [sys.executable, ruta_archivo],
            check=True,
            capture_output=True,
            text=True
        )
        duracion = time.time() - inicio
        minutos  = int(duracion // 60)
        segundos = int(duracion % 60)

        msg = f"[OK] {nombre_script} — {minutos}m {segundos}s"
        log(msg)

        # Si es la auditoría, imprimimos su salida completa
        if "Auditoría" in nombre_script:
            print(resultado.stdout)

    except subprocess.CalledProcessError as e:
        log(f"[ERROR] {nombre_script}:")
        print(e.stderr)
        return False

    return True

# ----------------------------------------------------------
# PIPELINE: Definición de pasos en orden de ejecución
# Cada paso depende del anterior — si uno falla, se detiene.
# ----------------------------------------------------------
def main():
    header("INICIANDO PIPELINE INTEGRAL DE DATOS - ADUANAS DNIT")

    scripts = [
        ("1. Reseteo de Estructura (DDL)",  r"sql\01_crear_tablas.py"),
        ("2. Carga a Staging (Silver)",     r"etl\02_etl_cargar_staging.py"),
        ("3. Procesamiento de Dimensiones", r"etl\03_etl_dimensiones.py"),
        ("4. Carga de Fact Table (Gold)",   r"etl\04_etl_fact_aduana.py"),
        ("5. Estructuras OLAP",             r"sql\05_olap_analitico.py"),
        ("6. Exportación Modelo Estrella",  r"etl\06_exportar_modelo_estrella.py"),
        ("7. Auditoría de Datos Final",     r"sql\07_verificar_creacion_tablas.py"),
    ]

    pipeline_inicio = time.time()
    resultados = []

    for nombre, ruta in scripts:
        exito = ejecutar_script(nombre, ruta)
        resultados.append((nombre, exito))

        if not exito:
            log("PIPELINE DETENIDO POR ERROR — revisar el paso anterior.")
            break

    # ----------------------------------------------------------
    # RESUMEN FINAL
    # Muestra el estado de cada paso y el tiempo total
    # ----------------------------------------------------------
    duracion_total = time.time() - pipeline_inicio
    minutos  = int(duracion_total // 60)
    segundos = int(duracion_total % 60)

    print()
    header("RESUMEN DEL PIPELINE")

    for nombre, exito in resultados:
        estado = "✔ OK" if exito else "✘ FALLÓ"
        print(f"   {estado}  {nombre}")

    print()
    log(f"Tiempo total de ejecución: {minutos} min {segundos} seg.")
    header("PIPELINE FINALIZADO")

if __name__ == "__main__":
    main()