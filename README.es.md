# CoopExecutive

![CoopExecutive Banner](assets/banner.png)

> **Sistema Directivo Colegiado y Agente Procurador de Fondos con IA para Cooperativas, Asociaciones Civiles (A.C. / ONGs) y la Economía Social.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Modelos Libres](https://img.shields.io/badge/Modelos-OpenRouter%20:free%20%7C%20Ollama-orange.svg)](#configuración-a-costo-cero)
[![Manifiesto Economía Social](https://img.shields.io/badge/Filosof%C3%ADa-Econom%C3%ADa%20Social-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

[🇺🇸 Read in English](README.md) | [📢 Kit de Difusión en Redes](docs/KIT_DIFUSION_REDES.md)

**CoopExecutive** es una alternativa de código abierto al modelo corporativo tradicional. Mientras las herramientas convencionales de Silicon Valley asumen juntas de accionistas, capital de riesgo y reparto de utilidades privadas, este sistema está diseñado para **organizaciones democráticas**: asambleas soberanas, fondos de reserva colectivos y proyectos de beneficio común.

Integra un **Agente Procurador de Fondos** para evaluar y redactar propuestas a fondos multilaterales y convocatorias de plataformas como [FundsforNGOs](https://www.fundsforngos.org/), agencias de cooperación internacional y fundaciones ambientales.

---

## La Antítesis: Silicon Valley vs. CoopExecutive

| Dimensión | Enfoque de Silicon Valley | CoopExecutive (Economía Social) |
| :--- | :--- | :--- |
| **Poder de Decisión** | Ponderado por capital (*un dólar, un voto*). | Democrático (*un socio, un voto* — Asamblea General). |
| **Supervisión** | Comités de fondos de inversión privados. | **Consejo de Vigilancia** interno e independiente. |
| **Financiamiento** | Deuda, dilución de capital y búsqueda de venta (*exit*). | Operación sostenible + **Subvenciones no reembolsables ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Excedentes** | Maximización de utilidades para accionistas. | **Fondos Estatutarios Blindados:** Reserva (15%), Previsión Social (10%), Educación (10%). |
| **Régimen Legal** | Sociedades anónimas mercantiles (S.A., Delaware C-Corp). | Sociedades Cooperativas (LGSC) y Asociaciones Civiles (A.C.). |
| **Infraestructura** | Software privativo con suscripciones recurrentes. | **100% Código Abierto, modelos libres sin costo ($0.00).** |

---

## Demostración Visual

![Demostración de CoopExecutive](assets/demo.gif)

---

## Capacidades Principales

### 1. Agente Procurador de Fondos (*Grant Procurement Agent*)
* **Evaluación de Convocatorias (Rúbrica de 100 Puntos):** Analiza bases de financiamiento en segundos extrayendo fechas límite, montos y criterios mediante 8 dimensiones ponderadas (*APLICAR*, *EXPLORAR*, *CONDICIONAL* o *NO APLICAR*).
* **Metodología de Marco Lógico (MML):** Genera automáticamente Árboles de Problemas, Árboles de Objetivos y la Matriz de Indicadores de Resultados (MIR) 4x4.
* **Teoría del Cambio (ToC):** Vincula las actividades del proyecto con los Objetivos de Desarrollo Sostenible (ODS 7, 8, 9, 12, 13).
* **Presupuestación Auditable:** Desglosa con rigor costos de personal, equipamiento (CAPEX), operación de campo (OPEX) y contrapartidas valorizadas.

### 2. Consejo Directivo y de Vigilancia Colegiado
* **Consejo de Vigilancia:** Auditoría democrática interna y observancia de los estatutos.
* **Asesor Jurídico en Economía Social:** Marco legal cooperativo, donatarias autorizadas y convenios de tecnología abierta.
* **Gestor de Finanzas Solidarias:** Control y blindaje de los fondos de reserva, previsión social y educación cooperativa.
* **Desarrollo Tecnológico Comunitario:** Fomento de infraestructura abierta, energías limpias y formación técnica.
* **Secretaría de Actas:** Redacción formal de convocatorias, verificación de quórum y minutas de asamblea.

---

## Inicio Rápido

```bash
git clone https://github.com/pablomorenoc96/coop-executive.git
cd coop-executive/packages/core
cp ../../.env.example ../../.env
```

### Comandos de Ejemplo:
```powershell
# Ver perfil institucional y fondos estatutarios activos:
uv run coopexecutive info

# Generar una Matriz de Marco Lógico completa:
uv run coopexecutive marco-logico "Energía Limpia Comunitaria y Capacitación Técnica"

# Evaluar una convocatoria de financiamiento:
uv run coopexecutive evaluar-convocatoria "https://www.fundsforngos.org/..."

# Estructurar un presupuesto auditable:
uv run coopexecutive presupuesto "Microplanta de Automatización Rural"

# Generar un dossier formal de postulación técnica y financiera:
uv run coopexecutive dossier "Electrificación Limpia de Talleres"

# Abrir el Panel de Control Web y Gobernanza Colegiada:
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
