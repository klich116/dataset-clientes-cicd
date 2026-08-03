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
from datetime import datetime, timedelta, timezone
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
DATASET_ORIGEN = CARPETA_PROYECTO / "data" / "clientes_telefonos.csv"
CARPETA_PRODUCCION = CARPETA_PROYECTO / "data" / "produccion"
REGISTRO_DESPLIEGUES = CARPETA_PRODUCCION / "log_despliegues.csv"

# Colombia no tiene horario de verano, asi que su diferencia con UTC es
# siempre de 5 horas. Se deja como zona horaria fija en vez de depender
# de una libreria externa de zonas horarias.
ZONA_COLOMBIA = timezone(timedelta(hours=-5))


def contar_registros(ruta: Path) -> int:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return sum(1 for _ in csv.DictReader(archivo))


def copiar_a_produccion(marca_tiempo: str) -> Path:
    """Guarda una copia del dataset con marca de tiempo, para no perder versiones anteriores."""
    CARPETA_PRODUCCION.mkdir(parents=True, exist_ok=True)
    destino = CARPETA_PRODUCCION / f"clientes_telefonos_{marca_tiempo}.csv"
    shutil.copy2(DATASET_ORIGEN, destino)
    return destino


def dejar_constancia(marca_tiempo: str, destino: Path, total_registros: int):
    """Anota el despliegue en el log, para poder auditar despues cuando y cuanto se publico.

    Usa la misma marca de tiempo con la que se nombro el archivo, para
    que el nombre del archivo y la fila del log siempre coincidan.

    Nota sobre el historial: las primeras corridas de este proyecto
    guardaban la marca de tiempo en UTC con sufijo "Z"
    (20260802T160239Z) y la columna se llamaba "timestamp_utc". Despues
    cambie a hora de Colombia sin el sufijo (2026-08-02_17-16-12), que
    es el formato que se usa desde entonces. No reescribo los nombres
    de archivo ni las filas viejas del log para no alterar un registro
    de auditoria real; el encabezado de la columna si se actualizo a
    "fecha_hora" para reflejar el formato vigente. Si algun dia se
    necesita, la forma de distinguir una marca vieja de una nueva es
    que las viejas terminan en "Z" y las nuevas no.
    """
    log_ya_existia = REGISTRO_DESPLIEGUES.exists()
    with open(REGISTRO_DESPLIEGUES, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if not log_ya_existia:
            escritor.writerow(["fecha_hora", "archivo", "total_registros"])
        escritor.writerow([marca_tiempo, destino.name, total_registros])


def main():
    if not DATASET_ORIGEN.exists():
        print(f"No se encontro el dataset validado en {DATASET_ORIGEN}")
        sys.exit(1)

    marca_tiempo = datetime.now(ZONA_COLOMBIA).strftime("%Y-%m-%d_%H-%M-%S")
    destino = copiar_a_produccion(marca_tiempo)
    total_registros = contar_registros(DATASET_ORIGEN)
    dejar_constancia(marca_tiempo, destino, total_registros)

    print(f"Despliegue completado: {total_registros} registros publicados en {destino}")


if __name__ == "__main__":
    main()
