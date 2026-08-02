"""Publica el dataset ya validado en el ambiente de produccion.

Corresponde a la etapa de despliegue continuo del pipeline: solo se
ejecuta si la validacion previa fue exitosa y el cambio ya esta en la
rama principal del repositorio. En un escenario real este paso no
copiaria un archivo, sino que cargaria el dataset a una base de datos,
a un data warehouse o a un CRM mediante su API. Aqui se simula guardando
una copia fechada en una carpeta local, junto con un registro de cada
despliegue realizado.
"""

import csv
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
DATASET_ORIGEN = CARPETA_PROYECTO / "data" / "clientes_telefonos.csv"
CARPETA_PRODUCCION = CARPETA_PROYECTO / "data" / "produccion"
REGISTRO_DESPLIEGUES = CARPETA_PRODUCCION / "log_despliegues.csv"


def contar_registros(ruta: Path) -> int:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return sum(1 for _ in csv.DictReader(archivo))


def copiar_a_produccion() -> Path:
    """Guarda una copia del dataset con marca de tiempo, para no perder versiones anteriores."""
    CARPETA_PRODUCCION.mkdir(parents=True, exist_ok=True)
    marca_tiempo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = CARPETA_PRODUCCION / f"clientes_telefonos_{marca_tiempo}.csv"
    shutil.copy2(DATASET_ORIGEN, destino)
    return destino


def dejar_constancia(destino: Path, total_registros: int):
    """Anota el despliegue en el log, para poder auditar despues cuando y cuanto se publico."""
    log_ya_existia = REGISTRO_DESPLIEGUES.exists()
    with open(REGISTRO_DESPLIEGUES, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if not log_ya_existia:
            escritor.writerow(["timestamp_utc", "archivo", "total_registros"])
        escritor.writerow([datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), destino.name, total_registros])


def main():
    if not DATASET_ORIGEN.exists():
        print(f"No se encontro el dataset validado en {DATASET_ORIGEN}")
        sys.exit(1)

    destino = copiar_a_produccion()
    total_registros = contar_registros(DATASET_ORIGEN)
    dejar_constancia(destino, total_registros)

    print(f"Despliegue completado: {total_registros} registros publicados en {destino}")


if __name__ == "__main__":
    main()
