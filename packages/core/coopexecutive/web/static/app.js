"use strict";

// Panel local de CoopExecutive. Todo el texto se inserta con textContent; nunca se interpreta HTML que venga de los datos.

const TOKEN_CLAVE = "coopexecutive-token";

function leerToken() {
  const hash = new URLSearchParams(location.hash.slice(1));
  let token = hash.get("token");
  try {
    if (token) sessionStorage.setItem(TOKEN_CLAVE, token);
    else token = sessionStorage.getItem(TOKEN_CLAVE);
  } catch (_) { /* sin almacenamiento: se usa el del enlace */ }
  if (location.hash) history.replaceState(null, "", location.pathname);
  return token || "";
}

const TOKEN = leerToken();
const vista = document.getElementById("vista");
const aviso = document.getElementById("aviso");
const chat = document.getElementById("chat");

// --- Utilidades de DOM -------------------------------------------------------------------------

function el(etiqueta, props = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(props)) {
    if (k === "clase") nodo.className = v;
    else if (k === "texto") nodo.textContent = v;
    else if (k.startsWith("on")) nodo.addEventListener(k.slice(2), v);
    else nodo.setAttribute(k, v);
  }
  for (const h of hijos.flat()) {
    if (h === null || h === undefined || h === false) continue;
    nodo.append(h instanceof Node ? h : document.createTextNode(String(h)));
  }
  return nodo;
}

const vacio = (texto = "Sin datos") => el("div", { clase: "vacio", texto });
const guion = (v) => (v === null || v === undefined || v === "" ? "—" : String(v));

function chip(texto, tipo = "") {
  return el("span", { clase: `chip ${tipo}`.trim(), texto });
}

function chipDecision(decision) {
  const tipo = { APLICAR: "", EXPLORAR: "alerta", CONDICIONAL: "alerta" }[decision] ?? "error";
  return chip(decision, tipo);
}

function chipEstado(estado) {
  return chip(estado, { ok: "", denegada: "alerta" }[estado] ?? "error");
}

function tabla(columnas, filas, alHacerClic) {
  if (!filas.length) return vacio();
  const cabecera = el("tr", {}, columnas.map(([titulo]) => el("th", { texto: titulo })));
  const cuerpo = filas.map((fila) => {
    const tr = el("tr", alHacerClic ? { clase: "clic", tabindex: "0" } : {},
      columnas.map(([, valor]) => {
        const v = valor(fila);
        return el("td", {}, v instanceof Node ? v : guion(v));
      }));
    if (alHacerClic) {
      tr.addEventListener("click", () => alHacerClic(fila));
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter") alHacerClic(fila); });
    }
    return tr;
  });
  return el("div", { clase: "tabla" }, el("table", {}, el("thead", {}, cabecera), el("tbody", {}, cuerpo)));
}

function campos(pares) {
  return el("dl", { clase: "campos" }, pares.flatMap(([k, v]) => [el("dt", { texto: k }), el("dd", {}, guion(v))]));
}

function bloque(titulo, ...contenido) {
  return el("section", { clase: "bloque" }, titulo ? el("h2", { texto: titulo }) : null, ...contenido);
}

function mostrarError(texto) {
  aviso.hidden = !texto;
  aviso.textContent = texto || "";
}

// --- API --------------------------------------------------------------------------------------

async function api(ruta, opciones = {}) {
  const respuesta = await fetch(`/api/${ruta}`, {
    ...opciones,
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json", ...(opciones.headers || {}) },
  });
  if (!respuesta.ok) {
    let detalle = `Error ${respuesta.status}`;
    try { detalle = (await respuesta.json()).detail || detalle; } catch (_) { /* sin cuerpo */ }
    throw new Error(detalle);
  }
  return respuesta.json();
}

// --- Vistas -------------------------------------------------------------------------------------

