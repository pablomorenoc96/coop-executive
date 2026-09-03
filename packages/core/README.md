# CoopExecutive 🏛️🌱
> **El Sistema Directivo Colegiado y Agente Procurador de Fondos con IA para Cooperativas, Asociaciones Civiles (A.C. / ONGs) y la Economía Social.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Modelos Libres](https://img.shields.io/badge/Modelos-OpenRouter%20:free%20%7C%20Ollama-orange.svg)](#modelos-y-costo-cero)
[![Filosofía MORECAM](https://img.shields.io/badge/Filosof%C3%ADa-Soberan%C3%ADa%20T%C3%A9cnica-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

**CoopExecutive** nace como una **antítesis directa al modelo de Silicon Valley** encarnado por herramientas como [OpenExecutive](https://github.com/SenteLabsAI/OpenExecutive). Mientras que el software tradicional asume corporaciones con juntas de accionistas, capital de riesgo (VC), búsqueda de *exits* y maximización de utilidades individuales, **CoopExecutive** está diseñado desde sus cimientos para las **organizaciones democráticas, cooperativas de producción y servicios, asociaciones civiles y proyectos de soberanía comunitaria**.

Incorpora de forma nativa al **Agente Procurador de Fondos (Grant Procurement Agent)**, una herramienta especializada en captar fondos no reembolsables y cooperaciones internacionales (a través de plataformas como [FundsforNGOs](https://www.fundsforngos.org/), agencias bilaterales y fundaciones climáticas/sociales).

---

## ⚖️ La Antítesis: Silicon Valley vs. CoopExecutive

| Dimensión | OpenExecutive (Silicon Valley) | CoopExecutive (Economía Social y Solidaria) |
| :--- | :--- | :--- |
| **Poder de Decisión** | *Un dólar, un voto* (Junta de Accionistas / Inversionistas VC). | **Un socio, un voto** (Asamblea General Democrática). |
| **Órgano de Control** | Comités de auditoría de fondos de inversión privados. | **Consejo de Vigilancia** (auditoría interna democrática y ética). |
| **Financiamiento** | Deuda predatoria, rondas de capital (Seed, Serie A), dilución. | **Flujo operativo bootstrap + Grants y Convocatorias Internacionales ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Finanzas** | Maximizar EBITDA y dividendos para socios capitalistas. | **Fondos Estatutarios Obligatorios (LGSC):** Fondo de Reserva, Previsión Social y Educación Cooperativa. |
| **Régimen Legal** | S.A.P.I., S.A. de C.V., Delaware C-Corp. | Ley General de Sociedades Cooperativas (LGSC), Código Civil (A.C.), Donatarias Autorizadas (SAT). |
| **Propósito Tecnológico** | Monopolios cerrados con obsolescencia y extracción de rentas. | **Soberanía tecnológica, herramientas abiertas, energía limpia y beneficio común.** |
| **Acceso y Costo** | Licencias privativas caras, plataformas cerradas (M365). | **100% Código Abierto, libre acceso y compatible con modelos gratuitos (OpenRouter / Ollama).** |

---

## ✨ Capacidades Principales

### 1. Agente Procurador de Fondos (*Grant Procurement Agent*)
Inspirado y evolucionado a partir de las experiencias de campo con organizaciones de la sociedad civil (Red por la Ciberseguridad, Causas para la Transformación A.C. y REACCIONA):
* **Evaluación de Convocatorias (0 a 100 puntos):** Analiza bases de convocatorias en segundos extrayendo fechas, montos, áreas temáticas y requisitos, aplicando una matriz de 8 dimensiones para dictaminar: *APLICAR*, *EXPLORAR*, *CONDICIONAL* o *NO APLICAR*.
* **Metodología de Marco Lógico (MML):** Genera automáticamente Árboles de Problemas, Árboles de Objetivos y la Matriz de Indicadores de Resultados (MIR).
* **Teoría del Cambio (ToC):** Estructura la cadena causal desde actividades e insumos hasta impactos sostenibles a largo plazo.
* **Alineación con los ODS:** Vinculación estricta con la Agenda 2030 de la ONU (ODS 7: Energía Limpia, ODS 8: Trabajo Decente, ODS 9: Industria/Innovación, ODS 12: Producción Responsable).
* **Presupuestos Auditables:** Desglose riguroso de CAPEX, OPEX, personal técnico, contrapartidas y gastos administrativos elegibles.
* **Redacción Bilingüe:** Generación de propuestas en Español y en Inglés conforme a los estándares de organismos internacionales (BID, UE, agencias de cooperación, fundaciones climáticas).

### 2. Consejo Directivo y de Vigilancia Colegiado
El sistema pone a disposición de la Asamblea un consejo de agentes especializados:
* **Director de Impacto y Principios Cooperativos:** Vela por la misión social y la adhesión a los 7 principios cooperativos universales.
* **Gestor de Fondos Estatutarios:** Controla el Fondo de Reserva, Fondo de Previsión Social (salud/retiro) y Fondo de Educación Cooperativa conforme a la LGSC.
* **Consejo de Vigilancia (Auditoría Democrática):** Detecta desvíos estatutarios, conflictos de interés y asegura la máxima transparencia para la asamblea.
* **Asesor Jurídico en Economía Social:** Especialista en la Ley General de Sociedades Cooperativas, Código Civil para A.C. y trámites ante el SAT (Donatarias Autorizadas).
* **Secretaría de Actas y Gobernanza Asamblearia:** Redacción de convocatorias formales, órdenes del día, cómputo de quórum y actas de asamblea.
* **Desarrollo Tecnológico Comunitario:** Fomenta la infraestructura abierta, hardware libre, energías limpias y formación técnica continua.
* **Comunicación y Vinculación Social:** Difusión ética, atracción de nuevos socios/asociados y alianzas con otras cooperativas.

---

## 🚀 Inicio Rápido

### Requisitos Previos
- Python 3.11 o superior instalado.
- [uv](https://docs.astral.sh/uv/) (el gestor de paquetes ultrarrápido).

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/coop-executive.git
cd coop-executive/packages/core
```

### 2. Configurar variables de entorno
Copia el archivo de ejemplo:
```bash
cp ../../.env.example ../../.env
```

Edita `.env` para elegir tu proveedor de IA:
* **Opción Gratuita en la Nube (Recomendada):** Coloca tu clave gratuita de [OpenRouter](https://openrouter.ai/keys) (`OPENROUTER_API_KEY=sk-or-v1-...`) y usa modelos como `minimax/minimax-m3:free` o `nvidia/nemotron-3-super-120b-a12b:free` a costo $0.00.
* **Opción Local Ilimitada (Sin internet):** Si tienes [Ollama](https://ollama.com/) instalado, activa `LOCAL_MODELS_ENABLED=true` y corre modelos locales como `llama3.1` o `qwen2.5`.

### 3. Evaluar tu primera convocatoria
```powershell
uv run coopexecutive evaluar-convocatoria "https://www.fundsforngos.org/latest-funds-for-ngos/climate-transition-grants/"
```

### 4. Iniciar el chat con el Director Colegiado
```powershell
uv run coopexecutive chat
```

---

## 📖 Documentación
* [Manifiesto de Economía Social y Soberanía Técnica](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)
* [Guía Práctica de Marco Lógico y Fondos Internacionales](docs/GUIA_MARCO_LOGICO.md)
* [Guía de Gobernanza y Fondos Estatutarios (LGSC México)](docs/GUIA_FONDOS_ESTATUTARIOS.md)

---

## 🤝 Filosofía y Origen
CoopExecutive fue concebido bajo la filosofía de **MORECAM** (rigor de ingeniería, soberanía técnica y rechazo a la especulación financiera) y enriquecido con el trabajo práctico desarrollado en proyectos de procuración de fondos para la sociedad civil organizada en México.

**Licencia:** [Apache 2.0](LICENSE) — Libre para usar, modificar, cooperativizar y compartir.
