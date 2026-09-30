# Guía de uso de CoopExecutive

Esta guía recorre cada área con ejemplos que puede copiar. Los comandos suponen que ya instaló el paquete (vea el [README](../README.es.md#instalación)) y que definió el espacio de su organización:

```bash
export COOPEXECUTIVE_WORKSPACE=~/procuracion/mi-org
```

En Windows (PowerShell): `$env:COOPEXECUTIVE_WORKSPACE = "$HOME\procuracion\mi-org"`. También puede pasar `--espacio RUTA` antes de cualquier comando.

Contenido:

1. [Primeros pasos](#1-primeros-pasos)
2. [Perfil de la organización](#2-perfil-de-la-organización)
3. [Fecha y plazos](#3-fecha-y-plazos)
4. [Evaluar convocatorias](#4-evaluar-convocatorias)
5. [Comparar convocatorias](#5-comparar-convocatorias)
6. [Monitorear convocatorias](#6-monitorear-convocatorias)
7. [Financiadores y expedientes](#7-financiadores-y-expedientes)
8. [Preparar reuniones](#8-preparar-reuniones)
9. [Redactar y generar documentos Word](#9-redactar-y-generar-documentos-word)
10. [Diseño de proyecto](#10-diseño-de-proyecto)
11. [Consultar información y revisar fuentes](#11-consultar-información-y-revisar-fuentes)
12. [Asamblea](#12-asamblea)
13. [Chat con herramientas](#13-chat-con-herramientas)
14. [Panel local y API](#14-panel-local-y-api)
15. [Servidor MCP](#15-servidor-mcp)
16. [Bitácora](#16-bitácora)
17. [Problemas frecuentes](#17-problemas-frecuentes)

---

## 1. Primeros pasos

```bash
coopexecutive iniciar ~/procuracion/mi-org --nombre "Mi Organización" --tipo asociacion_civil
coopexecutive info
```

`iniciar` crea la carpeta con un perfil mínimo (`profile.yaml`), la base de datos y `salidas/`. Los tipos válidos son `cooperativa`, `asociacion_civil`, `empresa` y `persona_fisica`. Solo las cooperativas tienen fondos estatutarios y asamblea de un socio, un voto.

`info` muestra la organización activa, el proveedor y el modelo, y qué archivos `.env` se cargaron. Si todavía no tiene clave de ningún modelo, puede avanzar: la matriz, los plazos, los expedientes, los documentos Word, la asamblea y la bitácora funcionan sin modelo.

## 2. Perfil de la organización

### Desde el sitio web

```bash
coopexecutive configurar --sitio https://www.ejemplo.org/
```

El agente lee la portada y hasta seis páginas del mismo dominio que suelen tener datos institucionales (nosotros, contacto, programas, únete, transparencia). Respeta robots.txt y limita el tamaño de cada página. Antes de proponer nada quita cuentas bancarias, RFC, CURP, correos personales y teléfonos.

Para cada una de las diez preguntas muestra la propuesta, la evidencia y la URL de donde salió:

- «sí» acepta la propuesta;
- cualquier otro texto la sustituye;
- Enter conserva el valor actual, o lo deja pendiente si estaba vacío.

Si el sitio no dice algo, la pregunta aparece como «Pendiente» y usted puede escribir el dato.

### A mano

```bash
coopexecutive configurar
```

Diez preguntas: nombre y siglas, figura jurídica, misión, población y territorio, programas y ejes de trabajo, métricas, estatus legal y fiscal, rango de montos y moneda, alianzas y financiadores previos, y quién aprueba y cómo se reciben los fondos. Si una respuesta es «está en nuestro sitio», el agente pide el enlace una sola vez y lo consulta solo para esa pregunta.

### Desde un archivo

```bash
coopexecutive configurar --desde company/examples/respuestas_perfil.yaml
```

El archivo de ejemplo tiene datos ficticios. Lo que no sepa, déjelo vacío: queda como `[PENDIENTE]`. No incluya RFC, CURP, domicilio ni cuentas bancarias.

En los tres modos se respalda el perfil anterior (`profile.yaml.bak-…`) antes de escribir, y `procuracion.origenes` guarda la procedencia de cada dato.

### Membrete e identidad

En `profile.yaml`, el bloque `procuracion.membrete` define el membrete de los Word:

```yaml
procuracion:
  membrete:
    imagen: membrete.png   # encabezado, relativo a la carpeta del perfil
    pie: "www.ejemplo.org"
    fuente: Arial
    tamano: 11
```

El bloque `identidad` (nombre corto, lema, logo, fuente y colores) alimenta la intro de la terminal: `coopexecutive intro generar` la dibuja y requiere el extra `identidad`.

En cooperativas, `governance.mayoria` puede ser `simple` o `dos_tercios`; el escrutinio aplica esa regla y el acta la cita.

## 3. Fecha y plazos

```bash
coopexecutive fecha
coopexecutive fecha --cierre 2026-10-09 --cierre "30 de octubre de 2026" --cierre 15/11/2026
```

Muestra la fecha de hoy en la zona de `USER_TIMEZONE` y, por cada cierre, el día de la semana, los días naturales restantes y el texto de plazo: «Faltan N días», «(URGENTE)» con 13 días o menos, «Cierra hoy» o «Vencida». Es el mismo criterio que usa la matriz.

## 4. Evaluar convocatorias

La matriz tiene ocho criterios que suman 100 puntos:

| Criterio | Peso |
|---|---|
| Alineación con la misión | 20 |
| Elegibilidad geográfica y legal | 10 |
| Rango presupuestal adecuado | 15 |
| Viabilidad de tiempos y entrega | 10 |
| Capacidad técnica y operativa | 15 |
| Potencial de impacto medible | 15 |
| Valor estratégico a largo plazo | 10 |
| Requisitos de auditoría y reporte | 5 |

Cada puntaje necesita evidencia. Un criterio vacío queda pendiente y no cuenta como cero. Los puntos de tiempos deben corresponder a los días que faltan: menos de 7 días admite de 0 a 2 puntos; de 7 a 13, de 3 a 5; de 14 a 28, de 6 a 8; y más de 28, de 9 a 10.

La decisión sale de la primera regla que se cumpla:

| Orden | Condición | Decisión |
|---|---|---|
| 1 | Datos que no cumplen las reglas (puntaje fuera de rango, sin evidencia) | `ERROR_VALIDACION` |
| 2 | Elegibilidad excluida o cierre vencido | `DESCARTAR` |
| 3 | Elegibilidad pendiente | `VERIFICAR_ELEGIBILIDAD` |
| 4 | Vigencia pendiente | `VERIFICAR_VIGENCIA` |
| 5 | Choque con una posición pública de la organización | `ESCALAR_DIRECCION` |
| 6 | Algún criterio sin calificar | `EVALUACION_INCOMPLETA` |
| 7 | 80 puntos o más | `APLICAR` |
| 8 | De 60 a 79 | `EXPLORAR` |
| 9 | De 40 a 59 | `CONDICIONAL` |
| 10 | Menos de 40 | `DESCARTAR` |

Una tensión pendiente baja APLICAR o EXPLORAR a CONDICIONAL. Cada resultado incluye un contrapunto (el criterio más fuerte o el más débil), el siguiente paso y una huella SHA-256 de la entrada y el resultado.

Hay cuatro formas de dar la entrada:

```bash
# 1. Preguntas en la terminal
coopexecutive evaluar-convocatoria

# 2. Un YAML con puntajes y evidencias (sin modelo)
coopexecutive evaluar-convocatoria --archivo company/examples/convocatoria_ejemplo.yaml

# 3. Las bases en URL, PDF, Word o HTML: el modelo propone puntajes con evidencia
coopexecutive evaluar-convocatoria https://ejemplo.org/bases.pdf --expediente EXP-2026-0001

# 4. Las bases como texto pegado
coopexecutive evaluar-convocatoria --asistido "Texto de las bases…"
```

En los modos 3 y 4, el modelo solo propone. La propuesta se valida con pydantic, usted la confirma o la corrige (`--si` la acepta sin preguntar), la matriz decide y después el modelo redacta el análisis, que pasa por la revisión estricta.

Opciones útiles:

- `--no-guardar`: muestra el resultado sin guardarlo.
- `--expediente EXP-…`: vincula la evaluación a un expediente.
- `--proponer-asamblea`: si la decisión es APLICAR, crea una propuesta de categoría `subvencion` que cita el folio y la huella. En organizaciones sin asamblea remite a sus aprobadores.

## 5. Comparar convocatorias

```bash
coopexecutive comparar-convocatorias                      # las diez evaluaciones más recientes
coopexecutive comparar-convocatorias 1 2 --orden puntaje  # por identificador
coopexecutive comparar-convocatorias --expediente EXP-2026-0001 --word
```

La tabla muestra decisión, puntaje, monto, plazo y siguiente paso, y termina con cuál atender primero: la más urgente entre las que conviene preparar (`--orden plazo`, por omisión) o la de mayor puntaje (`--orden puntaje`). Con `--word` guarda el reporte.

## 6. Monitorear convocatorias

```bash
coopexecutive monitorear
coopexecutive monitorear --tema "energía renovable" --tema "formación técnica"
coopexecutive monitorear --sin-cache --todas
```

Lee los canales RSS/Atom públicos de las fuentes incluidas y de su `fuentes.yaml`. Los temas salen de los ejes de trabajo del perfil, o de `--tema`. Un aviso se conserva solo si contiene todas las palabras significativas de al menos un tema. Una fecha de cierre solo se acepta si sigue a una palabra de cierre; si no, el aviso queda `VIGENCIA NO VERIFICADA`.

Para sumar fuentes propias, cree `fuentes.yaml` en el espacio:

```yaml
fuentes:
  - nombre: Portal estatal de convocatorias
    tipo: Gobierno
    region: México
    idioma: es
    url: https://convocatorias.ejemplo.gob.mx/
    rss: https://convocatorias.ejemplo.gob.mx/feed/
temas: ["energía comunitaria"]
solo_propias: false
```

Una fuente sin `rss` aparece para revisión manual. Las descargas se guardan 12 horas en `.cache/`. Cada corrida queda en la base y se ve en el panel. `documento reporte-monitoreo` guarda el resultado en Word.

## 7. Financiadores y expedientes

```bash
coopexecutive financiadores registrar "Fundación Ejemplo" --proyecto "Microrredes comunitarias" \
  --tipo "Fundación" --canal "Correo" --moneda USD --contacto "Oficial de programa"
coopexecutive financiadores buscar ejemplo
coopexecutive financiadores ver FIN-2026-0001
coopexecutive financiadores actualizar FIN-2026-0001 --seguimiento 2026-10-15

coopexecutive expedientes abrir "Fundación Ejemplo" --tipo Convocatoria --fecha-limite 2026-11-08
coopexecutive expedientes avance EXP-2026-0001 --estado "Nota conceptual enviada" \
  --siguiente "Llamar a la oficial de programa" --origen "Dato del usuario"
coopexecutive expedientes listar
coopexecutive expedientes ver EXP-2026-0001
```

Los financiadores reciben folio `FIN-AAAA-NNNN` y se detectan duplicados por nombre normalizado. Los expedientes reciben `EXP-AAAA-NNNN`; solo puede haber uno abierto por entidad y tipo. Sin `--monto`, el expediente muestra `MONTO POR DEFINIR`. Cada avance lleva su origen, y `--cerrar` cierra el expediente.

## 8. Preparar reuniones

```bash
coopexecutive reunion preparar "Fundación Ejemplo" --sitio https://fundacion.ejemplo.org/ \
  --expediente EXP-2026-0001 --objetivo "Presentar el proyecto y conocer su ciclo de convocatorias" --word
```

Lee la portada del sitio y hasta tres páginas. Entrega el perfil público de la entidad (solo con lo leído), la ficha de su organización, los puntos en común, los riesgos, una agenda y preguntas. Cada dato lleva su etiqueta de origen; lo que no se pudo confirmar queda `NO VERIFICADO` o `PENDIENTE`.

## 9. Redactar y generar documentos Word

### Borradores para terceros

```bash
coopexecutive redactar carta-intencion --expediente EXP-2026-0001
coopexecutive redactar propuesta --expediente EXP-2026-0001 --bases https://ejemplo.org/bases.pdf --word
coopexecutive redactar correo-seguimiento --expediente EXP-2026-0001 --indicaciones "Agradecer la llamada del martes"
```

Tipos: `propuesta`, `carta-intencion`, `nota-conceptual`, `justificacion` y `correo-seguimiento`. El texto usa solo los datos del perfil, el expediente y las bases. Antes de mostrarse, los montos y fechas sin respaldo se sustituyen por marcadores y las cuentas bancarias se censuran. Con `--word` se guarda con su membrete.

### Documentos Word

```bash
coopexecutive documento solicitud --expediente EXP-2026-0001
coopexecutive documento institucional
coopexecutive documento ficha --expediente EXP-2026-0001
coopexecutive documento carta-intencion --expediente EXP-2026-0001
coopexecutive documento nota-conceptual --expediente EXP-2026-0001
coopexecutive documento reporte-evaluacion
coopexecutive documento reporte-monitoreo
```

Se arman con el perfil, el expediente y la evaluación, sin modelo. Lo que falta queda como `[PENDIENTE: …]`. Usted ve el contenido antes de guardarlo (`--si` guarda sin preguntar). Los archivos van a `salidas/AAAA/EXP-…/`, nunca se sobrescriben y quedan registrados en su expediente.

## 10. Diseño de proyecto

```bash
coopexecutive proyecto marco-logico "Microrredes comunitarias" --plantilla   # copie la plantilla a marco.yaml
coopexecutive proyecto marco-logico "Microrredes comunitarias" --desde marco.yaml -o marco.md
coopexecutive proyecto presupuesto "Microrredes comunitarias" --desde presupuesto.yaml --tope-indirectos 10
coopexecutive proyecto dossier "Microrredes comunitarias" --expediente EXP-2026-0001 --marco marco.yaml --presupuesto presupuesto.yaml
```

- **Marco lógico:** fin, propósito, componentes y actividades, con indicadores, medios de verificación y supuestos. Con `--asistido`, el modelo propone la estructura y se valida. Lo que falte, como la alineación con los ODS, queda pendiente.
- **Presupuesto:** partidas con solicitado y contrapartida. Una partida sin costo aparece como `COSTO POR COTIZAR` y el total como `MONTO POR DEFINIR`. Los costos indirectos solo se calculan si da `--tope-indirectos`.
- **Dossier:** reúne lo anterior con el financiador y la convocatoria del expediente. Los fondos estatutarios solo aparecen en cooperativas.

`-o archivo.md` guarda el resultado sin sobrescribir. Los nombres cortos `marco-logico`, `presupuesto` y `dossier` siguen funcionando.

## 11. Consultar información y revisar fuentes

```bash
coopexecutive consultar "¿cuál es nuestra figura jurídica?"
coopexecutive consultar "¿qué programas tenemos?" --redactar
coopexecutive revisar https://ejemplo.org/bases.pdf --pregunta "¿quién puede postular?"
coopexecutive revisar informe.docx --sin-modelo --pregunta "indicadores"
```

`consultar` busca en el perfil, en la carpeta `conocimiento/` del espacio (md, txt, html, docx y pdf) y en las guías incluidas. Sin `--redactar` no usa el modelo ni la red: muestra los pasajes con su fuente. Si nada coincide, responde «No consta en el perfil ni en los documentos de conocimiento».

`revisar` resume una página o un archivo citando la fuente. Con `--sin-modelo` muestra los fragmentos más pertinentes a la pregunta.

## 12. Asamblea

Solo para cooperativas.

```bash
coopexecutive socios alta SOC-001 -n "Socia uno"
coopexecutive socios alta SOC-002 -n "Socio dos"
coopexecutive socios listar

coopexecutive propuesta "Postular al fondo de energía" -d "Aprobar la postulación y su contrapartida" -c subvencion
coopexecutive propuestas
coopexecutive votar 1 -s SOC-001 -v a_favor -j "Coincide con el plan anual"
coopexecutive votar 1 -s SOC-002 -v abstencion
coopexecutive escrutinio 1
```

Cada socio vota una vez por propuesta. `escrutinio` toma el padrón de socios activos (o `--padron N`), revisa el cuórum de más de la mitad, aplica la mayoría del perfil, cierra la propuesta como aprobada o rechazada y emite el acta con huella SHA-256. Las propuestas que venden participación, reparten fondos estatutarios o imponen trabajo no remunerado se rechazan.

## 13. Chat con herramientas

```bash
coopexecutive chat
coopexecutive chat --rol finanzas --solo-lectura
coopexecutive ask "¿Qué expedientes vencen este mes?"
coopexecutive ask "Registra a la Fundación Ejemplo como financiador" --estricto
```

Roles: `procurador`, `vigilancia`, `legal`, `finanzas`, `tecnico`, `comunicacion` y `asamblea`.

El modelo puede usar 19 herramientas (las mismas del panel y del servidor MCP). Las 14 de consulta se ejecutan directo. Las 5 que escriben (registrar financiador, abrir expediente, registrar avance, guardar evaluación y generar documento) muestran qué van a hacer y esperan su confirmación. Si usted dice que no, el modelo lo sabe y la revisión posterior no deja pasar frases como «ya lo registré».

`--solo-lectura` ofrece solo las de consulta; `--sin-herramientas` solo conversa.

## 14. Panel local y API

```bash
coopexecutive panel
```

Abre el navegador en `http://127.0.0.1:8765/#token=…`. El token cambia en cada arranque. El chat del panel pide confirmación en un diálogo antes de cualquier escritura; la casilla «Solo consultas» limita el chat a herramientas de consulta.

Ejemplo con la API desde otra terminal (sustituya el token):

```bash
TOKEN=el-token-que-mostró-la-terminal
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/api/expedientes
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"argumentos": {"cierres": ["2026-10-09"]}}' http://127.0.0.1:8765/api/herramientas/fecha_y_plazos
```

Para una herramienta que escribe, la primera llamada responde 409 con el resumen de lo que haría; repítala con `"confirmar": true` en el cuerpo.

## 15. Servidor MCP

```bash
coopexecutive mcp               # todas las herramientas
coopexecutive mcp --solo-lectura
```

Configure su cliente con el comando `coopexecutive`, el argumento `mcp` y la variable `COOPEXECUTIVE_WORKSPACE`. El README tiene el ejemplo para Claude Desktop y Claude Code. El servidor solo escribe en stdout los mensajes del protocolo; los registros van a stderr.

## 16. Bitácora

```bash
coopexecutive bitacora ver
coopexecutive bitacora verificar
coopexecutive bitacora exportar bitacora.jsonl
```

Cada comando y cada llamada a herramienta queda con fecha, canal (cli, agente, http o mcp), acción, parámetros censurados, resultado y una huella SHA-256 que incluye la del registro anterior. `verificar` recorre la cadena y señala el primer registro editado o borrado. `exportar` guarda todos los registros en JSON Lines, sin sobrescribir.

## 17. Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| El modelo no responde o falta la clave | Revise `coopexecutive info`: indica qué `.env` se cargó. Ponga la clave en ese archivo o use Ollama |
| Error 429 del modelo gratuito | Es el límite diario de OpenRouter. Espere, cambie `DEFAULT_MODEL` o use un modelo local |
| El modelo no admite herramientas | El turno se repite sin ellas. Use `coopexecutive modelos --herramientas` para elegir uno que sí |
| No lee un PDF | Instale el extra `pdf` |
| `panel` o `mcp` no existen | Instale los extras `web` o `mcp` |
| El panel dice «Falta el token» | Abra el enlace completo que imprimió la terminal, con `#token=…` |
| `escrutinio` pide padrón | Registre socios con `socios alta` o use `--padron N` |
| La ficha tiene muchos `[PENDIENTE]` | Complete el perfil (`configurar`) y el expediente; el agente no rellena datos que no tiene |