const VISTAS = {
  async resumen() {
    const e = await api("estado");
    const c = e.conteos;
    const tarjeta = (cifra, etiqueta) => el("div", { clase: "tarjeta" },
      el("div", { clase: "cifra", texto: String(cifra) }), el("div", { clase: "etiqueta", texto: etiqueta }));
    const ev = await api("evaluaciones?limite=5");
    return [
      el("div", { clase: "tarjetas" },
        tarjeta(c.financiadores, "Financiadores"),
        tarjeta(c.expedientes_abiertos, "Expedientes abiertos"),
        tarjeta(c.evaluaciones, "Evaluaciones"),
        tarjeta(c.documentos, "Documentos")),
      bloque("Evaluaciones recientes", tabla([
        ["Convocatoria", (f) => f.convocatoria],
        ["Decisión", (f) => chipDecision(f.decision)],
        ["Puntaje", (f) => f.puntaje],
        ["Plazo", (f) => f.plazo],
      ], ev.evaluaciones)),
      bloque("Configuración", campos([
        ["Hoy", e.hoy_texto], ["Proveedor", e.proveedor], ["Modelo", e.modelo], ["Versión", e.version],
      ])),
    ];
  },

  async perfil() {
    const p = await api("perfil");
    return [
      bloque(p.nombre, campos([["Figura", p.figura], ["Ejes", (p.ejes || []).join(", ")],
        ["Asamblea", p.tiene_asamblea ? "Sí" : "No"]])),
      bloque("Perfil completo", el("pre", { texto: p.perfil })),
    ];
  },

  async financiadores() {
    const d = await api("financiadores?limite=100");
    return bloque("Financiadores", tabla([
      ["Folio", (f) => f.folio], ["Organización", (f) => f.organizacion], ["Proyecto", (f) => f.proyecto],
      ["Tipo", (f) => f.tipo], ["Estatus", (f) => f.estatus], ["Solicitado", (f) => f.monto_solicitado_texto],
      ["Seguimiento", (f) => f.seguimiento],
    ], d.financiadores));
  },

  async expedientes() {
    const d = await api("expedientes?estado=todos&limite=200");
    return bloque("Expedientes", tabla([
      ["Folio", (x) => x.folio], ["Título", (x) => x.titulo], ["Responsable", (x) => x.responsable],
      ["Fecha límite", (x) => x.fecha_limite], ["Monto", (x) => x.monto_texto],
      ["Estado", (x) => chip(x.abierto ? "abierto" : "cerrado", x.abierto ? "" : "alerta")],
    ], d.expedientes, (x) => abrirExpediente(x.folio)));
  },

  async evaluaciones() {
    const d = await api("evaluaciones?limite=50");
    return bloque("Evaluaciones con la matriz", tabla([
      ["Id", (f) => f.id], ["Convocatoria", (f) => f.convocatoria], ["Financiador", (f) => f.financiador],
      ["Decisión", (f) => chipDecision(f.decision)], ["Puntaje", (f) => f.puntaje], ["Plazo", (f) => f.plazo],
      ["Expediente", (f) => f.expediente], ["Evaluada", (f) => f.fecha_evaluacion],
    ], d.evaluaciones));
  },

  async documentos() {
    const d = await api("documentos?limite=100");
    return bloque("Documentos generados", tabla([
      ["Id", (x) => x.id], ["Tipo", (x) => x.tipo], ["Archivo", (x) => x.ruta.split(/[\\/]/).pop()],
      ["Expediente", (x) => x.expediente_folio], ["Huella", (x) => x.sha256.slice(0, 12)],
      ["Creado", (x) => x.creado_en],
    ], d.documentos));
  },

  async monitoreo() {
    const { monitoreo: m } = await api("monitoreo");
    if (!m) return vacio("Sin monitoreos. Ejecute «coopexecutive monitorear» o pídalo en el chat.");
    const lista = (avisos) => tabla([
      ["Convocatoria", (a) => (/^https?:\/\//i.test(a.enlace || "")
        ? el("a", { href: a.enlace, target: "_blank", rel: "noopener noreferrer", texto: a.titulo })
        : a.titulo)],
      ["Fuente", (a) => a.fuente], ["Plazo", (a) => a.plazo], ["Temas", (a) => (a.coincidencias || []).join(", ")],
    ], avisos);
    return [
      bloque(`Monitoreo del ${m.ejecutado_en}`, campos([["Temas", (m.temas || []).join(", ")],
        ["Fuentes consultadas", m.consultadas], ["Fuentes con falla", (m.fallidas || []).length]])),
      bloque("Priorizadas", lista(m.priorizadas || [])),
      bloque("Por revisar (vigencia no verificada)", lista(m.por_revisar || [])),
    ];
  },

  async asamblea() {
    const d = await api("asamblea");
    return bloque(`Asamblea · ${d.padron_activo} socio(s) activo(s)`, tabla([
      ["Id", (p) => p.id], ["Propuesta", (p) => p.title], ["Categoría", (p) => p.category],
      ["Estado", (p) => chip(p.status, p.status === "rechazada" ? "error" : p.status === "abierta" ? "alerta" : "")],
      ["Creada", (p) => p.created_at],
    ], d.propuestas));
  },

  async bitacora() {
    const d = await api("bitacora?limite=200");
    const v = d.verificacion;
    const estado = v.integra
      ? chip(`Íntegra · ${v.total} registro(s)`)
      : chip(`Alterada en el registro ${v.roto_en}: ${v.motivo}`, "error");
    return bloque("Bitácora de acciones", el("p", {}, estado), tabla([
      ["Id", (r) => r.id], ["Fecha (UTC)", (r) => r.registrado_en], ["Canal", (r) => r.canal],
      ["Acción", (r) => r.accion], ["Estado", (r) => chipEstado(r.estado)], ["Resultado", (r) => r.resultado],
    ], d.registros));
  },
};

