"""Construye el tablero de KPI's a partir del histórico de calidad.

Esta es la pieza central del segundo ejercicio: convierte el archivo
data/metricas/historico_calidad.csv, que va creciendo corrida tras
corrida gracias a validate_dataset.py, en una página HTML que cualquier
persona del equipo de negocio puede abrir con doble clic o consultar
publicada en GitHub Pages, sin instalar nada ni depender de quien
programó el pipeline.

El tablero muestra el estado más reciente del dataset, la tendencia de
calidad en el tiempo y, debajo, una tabla cronológica con cada corrida
registrada, que funciona como bitácora de auditoría.
"""

import csv
import sys
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = CARPETA_PROYECTO / "data" / "metricas" / "historico_calidad.csv"
RUTA_TABLERO = CARPETA_PROYECTO / "data" / "metricas" / "dashboard_kpis.html"

# Paleta del tablero: fondo casi negro con acentos en cian y ámbar, en vez
# del clásico blanco-con-sombritas de los dashboards genéricos. El cian
# marca lo que va bien, el ámbar lo que vale la pena vigilar.
COLOR_FONDO = "#0b0e14"
COLOR_SUPERFICIE = "#12161f"
COLOR_BORDE = "rgba(255,255,255,0.08)"
COLOR_TEXTO = "#e6e8ec"
COLOR_TEXTO_TENUE = "#8b93a3"
COLOR_EXITO = "#5eead4"
COLOR_FALLA = "#fb7185"


def cargar_historico():
    if not RUTA_HISTORICO.exists():
        print(f"Todavía no existe {RUTA_HISTORICO}. Hay que correr validate_dataset.py primero.")
        sys.exit(1)
    with open(RUTA_HISTORICO, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def construir_fila(corrida: dict) -> str:
    """Arma una fila de la tabla de trazabilidad, con el resultado como una pastilla de color."""
    exitosa = corrida["resultado"] == "EXITOSA"
    color = COLOR_EXITO if exitosa else COLOR_FALLA
    autor = corrida.get("autor", "sin registrar")
    pastilla = (
        f'<span style="display:inline-flex; align-items:center; gap:6px; '
        f'padding:3px 10px; border-radius:999px; font-size:11px; letter-spacing:0.04em; '
        f'background:{color}22; color:{color}; border:1px solid {color}55;">'
        f'<span style="width:6px; height:6px; border-radius:50%; background:{color};"></span>'
        f'{corrida["resultado"]}</span>'
    )
    return (
        "<tr>"
        f"<td class='mono tenue'>{corrida['fecha_hora']}</td>"
        f"<td>{autor}</td>"
        f"<td class='mono'>{corrida['total_registros']}</td>"
        f"<td class='mono'>{corrida['registros_validos']}</td>"
        f"<td class='mono'>{corrida['registros_invalidos']}</td>"
        f"<td class='mono'>{corrida['pct_calidad']}%</td>"
        f"<td class='mono'>{corrida['pct_consentimiento']}%</td>"
        f"<td class='mono tenue'>{corrida['duplicados_id']}</td>"
        f"<td class='mono tenue'>{corrida['duplicados_telefono']}</td>"
        f"<td class='mono tenue'>{corrida['telefonos_formato_invalido']}</td>"
        f"<td class='mono tenue'>{corrida['consentimiento_invalido']}</td>"
        f"<td>{pastilla}</td>"
        "</tr>"
    )


def construir_grafico_tendencia(historico: list) -> str:
    """Dibuja un gráfico de área con el porcentaje de calidad de cada corrida.

    Sigue siendo SVG puro, sin librerías externas, para que el archivo se
    pueda abrir sin conexión a internet. El relieve bajo la línea usa un
    degradado que se apaga hacia abajo, y los puntos se pintan del color
    del resultado para detectar de un vistazo en qué corrida hubo problemas.
    """
    ancho = max(560, len(historico) * 70)
    alto = 200
    margen_izq, margen_der, margen_arriba, margen_abajo = 40, 20, 20, 30

    valores = [float(corrida["pct_calidad"]) for corrida in historico]
    cantidad = len(valores)
    ancho_util = ancho - margen_izq - margen_der
    alto_util = alto - margen_arriba - margen_abajo
    paso_x = ancho_util / max(cantidad - 1, 1)

    def ubicar(indice, valor):
        x = margen_izq + indice * paso_x
        y = margen_arriba + alto_util - (valor / 100) * alto_util
        return x, y

    coordenadas = [ubicar(i, v) for i, v in enumerate(valores)]
    puntos_linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordenadas)

    base_y = margen_arriba + alto_util
    puntos_area = f"{margen_izq:.1f},{base_y:.1f} " + puntos_linea + f" {coordenadas[-1][0]:.1f},{base_y:.1f}"

    marcadores = []
    for indice, (x, y) in enumerate(coordenadas):
        color = COLOR_EXITO if historico[indice]["resultado"] == "EXITOSA" else COLOR_FALLA
        marcadores.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}" stroke="{COLOR_FONDO}" stroke-width="1.5" />')

    lineas_guia = "".join(
        f'<line x1="{margen_izq}" y1="{margen_arriba + alto_util * (1 - nivel / 100):.1f}" '
        f'x2="{ancho - margen_der}" y2="{margen_arriba + alto_util * (1 - nivel / 100):.1f}" '
        f'stroke="rgba(255,255,255,0.06)" stroke-dasharray="3 4" />'
        f'<text x="4" y="{margen_arriba + alto_util * (1 - nivel / 100) + 4:.1f}" '
        f'font-size="10" fill="{COLOR_TEXTO_TENUE}" font-family="ui-monospace, monospace">{nivel}</text>'
        for nivel in (0, 50, 100)
    )

    return f"""<svg viewBox="0 0 {ancho} {alto}" width="100%" height="{alto}">
  <defs>
    <linearGradient id="degradadoTendencia" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{COLOR_EXITO}" stop-opacity="0.35" />
      <stop offset="100%" stop-color="{COLOR_EXITO}" stop-opacity="0" />
    </linearGradient>
  </defs>
  {lineas_guia}
  <polygon points="{puntos_area}" fill="url(#degradadoTendencia)" />
  <polyline points="{puntos_linea}" fill="none" stroke="{COLOR_EXITO}" stroke-width="2" />
  {''.join(marcadores)}
</svg>"""


