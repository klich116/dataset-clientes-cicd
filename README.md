# Dataset de números de teléfono de clientes con CI/CD (y cómo saber si está funcionando)

Prototipo funcional de los dos ejercicios conceptuales de la prueba, porque en la práctica son la misma conversación: primero hay que decidir cómo se crea y se cuida el dataset, y después hay que poder responder "¿está bien ese dato o no?" sin tener que meterse al código cada vez que alguien de negocio pregunte.

**Repositorio:** este mismo — [github.com/klich116/dataset-clientes-cicd](https://github.com/klich116/dataset-clientes-cicd)
**Tablero de KPI's en vivo:** [klich116.github.io/dataset-clientes-cicd/data/metricas/dashboard_kpis.html](https://klich116.github.io/dataset-clientes-cicd/data/metricas/dashboard_kpis.html) — se actualiza solo después de cada corrida, sin descargar nada.

## El problema que estoy resolviendo

Hoy en día, cuando un dataset de contacto de clientes se arma "a mano" —alguien exporta un CSV, otro lo revisa por encima, alguien más lo sube a donde se vaya a usar— es fácil que se cuelen números mal escritos, duplicados, o registros sin el consentimiento del cliente para ser contactado. El error se descubre tarde, normalmente cuando ya se mandó un mensaje a un número que no existe o a alguien que pidió que no lo llamaran más.

La idea de este ejercicio es quitarle esa parte manual al proceso y ponerle un filtro automático: nada se publica si no pasa antes por una serie de revisiones. A eso es a lo que le llaman CI/CD.

## Entonces, ¿qué es CI/CD?

CI/CD junta dos ideas que casi siempre van de la mano:

**Integración continua (CI).** Cada vez que alguien propone un cambio —en este caso, una versión nueva del dataset— se disparan automáticamente unas pruebas. Si el cambio no cumple las reglas, ahí se queda, no avanza. Nadie tiene que acordarse de revisarlo manualmente porque el sistema ya lo hace.

**Entrega o despliegue continuo (CD).** Si esas pruebas pasan, el cambio se publica solo, sin que alguien tenga que copiarlo o subirlo a mano. Se conecta directo con el destino final: una base de datos, un CRM, lo que sea.

Normalmente esto se usa para código, pero la lógica es exactamente la misma si lo que se está versionando es un dataset: las "pruebas" pasan a ser reglas de calidad de datos, y el "despliegue" es publicar la versión validada en el sistema donde se va a usar.

## Ejercicio 1 — el pipeline

Pensé el pipeline en tres pasos, uno detrás del otro:

Primero, el dataset vive en un repositorio (uso Git/GitHub porque es gratis y es el estándar de facto). Cada cambio queda con nombre de quién lo hizo y cuándo, así que ya desde ahí hay trazabilidad sin tener que construir nada extra.

Segundo, cuando alguien propone un cambio, un proceso automático revisa el archivo contra un conjunto de reglas. Si algo no cumple, el proceso se detiene ahí y avisa exactamente qué falló y en qué fila.

Tercero, si todo pasó y el cambio ya quedó en la rama principal, se publica automáticamente. Para este ejercicio simulé esa publicación (copiando el archivo a una carpeta de "producción" con fecha), pero en un caso real ese paso cargaría los datos a una base de datos o llamaría a la API de un CRM.

Para orquestar esto usé GitHub Actions. La elegí por una razón simple: es gratuita, no exige instalar nada, y como el dataset ya vive en GitHub, el pipeline queda ahí mismo, sin depender de otra herramienta. Vale la pena aclarar que GitHub Actions solo decide *cuándo* correr cada paso (eso está en un archivo de configuración); la lógica real —las reglas de validación, el despliegue— está escrita en Python, que es más fácil de leer y de modificar para cualquiera que herede este proyecto.

### Las reglas que apliqué

No quise inventar reglas complicadas, sino las que de verdad importan para que el dato sirva:

- Que el archivo tenga las columnas que se necesitan (id de cliente, nombre, teléfono, país, consentimiento, fecha).
- Que ningún campo obligatorio esté vacío.
- Que el teléfono tenga formato E.164 (el estándar internacional: `+`, código de país, número, sin espacios ni guiones). Si no cumple esto, ningún sistema de mensajería masiva lo va a aceptar de todas formas.
- Que no haya clientes ni teléfonos repetidos.
- Que el campo de consentimiento esté explícitamente en `true` o `false`, nunca vacío. Esta última es, en realidad, la regla que más me importa: no quiero que se publique un registro donde no quede claro si el cliente autorizó o no que lo contacten.

Si una sola fila incumple una regla, el pipeline entero se detiene. Preferí que fuera así de estricto porque el costo de dejar pasar un dato malo (una llamada a un número equivocado, un mensaje a alguien que no dio consentimiento) es más alto que el costo de tener que corregir el archivo y volver a intentar.

## Ejercicio 2 — que negocio pueda ver qué está pasando

Aquí el reto cambia un poco. Ya no se trata de bloquear datos malos, sino de que alguien que no sabe programar pueda mirar el estado del dataset sin tener que pedirle a alguien de TI que le explique.

La solución que propongo se apoya completamente en lo que ya construí en el ejercicio 1, en vez de armar algo aparte. Cada vez que el pipeline corre —pase o falle la validación— guarda una fila de métricas: cuántos registros había, cuántos pasaron, cuántos no, y por qué. Esas filas se van acumulando en un archivo histórico, y ese histórico es la materia prima de todo.

A partir de ahí genero automáticamente una página (HTML, sin nada que instalar, se abre con doble clic) que muestra:

- Qué tan bien está el dataset ahora mismo (porcentaje de registros válidos).
- Qué porcentaje de los clientes dio su consentimiento.
- Qué tan seguido el pipeline logra pasar sin errores, lo cual dice bastante sobre qué tan disciplinado es el proceso de captura de datos aguas arriba.
- Un desglose de qué tipo de error es el más común (¿son duplicados? ¿formato? ¿falta el consentimiento?), para saber dónde enfocar la limpieza.
- Una tabla con el historial completo de corridas, ordenada de la más reciente a la más antigua, que sirve como bitácora de auditoría.

Un punto que me pareció importante: guardo las métricas de *todas* las corridas, no solo las que terminaron bien. Si solo registrara los éxitos, se perdería la parte más útil para negocio, que es entender cuántas veces y por qué algo no pasó la validación.

Y la trazabilidad de quién hizo qué cambio no la tuve que inventar: como todo vive en un repositorio con control de versiones, cada modificación ya queda asociada a una persona, una fecha y un mensaje explicando el motivo. Es una de esas cosas que Git te da gratis si decides usarlo desde el principio.

## Estructura del proyecto

```
dataset-clientes-cicd/
├── data/
│   ├── clientes_telefonos.csv       <- dataset "fuente" (el que se edita)
│   ├── produccion/                  <- se genera automáticamente al desplegar
│   └── metricas/
│       ├── historico_calidad.csv    <- una fila de métricas por cada corrida (KPI's)
│       └── dashboard_kpis.html      <- vista para negocio, se regenera solo
├── scripts/
│   ├── validate_dataset.py          <- reglas de calidad (CI) + registra métricas
│   ├── deploy_dataset.py            <- simula publicar a producción (CD)
│   └── generar_kpis.py              <- construye el dashboard de KPI's (Ejercicio 2)
├── .github/workflows/
│   └── ci-cd.yml                    <- orquesta cuándo correr CI, CD y KPI's
└── README.md
```

## Probarlo en tu computador (sin GitHub, sin nada que instalar aparte de Python)

Necesitas tener Python 3 instalado (ya viene en Mac/Linux; en Windows descárgalo de python.org). No requiere librerías externas.

1. Abre una terminal dentro de la carpeta `dataset-clientes-cicd`.
2. Corre la validación:
   ```
   python3 scripts/validate_dataset.py
   ```
   Si el dataset está bien, verás "VALIDACION EXITOSA". Si algo está mal (un teléfono con formato inválido, un duplicado, un campo vacío), el script te dice exactamente cuál fila y por qué, y termina con error — así es como el pipeline "bloquea" un despliegue con datos malos.
3. Si la validación pasó, simula el despliegue:
   ```
   python3 scripts/deploy_dataset.py
   ```
   Esto crea `data/produccion/` con una copia fechada del dataset y un log (`log_despliegues.csv`) de cada despliegue realizado.

Prueba a romper una fila del CSV (por ejemplo, borra el `+` de un teléfono) y vuelve a correr `validate_dataset.py` para ver cómo falla. Cada vez que corras `validate_dataset.py` (pase o falle), se agrega una fila nueva a `data/metricas/historico_calidad.csv` — así se construye la trazabilidad en el tiempo.

4. Genera (o actualiza) el dashboard de KPI's para negocio:
   ```
   python3 scripts/generar_kpis.py
   ```
   Esto crea/actualiza `data/metricas/dashboard_kpis.html`. Ábrelo con doble clic en cualquier navegador — no necesita servidor ni internet. Muestra: % de calidad, % de consentimiento, tasa de éxito del pipeline, y una tabla cronológica de cada corrida (trazabilidad).

## Ponerlo a correr automáticamente en GitHub (gratis, sin instalar nada)

Esto es lo que activa el CI/CD "de verdad": cada vez que subas un cambio, GitHub valida el dataset solo, y si está en la rama `main`, lo despliega solo.

1. Crea una cuenta gratuita en https://github.com (si no tienes).
2. Crea un repositorio nuevo, vacío, público o privado (ambos son gratis).
3. Sube esta carpeta completa al repositorio. La forma más fácil sin usar la terminal de git: en la página del repo, botón "Add file" → "Upload files", y arrastra todos los archivos y carpetas (incluyendo `.github/workflows/ci-cd.yml` — GitHub a veces oculta carpetas que empiezan con punto en el explorador de tu sistema operativo; si no la ves, usa `git` por terminal o revisa la opción de "mostrar archivos ocultos" de tu sistema).
4. Ve a la pestaña "Actions" del repositorio. Deberías ver el workflow "CI/CD Dataset Clientes Telefonos" corriendo automáticamente.
5. Cada vez que edites `data/clientes_telefonos.csv` y subas el cambio a `main`, el pipeline: (a) valida, y (b) si pasa, despliega y guarda el resultado en `data/produccion/` dentro del mismo repositorio.

## Dónde verlo funcionando de verdad

Todo lo anterior ya no es solo diseño en papel: está corriendo en este mismo repositorio.

**Cómo se activa el pipeline.** No hay que correr nada a mano ni apretar un botón: el pipeline se dispara solo cada vez que alguien sube un cambio (`push`) a la rama principal (`main`) que toque la carpeta `data/` o `scripts/`. En la práctica eso pasa cuando alguien edita el archivo `data/clientes_telefonos.csv` (agrega un cliente, corrige un teléfono) y confirma el cambio. En ese momento GitHub Actions arranca automáticamente los dos jobs: primero valida, y si pasa, despliega. Todo esto se puede ver en vivo en la pestaña **Actions** del repositorio.

**Tablero de KPI's, en línea.** El archivo `dashboard_kpis.html` que genera el pipeline no solo queda guardado en el repositorio: también está publicado como página web (vía GitHub Pages), así que se puede consultar sin descargar nada y se actualiza solo después de cada corrida:

[klich116.github.io/dataset-clientes-cicd/data/metricas/dashboard_kpis.html](https://klich116.github.io/dataset-clientes-cicd/data/metricas/dashboard_kpis.html)

## Cómo esto se conecta con un caso real

En producción real, `deploy_dataset.py` no copiaría un archivo — haría un `INSERT`/`UPSERT` a una base de datos, cargaría el archivo a un data warehouse (BigQuery, Snowflake, Redshift) o llamaría a la API de un CRM. La lógica de validación y la estructura del pipeline (CI que valida en cada cambio, CD que despliega solo si valida) es la misma sin importar el destino final.

## Para cerrar

Al final, lo que estoy proponiendo no es una herramienta complicada, sino quitar del medio los pasos manuales donde más se cuelan los errores: nadie tiene que acordarse de revisar el archivo a mano, y nadie tiene que preguntar por Slack si el dataset está actualizado, porque el tablero ya lo dice. Si mañana cambia una regla de negocio (por ejemplo, que se empiece a exigir un campo más), el ajuste se hace en un solo lugar y automáticamente aplica para cualquier actualización futura del dataset.