async function abrirExpediente(folio) {
  mostrarError("");
  try {
    const d = await api(`expedientes/${encodeURIComponent(folio)}`);
    const x = d.expediente;
    vista.replaceChildren(
      el("button", { clase: "volver", texto: "← Expedientes", onclick: () => mostrar("expedientes") }),
      bloque(`${x.folio} · ${x.titulo}`, campos([
        ["Tipo", x.tipo], ["Entidad", x.entidad], ["Objetivo", x.objetivo], ["Responsable", x.responsable],
        ["Fecha límite", x.fecha_limite], ["Monto", x.monto_texto], ["Estado", x.abierto ? "Abierto" : "Cerrado"],
      ])),
      bloque("Avances", tabla([["Fecha", (a) => a.registrado_en], ["Estado", (a) => a.estado],
        ["Pendientes", (a) => a.pendientes], ["Siguiente acción", (a) => a.siguiente_accion],
        ["Origen", (a) => a.origen]], d.avances)),
      bloque("Evaluaciones", tabla([["Id", (e) => e.id], ["Decisión", (e) => chipDecision(e.decision)],
        ["Puntaje", (e) => e.puntaje]], d.evaluaciones)),
      bloque("Documentos", tabla([["Tipo", (e) => e.tipo], ["Archivo", (e) => e.ruta.split(/[\\/]/).pop()],
        ["Creado", (e) => e.creado_en]], d.documentos)),
    );
  } catch (err) {
    mostrarError(err.message);
  }
}

async function mostrar(nombre) {
  for (const b of document.querySelectorAll(".pestanas button")) {
    b.setAttribute("aria-selected", String(b.dataset.vista === nombre));
  }
  mostrarError("");
  const esChat = nombre === "chat";
  chat.hidden = !esChat;
  vista.hidden = esChat;
  if (esChat) { document.getElementById("entrada").focus(); return; }
  vista.replaceChildren(el("p", { clase: "tenue", texto: "Cargando…" }));
  try {
    const contenido = await VISTAS[nombre]();
    vista.replaceChildren(...[contenido].flat());
  } catch (err) {
    vista.replaceChildren();
    mostrarError(err.message);
  }
}

// --- Chat ---------------------------------------------------------------------------------------

const historial = [];
const mensajes = document.getElementById("mensajes");
const dialogo = document.getElementById("confirmacion");

function burbuja(clase, texto = "") {
  const nodo = el("div", { clase: `mensaje ${clase}` }, el("div", { clase: "texto", texto }));
  mensajes.append(nodo);
  nodo.scrollIntoView({ block: "end" });
  return nodo;
}

