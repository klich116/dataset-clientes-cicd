# Dataset de Numeros de Telefono de Clientes — Pipeline CI/CD + KPI's

Prototipo funcional de los dos ejercicios conceptuales:

1. Proceso automatizado con practicas de CI/CD para crear, validar,
   desplegar y mantener un dataset confiable de numeros de telefono de
   clientes.
2. Mecanismo de veeduria de calidad y trazabilidad (KPI's) para que
   equipos de negocio consulten el estado del dataset, sin necesidad de
   tocar el pipeline ni saber programar.

Todo lo que valida y despliega el dataset esta escrito en **Python puro**
(`scripts/validate_dataset.py` y `scripts/deploy_dataset.py`). El unico
archivo que no es Python es `.github/workflows/ci-cd.yml`, que es la
configuracion (en YAML) que le dice a GitHub Actions cuando ejecutar esos
scripts. Ese archivo no hace nada por si solo, solo orquesta.

## Estructura del proyecto

```
dataset-clientes-cicd/
├── data/
│   ├── clientes_telefonos.csv       <- dataset "fuente" (el que se edita)
│   ├── produccion/                  <- se genera automaticamente al desplegar
│   └── metricas/
│       ├── historico_calidad.csv    <- una fila de metricas por cada corrida (KPI's)
│       └── dashboard_kpis.html      <- vista para negocio, se regenera solo
├── scripts/
│   ├── validate_dataset.py          <- reglas de calidad (CI) + registra metricas
│   ├── deploy_dataset.py            <- simula publicar a produccion (CD)
│   └── generar_kpis.py              <- construye el dashboard de KPI's (Ejercicio 2)
├── .github/workflows/
│   └── ci-cd.yml                    <- orquesta cuando correr CI, CD y KPI's
└── README.md
```

## Probarlo en tu computador (sin GitHub, sin nada que instalar aparte de Python)

Necesitas tener Python 3 instalado (ya viene en Mac/Linux; en Windows
descargalo de python.org). No requiere librerias externas.

1. Abre una terminal dentro de la carpeta `dataset-clientes-cicd`.
2. Corre la validacion:
   ```
   python3 scripts/validate_dataset.py
   ```
   Si el dataset esta bien, veras "VALIDACION EXITOSA". Si algo esta mal
   (un telefono con formato invalido, un duplicado, un campo vacio), el
   script te dice exactamente cual fila y por que, y termina con error
   — asi es como el pipeline "bloquea" un despliegue con datos malos.
3. Si la validacion paso, simula el despliegue:
   ```
   python3 scripts/deploy_dataset.py
   ```
   Esto crea `data/produccion/` con una copia fechada del dataset y un
   log (`log_despliegues.csv`) de cada despliegue realizado.

Prueba a romper una fila del CSV (por ejemplo, borra el `+` de un
telefono) y vuelve a correr `validate_dataset.py` para ver como falla.
Cada vez que corras `validate_dataset.py` (pase o falle), se agrega una
fila nueva a `data/metricas/historico_calidad.csv` — asi se construye la
trazabilidad en el tiempo.

4. Genera (o actualiza) el dashboard de KPI's para negocio:
   ```
   python3 scripts/generar_kpis.py
   ```
   Esto crea/actualiza `data/metricas/dashboard_kpis.html`. Abrelo con
   doble clic en cualquier navegador — no necesita servidor ni internet.
   Muestra: % de calidad, % de consentimiento, tasa de exito del
   pipeline, y una tabla cronologica de cada corrida (trazabilidad).

## Ponerlo a correr automaticamente en GitHub (gratis, sin instalar nada)

Esto es lo que activa el CI/CD "de verdad": cada vez que subas un cambio,
GitHub valida el dataset solo, y si esta en la rama `main`, lo despliega
solo.

1. Crea una cuenta gratuita en https://github.com (si no tienes).
2. Crea un repositorio nuevo, vacio, publico o privado (ambos son gratis).
3. Sube esta carpeta completa al repositorio. La forma mas facil sin usar
   la terminal de git: en la pagina del repo, boton "Add file" ->
   "Upload files", y arrastra todos los archivos y carpetas (incluyendo
   `.github/workflows/ci-cd.yml` — GitHub a veces oculta carpetas que
   empiezan con punto en el explorador de tu sistema operativo; si no
   la ves, usa `git` por terminal o revisa la opcion de "mostrar archivos
   ocultos" de tu sistema).
4. Ve a la pestana "Actions" del repositorio. Deberias ver el workflow
   "CI/CD Dataset Clientes Telefonos" corriendo automaticamente.
5. Cada vez que edites `data/clientes_telefonos.csv` y subas el cambio
   a `main`, el pipeline: (a) valida, y (b) si pasa, despliega y guarda
   el resultado en `data/produccion/` dentro del mismo repositorio.

## Como esto se conecta con un caso real

En produccion real, `deploy_dataset.py` no copiaria un archivo — haria
un `INSERT`/`UPSERT` a una base de datos, cargaria el archivo a un data
warehouse (BigQuery, Snowflake, Redshift) o llamaria a la API de un CRM.
La logica de validacion y la estructura del pipeline (CI que valida en
cada cambio, CD que despliega solo si valida) es la misma sin importar
el destino final.
