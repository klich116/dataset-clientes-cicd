"""Construye el tablero de KPI's a partir del historico de calidad.

Esta es la pieza central del segundo ejercicio: convierte el archivo
data/metricas/historico_calidad.csv, que va creciendo corrida tras
corrida gracias a validate_dataset.py, en una pagina HTML que cualquier
persona del equipo de negocio puede abrir con doble clic, sin instalar
nada ni depender de quien programo el pipeline.

El tablero muestra el estado mas reciente del dataset y, debajo, una
tabla cronologica con cada corrida registrada, que funciona como
bitacora de auditoria.
"""

import csv
import sys
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = CARPETA_PROYECTO / "data" / "metricas" / "historico_calidad.csv"
RUTA_TABLERO = CARPETA_PROYECTO / "data" / "metricas" / "dashboard_kpis.html"


def cargar_historico():
    if not RUTA_HISTORICO.exists():
        print(f"Todavia no existe {RUTA_HISTORICO}. Hay que correr validate_dataset.py primero.")
        sys.exit(1)
    with open(RUTA_HISTORICO, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def construir_fila(corrida: dict) -> str:
    """Arma una fila de la tabla de trazabilidad, coloreando el resultado segun corresponda."""
    color_resultado = "#1a7f37" if corrida["resultado"] == "EXITOSA" else "#c62828"
    return (
        "<tr>"
        f"<td>{corrida['timestamp_utc']}</td>"
        f"<td>{corrida['total_registros']}</td>"
        f"<td>{corrida['registros_validos']}</td>"
        f"<td>{corrida['registros_invalidos']}</td>"
        f"<td>{corrida['pct_calidad']}%</td>"
        f"<td>{corrida['pct_consentimiento']}%</td>"
        f"<td>{corrida['duplicados_id']}</td>"
        f"<td>{corrida['duplicados_telefono']}</td>"
        f"<td>{corrida['telefonos_formato_invalido']}</td>"
        f"<td>{corrida['consentimiento_invalido']}</td>"
        f"<td style=\"color:{color_resultado}; font-weight:600;\">{corrida['resultado']}</td>"
        "</tr>"
    )


def calcular_resumen(historico: list) -> dict:
    """Saca los indicadores generales que van en las tarjetas de arriba del tablero."""
    corridas_exitosas = sum(1 for corrida in historico if corrida["resultado"] == "EXITOSA")
    return {
        "ultima_corrida": historico[-1],
        "total_corridas": len(historico),
        "corridas_exitosas": corridas_exitosas,
        "tasa_exito": round((corridas_exitosas / len(historico)) * 100, 1),
    }


def armar_pagina(historico: list) -> str:
    resumen = calcular_resumen(historico)
    ultima = resumen["ultima_corrida"]

    # La tabla se muestra de la corrida mas reciente a la mas antigua,
    # que es el orden en que alguien de negocio normalmente la revisa.
    filas_tabla = "\n".join(construir_fila(c) for c in reversed(historico))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>KPI's - Dataset de telefonos de clientes</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 0; padding: 32px; background: #f6f7f9; color: #1a1a1a; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  p.subtitulo {{ color: #555; margin-top: 0; }}
  .tarjetas {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; }}
  .tarjeta {{ background: white; border-radius: 10px; padding: 18px 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 170px; }}
  .tarjeta .valor {{ font-size: 28px; font-weight: 700; }}
  .tarjeta .etiqueta {{ font-size: 13px; color: #666; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  th, td {{ padding: 10px 12px; text-align: left; font-size: 13px; border-bottom: 1px solid #eee; }}
  th {{ background: #fafafa; color: #444; font-weight: 600; }}
  .seccion {{ margin-top: 32px; }}
</style>
</head>
<body>
  <h1>KPI's de calidad y trazabilidad - Dataset de telefonos de clientes</h1>
  <p class="subtitulo">Ultima actualizacion: {ultima['timestamp_utc']} - {resumen['total_corridas']} corrida(s) del pipeline registradas</p>

  <div class="tarjetas">
    <div class="tarjeta"><div class="valor">{ultima['pct_calidad']}%</div><div class="etiqueta">Calidad (ultima corrida)</div></div>
    <div class="tarjeta"><div class="valor">{ultima['pct_consentimiento']}%</div><div class="etiqueta">Consentimiento vigente</div></div>
    <div class="tarjeta"><div class="valor">{ultima['total_registros']}</div><div class="etiqueta">Registros en el dataset</div></div>
    <div class="tarjeta"><div class="valor">{ultima['registros_invalidos']}</div><div class="etiqueta">Registros invalidos (ultima corrida)</div></div>
    <div class="tarjeta"><div class="valor">{resumen['tasa_exito']}%</div><div class="etiqueta">Exito del pipeline ({resumen['corridas_exitosas']}/{resumen['total_corridas']})</div></div>
  </div>

  <div class="seccion">
    <h2>Historico de corridas</h2>
    <table>
      <thead>
        <tr>
          <th>Fecha (UTC)</th><th>Total</th><th>Validos</th><th>Invalidos</th>
          <th>% Calidad</th><th>% Consent.</th><th>Dup. ID</th><th>Dup. Tel.</th>
          <th>Tel. formato inv.</th><th>Consent. inv.</th><th>Resultado</th>
        </tr>
      </thead>
      <tbody>
{filas_tabla}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main():
    historico = cargar_historico()
    pagina = armar_pagina(historico)
    RUTA_TABLERO.write_text(pagina, encoding="utf-8")
    print(f"Tablero actualizado en {RUTA_TABLERO}")


if __name__ == "__main__":
    main()
