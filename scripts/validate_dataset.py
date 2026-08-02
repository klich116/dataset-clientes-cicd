"""Revisa el dataset de telefonos de clientes antes de que avance al despliegue.

Este script corre como parte de la etapa de integracion continua del
pipeline: se ejecuta en cada push y en cada pull request, y su salida
decide si el cambio puede seguir hacia produccion o si se detiene ahi
mismo. Ademas deja constancia de cada corrida en un historico de
metricas, que es lo que despues alimenta el tablero de KPI's.
"""

import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DATASET = CARPETA_PROYECTO / "data" / "clientes_telefonos.csv"
CARPETA_METRICAS = CARPETA_PROYECTO / "data" / "metricas"
RUTA_HISTORICO = CARPETA_METRICAS / "historico_calidad.csv"

COLUMNAS_OBLIGATORIAS = ["cliente_id", "nombre", "telefono", "pais", "consentimiento", "fecha_actualizacion"]

# El formato E.164 es el estandar internacional para numeros de telefono:
# un signo mas, el codigo de pais y el numero, sin espacios ni guiones.
PATRON_TELEFONO = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass
class ErrorFila:
    """Representa un problema encontrado en una fila concreta del CSV."""
    numero_fila: int
    categoria: str
    detalle: str


def leer_dataset(ruta: Path):
    """Abre el archivo CSV y devuelve el encabezado junto con sus filas."""
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        return lector.fieldnames, list(lector)


def revisar_filas(encabezado, filas):
    """Aplica cada regla de calidad fila por fila.

    Devuelve la lista completa de errores encontrados y el conjunto de
    filas que tuvieron al menos uno, que es lo que luego se usa para
    separar registros validos de invalidos.
    """
    columnas_faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in (encabezado or [])]
    if columnas_faltantes:
        # No tiene caso seguir revisando fila por fila si el archivo ni
        # siquiera tiene la estructura minima esperada.
        error = ErrorFila(0, "columnas_faltantes", f"Faltan columnas: {columnas_faltantes}")
        return [error], set()

    errores = []
    filas_con_problema = set()
    identificadores_usados = set()
    telefonos_usados = set()

    for posicion, fila in enumerate(filas, start=1):
        numero_fila = posicion + 1  # la fila 1 del archivo es el encabezado
        cliente_id = fila.get("cliente_id", "").strip()
        nombre = fila.get("nombre", "").strip()
        telefono = fila.get("telefono", "").strip()
        consentimiento = fila.get("consentimiento", "").strip().lower()

        if not cliente_id:
            errores.append(ErrorFila(numero_fila, "id_vacio", "cliente_id vacio"))
            filas_con_problema.add(posicion)

        if not nombre:
            errores.append(ErrorFila(numero_fila, "nombre_vacio", "nombre vacio"))
            filas_con_problema.add(posicion)

        # El telefono tiene dos formas de fallar: que no venga, o que
        # venga con un formato que ningun sistema de mensajeria aceptaria.
        if not telefono:
            errores.append(ErrorFila(numero_fila, "telefono_vacio", "telefono vacio"))
            filas_con_problema.add(posicion)
        elif not PATRON_TELEFONO.match(telefono):
            errores.append(ErrorFila(numero_fila, "telefono_formato_invalido", f"'{telefono}' no cumple el formato E.164"))
            filas_con_problema.add(posicion)

        if consentimiento not in ("true", "false"):
            errores.append(ErrorFila(numero_fila, "consentimiento_invalido", f"valor '{fila.get('consentimiento')}' no es true/false"))
            filas_con_problema.add(posicion)

        if cliente_id and cliente_id in identificadores_usados:
            errores.append(ErrorFila(numero_fila, "id_duplicado", f"cliente_id '{cliente_id}' ya aparecio antes"))
            filas_con_problema.add(posicion)
        identificadores_usados.add(cliente_id)

        if telefono and telefono in telefonos_usados:
            errores.append(ErrorFila(numero_fila, "telefono_duplicado", f"telefono '{telefono}' ya aparecio antes"))
            filas_con_problema.add(posicion)
        telefonos_usados.add(telefono)

    return errores, filas_con_problema


def resumir_en_metricas(filas, errores, filas_con_problema):
    """Traduce la lista de errores en los numeros que van al historico de KPI's."""
    total = len(filas)
    invalidos = len(filas_con_problema)
    validos = total - invalidos
    por_categoria = Counter(e.categoria for e in errores)

    registros_con_consentimiento = sum(
        1 for f in filas if f.get("consentimiento", "").strip().lower() == "true"
    )

    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_registros": total,
        "registros_validos": validos,
        "registros_invalidos": invalidos,
        "pct_calidad": round((validos / total) * 100, 1) if total else 0.0,
        "pct_consentimiento": round((registros_con_consentimiento / total) * 100, 1) if total else 0.0,
        "duplicados_id": por_categoria.get("id_duplicado", 0),
        "duplicados_telefono": por_categoria.get("telefono_duplicado", 0),
        "telefonos_formato_invalido": por_categoria.get("telefono_formato_invalido", 0),
        "campos_vacios": por_categoria.get("id_vacio", 0) + por_categoria.get("nombre_vacio", 0) + por_categoria.get("telefono_vacio", 0),
        "consentimiento_invalido": por_categoria.get("consentimiento_invalido", 0),
        "total_errores": len(errores),
        "resultado": "EXITOSA" if not errores else "FALLIDA",
    }


def registrar_en_historico(metricas: dict):
    """Agrega una fila mas al historico de calidad, sin sobrescribir lo ya guardado.

    Esto se hace pase o falle la validacion: el objetivo del historico es
    dar trazabilidad de todos los intentos, no solo de los que llegaron
    a produccion.
    """
    CARPETA_METRICAS.mkdir(parents=True, exist_ok=True)
    archivo_ya_existia = RUTA_HISTORICO.exists()

    with open(RUTA_HISTORICO, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(metricas.keys()))
        if not archivo_ya_existia:
            escritor.writeheader()
        escritor.writerow(metricas)


def main():
    if not RUTA_DATASET.exists():
        print(f"No se encontro el dataset en {RUTA_DATASET}")
        sys.exit(1)

    encabezado, filas = leer_dataset(RUTA_DATASET)
    if not filas:
        print("El dataset esta vacio, no hay nada que validar")
        sys.exit(1)

    errores, filas_con_problema = revisar_filas(encabezado, filas)

    metricas = resumir_en_metricas(filas, errores, filas_con_problema)
    registrar_en_historico(metricas)

    if errores:
        print(f"Validacion fallida, se encontraron {len(errores)} problema(s):")
        for error in errores:
            print(f"  - fila {error.numero_fila}: {error.detalle}")
        sys.exit(1)

    print(f"Validacion exitosa: {len(filas)} registros cumplen las reglas de calidad")
    sys.exit(0)


if __name__ == "__main__":
    main()
