# CoopExecutive

![CoopExecutive Banner](assets/banner.png)

> **Sistema Directivo Colegiado y Agente Procurador de Fondos con IA para Cooperativas, Asociaciones Civiles (A.C. / ONGs) y la Economía Social.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Modelos Libres](https://img.shields.io/badge/Modelos-Gratis%20y%20Comerciales-orange.svg)](#configuración-de-modelos-de-ia-gratis-locales-y-de-pago)
[![Manifiesto Economía Social](https://img.shields.io/badge/Filosof%C3%ADa-Econom%C3%ADa%20Social-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

[🇺🇸 Read in English](README.md) | [📢 Kit de Difusión en Redes](docs/KIT_DIFUSION_REDES.md)

**CoopExecutive** es una alternativa de código abierto al modelo corporativo tradicional. Mientras las herramientas convencionales de Silicon Valley asumen juntas de accionistas, capital de riesgo y reparto de utilidades privadas, este sistema está diseñado para **organizaciones democráticas**: asambleas soberanas, fondos de reserva colectivos y proyectos de beneficio común.

---

## ¿Qué es técnicamente CoopExecutive?

En términos de ingeniería de software e inteligencia artificial, **CoopExecutive no es un simple chatbot ni un generador de texto pasivo**: es un **Agente Autónomo de Inteligencia Artificial (Vertical AI Agent)** construido sobre 5 pilares arquitectónicos formales:

```
                   ┌────────────────────────────────────────────────────────┐
                   │                     ENTORNO (World)                    │
                   │  (profile.yaml, LGSC, Convocatorias BID, CLI, Web)     │
                   └───────────────▲────────────────────────┬───────────────┘
                                   │                        │
                          Percepción (Sensores)        Acción (Efectores)
                                   │                        │
       ┌───────────────────────────┴────────────────────────▼───────────────────────────┐
       │                             AGENTE CoopExecutive                               │
       │                                                                                │
       │   ┌────────────────────────────────────────────────────────────────────────┐   │
       │   │                       ORQUESTADOR COLEGIADO                            │   │
       │   │  (Router de roles: Procurador, Vigilancia, Legal, Finanzas, Asamblea)  │   │
       │   └──────┬───────────────────────┬──────────────────────────┬──────────────┘   │
       │          │                       │                          │                  │
       │   ┌──────▼──────┐         ┌──────▼──────┐            ┌──────▼──────┐           │
       │   │   MEMORIA   │         │    MOTOR    │            │ HERRAMIENTAS│           │
       │   │  EPISÓDICA  │         │ INFERENCIA  │            │ (TOOL-USE)  │           │
       │   │  (SQLite)   │         │  Universal  │            │             │           │
       │   │ - Acuerdos  │         │  (Fallback  │            │ - MML 4x4   │           │
       │   │ - Votaciones│         │  Resiliente)│            │ - Rúbrica   │           │
       │   │ - Dossiers  │         │             │            │ - Presupuesto│          │
       │   └─────────────┘         └─────────────┘            └─────────────┘           │
       │                                                                                │
       │   ┌────────────────────────────────────────────────────────────────────────┐   │
       │   │              SALVAGUARDAS ESTATUTARIAS (Guardrails Duros)              │   │
       │   │      Invariantes LGSC: 15% Reserva, 10% Previsión, 0% Dilución         │   │
       │   └────────────────────────────────────────────────────────────────────────┘   │
       └────────────────────────────────────────────────────────────────────────────────┘
```

1. **Percepción del Entorno (*Perception*):** Inspecciona el estado institucional (`company/profile.yaml`), analiza las leyes cooperativas vigentes y procesa convocatorias internacionales en tiempo real.
2. **Espacio de Acción y Herramientas (*Tool-Use / Actuation*):** Ejecuta código determinista: calcula presupuestos auditables con contrapartidas en especie, genera matrices de Marco Lógico 4x4 y compila expedientes técnicos oficiales (*dossiers*).
3. **Memoria Episódica Persistente (*Episodic Memory*):** Base de datos relacional SQLite (`coop_memory.db`) que almacena acuerdos asamblearios, evaluaciones de convocatorias y cédulas de votación entre sesiones.
4. **Deliberación y Toma de Decisiones (*Reasoning*):** Aplica rúbricas multicriterio de 100 puntos y emite dictámenes de negocio vinculantes (`APLICAR`, `OBSERVAR` o `RECHAZAR`).
5. **Salvaguardas Estatutarias Duras (*Invariants & Guardrails*):** Reglas inviolables programadas en el núcleo: blindaje de fondos irrepartibles (15% Reserva, 10% Previsión, 10% Educación) y veto inmediato ante propuestas de dilución de capital.

---

## La Antítesis: Silicon Valley vs. CoopExecutive

| Dimensión | Enfoque de Silicon Valley | CoopExecutive (Economía Social) |
| :--- | :--- | :--- |
| **Poder de Decisión** | Ponderado por capital (*un dólar, un voto*). | Democrático (*un socio, un voto* — Asamblea General). |
| **Supervisión** | Comités de fondos de inversión privados. | **Consejo de Vigilancia** interno e independiente. |
| **Financiamiento** | Deuda, dilución de capital y búsqueda de venta (*exit*). | Operación sostenible + **Subvenciones no reembolsables ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Excedentes** | Maximización de utilidades para accionistas. | **Fondos Estatutarios Blindados:** Reserva (15%), Previsión Social (10%), Educación (10%). |
| **Régimen Legal** | Sociedades anónimas mercantiles (S.A., Delaware C-Corp). | Sociedades Cooperativas (LGSC) y Asociaciones Civiles (A.C.). |
| **Infraestructura** | Software privativo con suscripciones recurrentes. | **100% Código Abierto, modelos libres sin costo ($0.00) y de pago opcionales.** |

---

## Demostración Visual

![Demostración de CoopExecutive](assets/demo.gif)

---

## Capacidades Principales

### 1. Agente Procurador de Fondos (*Grant Procurement Agent*)
* **Evaluación de Convocatorias (Rúbrica de 100 Puntos):** Analiza bases de financiamiento en segundos extrayendo fechas límite, montos y criterios mediante 8 dimensiones ponderadas (*APLICAR*, *EXPLORAR*, *CONDICIONAL* o *NO APLICAR*).
* **Metodología de Marco Lógico (MML):** Genera automáticamente Árboles de Problemas, Árboles de Objetivos y la Matriz de Indicadores de Resultados (MIR) 4x4.
* **Teoría del Cambio (ToC):** Vincula las actividades del proyecto con los Objetivos de Desarrollo Sostenible (ODS 7, 8, 9, 12, 13).
* **Expediente Técnico Multilateral (Dossier):** Ensambla expedientes completos listos para postular ante el BID, Horizonte Europa y fundaciones filantrópicas.

### 2. Gobernanza Democrática y Votación Soberana (Un Socio = Un Voto)
* **Emisión de Votos:** Registro y acreditación de cédulas de voto de socios con verificación de unicidad (prohibido votar dos veces).
* **Cálculo Automático de Cuórum Legal:** Verificación en tiempo real del umbral legal mínimo (50% + 1 socios del padrón conforme a la LGSC).
* **Escrutinio Criptográfico:** Emisión de actas oficiales resolutivas con firma y hash SHA-256 inmutable.
* **Veto Programático Anti-Dilución:** Rechazo automático de propuestas que intenten privatizar fondos irrepartibles o vender participaciones societarias.

### 3. Consejo Directivo y de Vigilancia Colegiado
* **Consejo de Vigilancia:** Auditoría democrática interna y observancia de los estatutos.
* **Asesor Jurídico en Economía Social:** Marco legal cooperativo, donatarias autorizadas y convenios de tecnología abierta.
* **Gestor de Finanzas Solidarias:** Control y blindaje de los fondos de reserva, previsión social y educación cooperativa.
* **Secretaría de Actas:** Redacción formal de convocatorias, verificación de cuórum y minutas de asamblea.

---

## Inicio Rápido

```bash
git clone https://github.com/pablomorenoc96/coop-executive.git
cd coop-executive/packages/core

# Instalar dependencias con uv:
uv sync --all-groups --extra dev

# Configurar variables de entorno:
cp ../../.env.example .env

# Evaluar una convocatoria con la rúbrica de 100 puntos:
uv run coopexecutive evaluar "Convocatoria_Energia_Limpia_BID.txt"

# Generar un expediente técnico completo para postulación multilateral:
uv run coopexecutive dossier "Microrredes Rurales Comunitarias" --donante "BID"

# Registrar y votar una propuesta en Asamblea General (Un Socio = Un Voto):
uv run coopexecutive propuesta "Postulación al Fondo BID 2026" -d "Aprobación de la contrapartida técnica comunal"
uv run coopexecutive votar 1 --socio-id "SOC-001" --socio-nombre "Elena Gómez" --voto "A_FAVOR"
uv run coopexecutive escrutinio 1 --padron 12

# Abrir el Panel de Control Web interactivo:
uv run coopexecutive dashboard

# Iniciar sesión interactiva con el consejo directivo:
uv run coopexecutive chat
```

---

## Configuración de Modelos de IA (Gratis, Locales y de Pago)

CoopExecutive es un motor multimodelo soberano. Ofrece tres vías de conexión configurables en `.env`:
1. **Ruta Gratuita en la Nube ($0.00):** Obtén una clave sin costo en [OpenRouter](https://openrouter.ai/keys) (no requiere tarjeta bancaria). Accede a modelos con soporte de herramientas como `minimax/minimax-m3:free` y `nvidia/nemotron-3-super-120b-a12b:free` con conmutación automática ante errores 429.
2. **Ruta Local Desconectada (100% Privada y Gratis):** Si cuentas con [Ollama](https://ollama.com/), cambia `LOCAL_MODELS_ENABLED=true` para operar sin conexión con modelos locales como `llama3.1` o `qwen2.5`.
3. **APIs Comerciales y de Pago (Opcional):** Si tu cooperativa u organización dispone de suscripciones o créditos institucionales, puedes conectar directamente tus claves de **OpenAI** (`gpt-4o`, `o1`, `o3-mini`), **Anthropic** (`claude-3-7-sonnet`, `claude-3-5-sonnet`), **Google Gemini** (`gemini-2.0-flash`), **Groq**, **Mistral**, **DeepSeek** o gateways compatibles con OpenAI (`vLLM`, `Azure OpenAI`). El sistema enruta automáticamente cada consulta según el proveedor activo.

---

## Documentación Técnica
* [Arquitectura del Sistema y Mecanismo de Resiliencia](ARCHITECTURE.md)
* [Manifiesto de Economía Social](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)
* [Guía Práctica de Marco Lógico](docs/GUIA_MARCO_LOGICO.md)
* [Guía de Fondos Estatutarios y Gobernanza LGSC](docs/GUIA_FONDOS_ESTATUTARIOS.md)
* [Guía para Contribuir](CONTRIBUTING.md)
* [Registro de Versiones](CHANGELOG.md)

---

## Licencia
Distribuido bajo licencia [MIT](LICENSE). Libre para uso, modificación y distribución comunitaria.