function pedirConfirmacion(datos) {
  document.getElementById("confHerramienta").textContent = datos.herramienta;
  document.getElementById("confDescripcion").textContent = datos.descripcion;
  document.getElementById("confArgumentos").textContent = JSON.stringify(datos.argumentos, null, 2);
  dialogo.returnValue = "";
  dialogo.showModal();
  dialogo.addEventListener("close", async () => {
    const autorizar = dialogo.returnValue === "si";
    try {
      await api(`chat/confirmar/${encodeURIComponent(datos.id)}`, {
        method: "POST", body: JSON.stringify({ autorizar }),
      });
    } catch (err) {
      mostrarError(err.message);
    }
  }, { once: true });
}

async function enviar(evento) {
  evento.preventDefault();
  const entrada = document.getElementById("entrada");
  const boton = document.getElementById("enviar");
  const mensaje = entrada.value.trim();
  if (!mensaje) return;
  entrada.value = "";
  boton.disabled = true;
  mostrarError("");
  burbuja("usuario", mensaje);
  const respuesta = burbuja("asistente");
  const texto = respuesta.querySelector(".texto");
  const acciones = el("div", { clase: "acciones" });
  respuesta.append(acciones);
  let completo = "";
  let resumen = "";
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje, historial, solo_lectura: document.getElementById("soloLectura").checked }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Error ${r.status}`);
    const lector = r.body.getReader();
    const decodificador = new TextDecoder();
    let pendiente = "";
    for (;;) {
      const { value, done } = await lector.read();
      if (done) break;
      pendiente += decodificador.decode(value, { stream: true });
      let corte;
      while ((corte = pendiente.indexOf("\n\n")) >= 0) {
        const bloqueSse = pendiente.slice(0, corte);
        pendiente = pendiente.slice(corte + 2);
        const tipo = (bloqueSse.match(/^event: (.*)$/m) || [])[1];
        const datos = JSON.parse((bloqueSse.match(/^data: (.*)$/m) || [, "{}"])[1]);
        if (tipo === "texto") { completo += datos.texto; texto.textContent = completo; }
        else if (tipo === "accion") {
          acciones.append(el("div", {}, chipEstado(datos.estado), " ", datos.herramienta, " · ", datos.resumen));
        } else if (tipo === "confirmacion") pedirConfirmacion(datos);
        else if (tipo === "aviso") acciones.append(el("div", { clase: "tenue", texto: datos.texto }));
        else if (tipo === "error") mostrarError(datos.mensaje);
        else if (tipo === "fin") {
          resumen = datos.acciones || "";
          if (datos.observaciones.length) {
            respuesta.append(el("div", { clase: "revision" },
              el("strong", { texto: "Revisión automática" }),
              ...datos.observaciones.map((o) => el("div", { texto: `· ${o}` }))));
          }
        }
        respuesta.scrollIntoView({ block: "end" });
      }
    }
    historial.push({ role: "user", content: mensaje }, { role: "assistant", content: `${completo}\n${resumen}`.trim() });
    while (historial.length > 40) historial.shift();
  } catch (err) {
    mostrarError(err.message);
  } finally {
    boton.disabled = false;
  }
}

// --- Arranque ------------------------------------------------------------------------------------

async function arrancar() {
  for (const b of document.querySelectorAll(".pestanas button")) {
    b.addEventListener("click", () => mostrar(b.dataset.vista));
  }
  document.getElementById("formulario").addEventListener("submit", enviar);
  document.getElementById("entrada").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); document.getElementById("formulario").requestSubmit(); }
  });
  if (!TOKEN) {
    mostrarError("Falta el token. Abra el enlace completo que mostró «coopexecutive panel» en la terminal.");
    return;
  }
  try {
    const e = await api("estado");
    document.getElementById("organizacion").textContent = e.organizacion;
    document.getElementById("subtitulo").textContent = `${e.figura} · ${e.hoy_texto}`;
    document.getElementById("pie").textContent = `CoopExecutive ${e.version} · panel local, solo escucha en este equipo`;
    const sello = document.getElementById("sello");
    sello.hidden = false;
    sello.className = `sello ${e.bitacora.integra ? "ok" : "mal"}`;
    sello.textContent = e.bitacora.integra ? "Bitácora íntegra" : "Bitácora alterada";
  } catch (err) {
    mostrarError(err.message);
  }
  mostrar("resumen");
}

arrancar();