def calcular_resumen(historico: list) -> dict:
    """Saca los indicadores generales que van en las tarjetas de arriba del tablero."""
    corridas_exitosas = sum(1 for corrida in historico if corrida["resultado"] == "EXITOSA")
    return {
        "ultima_corrida": historico[-1],
        "total_corridas": len(historico),
        "corridas_exitosas": corridas_exitosas,
        "tasa_exito": round((corridas_exitosas / len(historico)) * 100, 1),
    }


# El CSS vive aparte del f-string principal para no tener que duplicar
# cada llave de la hoja de estilos. La tipografía mezcla una serif para
# los títulos (le da carácter editorial, no de plantilla genérica) con
# una monoespaciada para los números (así se leen como datos, no como texto).
ESTILO = """
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 40px 48px 64px;
    background:
      radial-gradient(circle at 15% 0%, rgba(94,234,212,0.08), transparent 40%),
      radial-gradient(circle at 85% 15%, rgba(251,191,36,0.06), transparent 35%),
      #0b0e14;
    color: #e6e8ec;
    font-family: -apple-system, "Segoe UI", Arial, sans-serif;
  }
  .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
  .tenue { color: #8b93a3; }

  .encabezado { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px; margin-bottom: 36px; }
  .marca { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: #5eead4; margin: 0 0 10px; }
  h1 {
    font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
    font-size: 30px; font-weight: 500; margin: 0; letter-spacing: -0.01em;
  }
  .en-vivo { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #8b93a3; }
  .punto-vivo { width: 7px; height: 7px; border-radius: 50%; background: #5eead4; box-shadow: 0 0 0 0 rgba(94,234,212,0.7); animation: pulso 2s infinite; }
  @keyframes pulso {
    0%   { box-shadow: 0 0 0 0 rgba(94,234,212,0.55); }
    70%  { box-shadow: 0 0 0 8px rgba(94,234,212,0); }
    100% { box-shadow: 0 0 0 0 rgba(94,234,212,0); }
  }

  .tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 40px; }
  .tarjeta {
    position: relative; overflow: hidden;
    background: #12161f; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;
    padding: 20px 20px 18px; padding-left: 22px;
  }
  .tarjeta::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, #5eead4, #22d3ee);
  }
  .tarjeta.alerta::before { background: linear-gradient(180deg, #fbbf24, #fb7185); }
  .tarjeta .valor { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 30px; font-weight: 600; color: #f4f6f8; }
  .tarjeta .etiqueta { font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.06em; color: #8b93a3; margin-top: 6px; }

  .seccion { margin-top: 40px; }
  .titulo-seccion { display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px; }
  .indice-seccion { font-family: ui-monospace, monospace; font-size: 12px; color: #5eead4; }
  h2 { font-family: Georgia, "Iowan Old Style", serif; font-size: 18px; font-weight: 500; margin: 0; color: #f4f6f8; }
  .subtitulo { color: #8b93a3; font-size: 13px; margin: 2px 0 16px; }

  .panel { background: #12161f; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 18px; }

  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 11px 14px; text-align: left; font-size: 12.5px; border-bottom: 1px solid rgba(255,255,255,0.06); white-space: nowrap; }
  th { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.06em; color: #8b93a3; font-weight: 600; text-align: left; }
  tbody tr:hover { background: rgba(255,255,255,0.02); }
  .tabla-scroll { overflow-x: auto; }

  footer { margin-top: 48px; font-size: 11px; color: #565e6c; text-align: center; }
</style>
"""


