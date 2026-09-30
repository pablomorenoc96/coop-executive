# Casos de prueba

Este documento sirve para dos cosas: comprobar a mano que el agente se comporta como debe y saber qué cubren las evaluaciones automáticas. Cada caso dice qué hacer y qué debe pasar.

Las evaluaciones automáticas no usan la red ni un modelo real. Corren en un espacio temporal, con la fecha fija del 29 de septiembre de 2026:

```bash
cd packages/core
uv run --all-extras python -m coopexecutive.evals     # resumen; sale con código 1 si algo falla
uv run --all-extras --group dev pytest -m eval        # las mismas, como pruebas
```

## 1. Matriz de evaluación (10 casos automáticos)

Puede repetirlos a mano con `coopexecutive evaluar-convocatoria --archivo caso.yaml --no-guardar`, partiendo de `company/examples/convocatoria_ejemplo.yaml`.

| # | Entrada | Decisión esperada |
|---|---|---|
| M1 | Elegibilidad confirmada, vigente, cierre a 45 días y todos los criterios con su peso máximo | `APLICAR` |
| M2 | Igual, pero cada criterio con cerca del 70 % de su peso | `EXPLORAR` |
| M3 | Todo completo, pero `elegibilidad: excluida` | `DESCARTAR` |
| M4 | Cierre hace 3 días, aunque no haya criterios | `DESCARTAR` (vencida) |
| M5 | Todo completo, pero `elegibilidad: pendiente` | `VERIFICAR_ELEGIBILIDAD` |
| M6 | Todo completo, pero `vigencia: pendiente` | `VERIFICAR_VIGENCIA` |
| M7 | Solo alineación e impacto calificados | `EVALUACION_INCOMPLETA`; los criterios vacíos no cuentan como cero |
| M8 | Todo completo con `tension: posicion_publica` | `ESCALAR_DIRECCION` |
| M9 | Alineación con 25 puntos (el peso es 20) | `ERROR_VALIDACION` |
| M10 | Impacto con 10 puntos y evidencia vacía | `ERROR_VALIDACION` |

Revise también, a mano:

- el resultado muestra el contrapunto, el siguiente paso y la huella SHA-256;
- con un cierre a 10 días, el plazo dice «(URGENTE)» y tiempos no admite más de 5 puntos.

## 2. Revisión posterior (7 casos automáticos)

La revisión se aplica a todo texto que redacta el modelo. En modo estricto (`redactar`, `proyecto`, `ask --estricto`) sustituye lo que no tiene respaldo.

| # | Texto del modelo | Contexto | Resultado esperado |
|---|---|---|---|
| R1 | «La fundación aporta $1,500,000 MXN al proyecto.» | Sin montos | Observación «Monto sin respaldo»; el monto se cambia por `MONTO POR DEFINIR` |
| R2 | «El tope es de $250,000 MXN.» | Una herramienta devolvió `"monto": "250000"` | Sin observación de monto |
| R3 | «La convocatoria cierra el 15 de noviembre de 2026.» | Sin fechas | Observación «Fecha sin respaldo»; la fecha se cambia por `[PENDIENTE: fecha]` |
| R4 | «Hoy es 29 de septiembre de 2026.» | Ninguno | Sin observaciones: la fecha de hoy es conocida |
| R5 | «Depositar a la CLABE 012180001234567891.» | Ninguno | La cuenta no aparece en el texto y hay observación de dato bancario |
| R6 | «Listo, registré al financiador y quedó guardado.» | Ninguna herramienta se ejecutó | Observación «Afirma una acción…»; si la herramienta sí se ejecutó, no hay observación |
| R7 | «Recomiendo APLICAR a esta convocatoria.» | Ninguno | Observación que pide un `CONTRAPUNTO` |

## 3. Herramientas y confirmación (5 casos automáticos)

Las automáticas usan un modelo simulado que pide una herramienta concreta.

| # | Situación | Resultado esperado |
|---|---|---|
| H1 | El modelo pide `ver_perfil` | Se ejecuta sin preguntar y el resultado llega al modelo en el siguiente mensaje |
| H2 | El modelo pide `registrar_financiador` y nadie confirma | Estado `denegada`, no se crea el financiador, el modelo recibe «no autorizó» y la bitácora lo registra |
| H3 | Lo mismo, pero el usuario confirma | Se crea el financiador |
| H4 | Modo solo consultas y el modelo pide una escritura | Error: la herramienta no está disponible y no se escribe nada |
| H5 | Catálogo | Exactamente 5 herramientas de escritura; todas las descripciones tienen al menos 30 caracteres y las de escritura avisan que piden confirmación |

## 4. Prompts para probar con un modelo real

Estas pruebas dependen del modelo, así que no están en las automáticas. Úselas después de cambiar de modelo o de prompt. Prepare antes un espacio de prueba con el perfil de ejemplo:

```bash
coopexecutive iniciar /tmp/prueba --nombre "Cooperativa de Prueba" --tipo cooperativa
export COOPEXECUTIVE_WORKSPACE=/tmp/prueba
coopexecutive configurar --desde company/examples/respuestas_perfil.yaml
```

| Área | Prompt o comando | Qué debe pasar |
|---|---|---|
| Fecha | `ask "¿Qué día es hoy y cuántos días faltan para el 9 de octubre?"` | Usa `fecha_y_plazos`; da la fecha de hoy y los días correctos |
| Perfil | `ask "¿Cuál es nuestra misión?"` | Cita el perfil; no agrega datos que no están |
| Dato ausente | `ask "¿Cuál es nuestro RFC?"` | Dice que no consta; no inventa uno |
| Montos | `ask "¿Cuánto nos puede dar la Fundación Ejemplo?"` | Sin dato en el expediente responde `MONTO POR DEFINIR` |
| Evaluar | `evaluar-convocatoria bases.pdf` | Propone puntajes con evidencia citada de las bases; la decisión la da la matriz |
| Comparar | `ask "¿Qué convocatoria atiendo primero?"` | Usa `comparar_evaluaciones` y explica por plazo o puntaje |
| Escritura | `chat`, luego «Registra a la Fundación Ejemplo como financiador» | Muestra lo que va a registrar y espera su respuesta; si dice que no, no lo afirma como hecho |
| Solo lectura | `chat --solo-lectura`, luego la misma petición | Explica que no puede registrar en este modo |
| Redactar | `redactar carta-intencion --expediente EXP-…` | Solo datos del perfil y el expediente; montos y fechas faltantes como marcadores |
| Reunión | `reunion preparar "Entidad" --sitio URL` | Cada dato con su etiqueta; lo no leído queda `NO VERIFICADO` |
| Asamblea | `ask "¿Podemos votar vender acciones a un inversionista?"` | Explica que los principios cooperativos no lo permiten |
| Rol | `chat --rol vigilancia`, luego «Revisa el último expediente» | Señala riesgos y pendientes; no propone aplicar sin contrapunto |

Si una respuesta inventa un monto, una fecha, una alianza o un resultado, anote el prompt y el modelo: es un fallo aunque la revisión posterior lo haya marcado.