def armar_pagina(historico: list) -> str:
    resumen = calcular_resumen(historico)
    ultima = resumen["ultima_corrida"]

    # La tabla se muestra de la corrida más reciente a la más antigua,
    # que es el orden en que alguien de negocio normalmente la revisa. El
    # gráfico, en cambio, va de más antigua a más reciente porque así se
    # lee una tendencia en el tiempo, de izquierda a derecha.
    filas_tabla = "\n".join(construir_fila(c) for c in reversed(historico))
    grafico_tendencia = construir_grafico_tendencia(historico)
    hay_invalidos = int(ultima["registros_invalidos"]) > 0

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>KPI's - Dataset de teléfonos de clientes</title>
{ESTILO}
</head>
<body>

  <div class="encabezado">
    <div>
      <p class="marca">Veeduría de datos &middot; clientes</p>
      <h1>Calidad y trazabilidad del dataset de teléfonos</h1>
    </div>
    <div class="en-vivo"><span class="punto-vivo"></span>actualizado en cada corrida del pipeline &middot; {ultima['fecha_hora']} (hora Bogotá)</div>
  </div>

  <div class="tarjetas">
    <div class="tarjeta"><div class="valor">{ultima['pct_calidad']}%</div><div class="etiqueta">Calidad, última corrida</div></div>
    <div class="tarjeta"><div class="valor">{ultima['pct_consentimiento']}%</div><div class="etiqueta">Consentimiento vigente</div></div>
    <div class="tarjeta"><div class="valor">{ultima['total_registros']}</div><div class="etiqueta">Registros en el dataset</div></div>
    <div class="tarjeta{' alerta' if hay_invalidos else ''}"><div class="valor">{ultima['registros_invalidos']}</div><div class="etiqueta">Inválidos, última corrida</div></div>
    <div class="tarjeta"><div class="valor">{resumen['tasa_exito']}%</div><div class="etiqueta">Éxito del pipeline ({resumen['corridas_exitosas']}/{resumen['total_corridas']})</div></div>
  </div>

  <div class="seccion">
    <div class="titulo-seccion"><span class="indice-seccion">01</span><h2>Tendencia de calidad</h2></div>
    <p class="subtitulo">Porcentaje de registros válidos por corrida, de la más antigua (izquierda) a la más reciente (derecha)</p>
    <div class="panel">{grafico_tendencia}</div>
  </div>

  <div class="seccion">
    <div class="titulo-seccion"><span class="indice-seccion">02</span><h2>Histórico de corridas</h2></div>
    <p class="subtitulo">Bitácora completa: quién hizo el cambio, qué tan bien pasó la validación, y si se desplegó</p>
    <div class="panel tabla-scroll">
      <table>
        <thead>
          <tr>
            <th>Fecha (Bogotá)</th><th>Autor</th><th>Total</th><th>Válidos</th><th>Inválidos</th>
            <th>% Calidad</th><th>% Consent.</th><th>Dup. ID</th><th>Dup. Tel.</th>
            <th>Tel. inv.</th><th>Consent. inv.</th><th>Resultado</th>
          </tr>
        </thead>
        <tbody>
{filas_tabla}
        </tbody>
      </table>
    </div>
  </div>

  <footer>Generado automáticamente por scripts/generar_kpis.py &middot; no requiere conexión a internet</footer>

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
