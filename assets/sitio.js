// Sitio de negocio local: estado de "abierto ahora" y asistente de preguntas.
// Todo corre en el navegador. No guarda ni envía nada.
(function () {
  "use strict";

  var nodoDatos = document.getElementById("datos");
  if (!nodoDatos) return;
  var D = JSON.parse(nodoDatos.textContent);

  var DIAS = ["dom", "lun", "mar", "mie", "jue", "vie", "sab"];
  var NOMBRES = {
    dom: "domingo", lun: "lunes", mar: "martes", mie: "miércoles",
    jue: "jueves", vie: "viernes", sab: "sábado"
  };

  // ---------- utilidades ----------

  function normalizar(texto) {
    return String(texto)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9ñ\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function aMinutos(hhmm) {
    var p = hhmm.split(":");
    return Number(p[0]) * 60 + Number(p[1]);
  }

  function hora(hhmm) {
    var p = hhmm.split(":");
    var h = Number(p[0]);
    var sufijo = h >= 12 ? "pm" : "am";
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + ":" + p[1] + " " + sufijo;
  }

  function tramos(dia) {
    return (D.horario && D.horario[dia]) || [];
  }

  function textoDia(dia) {
    var t = tramos(dia);
    if (!t.length) return "cerrado";
    return t.map(function (x) { return hora(x[0]) + " a " + hora(x[1]); }).join(" y ");
  }

  function hayHorario() {
    return DIAS.some(function (d) { return tramos(d).length > 0; });
  }

  // Hora del centro de México, sin depender del reloj del visitante.
  function ahoraMX() {
    var partes = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Mexico_City",
      weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(new Date());
    var v = {};
    partes.forEach(function (p) { v[p.type] = p.value; });
    var indice = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(v.weekday);
    return { dia: indice, minutos: Number(v.hour) * 60 + Number(v.minute) };
  }

  function estadoActual() {
    if (!hayHorario()) return null;
    var ahora = ahoraMX();
    var hoy = tramos(DIAS[ahora.dia]);
    var i;
    for (i = 0; i < hoy.length; i++) {
      if (ahora.minutos >= aMinutos(hoy[i][0]) && ahora.minutos < aMinutos(hoy[i][1])) {
        return { abierto: true, titulo: "Abierto ahora", detalle: "Cierra a las " + hora(hoy[i][1]) };
      }
    }
    for (i = 0; i < hoy.length; i++) {
      if (ahora.minutos < aMinutos(hoy[i][0])) {
        return { abierto: false, titulo: "Cerrado ahora", detalle: "Abre hoy a las " + hora(hoy[i][0]) };
      }
    }
    for (i = 1; i <= 7; i++) {
      var dia = DIAS[(ahora.dia + i) % 7];
      var t = tramos(dia);
      if (t.length) {
        var cuando = i === 1 ? "mañana" : "el " + NOMBRES[dia];
        return { abierto: false, titulo: "Cerrado ahora", detalle: "Abre " + cuando + " a las " + hora(t[0][0]) };
      }
    }
    return null;
  }

  function ligaWhatsApp(texto) {
    return "https://wa.me/" + D.whatsapp + "?text=" + encodeURIComponent(texto);
  }

  function contacto(textoMensaje) {
    if (D.whatsapp) {
      return { texto: "Escribir por WhatsApp", href: ligaWhatsApp(textoMensaje || "Hola, vi su página y tengo una pregunta.") };
    }
    if (D.telefono) return { texto: "Llamar al " + D.telefono_visible, href: "tel:+52" + D.telefono };
    return null;
  }

  // ---------- estado en la portada y en la tabla ----------

  function pintarEstado() {
    var caja = document.querySelector("[data-estado-caja]");
    var e = estadoActual();
    if (caja && e) {
      caja.setAttribute("data-estado", e.abierto ? "abierto" : "cerrado");
      caja.querySelector("[data-estado-titulo]").textContent = e.titulo;
      caja.querySelector("[data-estado-detalle]").textContent = e.detalle;
    }
    var hoy = DIAS[ahoraMX().dia];
    document.querySelectorAll(".horario tr[data-dia]").forEach(function (fila) {
      var esHoy = fila.getAttribute("data-dia") === hoy;
      fila.classList.toggle("hoy", esHoy);
      var etiqueta = fila.querySelector("[data-hoy]");
      if (etiqueta) etiqueta.hidden = !esHoy;
    });
  }

  pintarEstado();
  setInterval(pintarEstado, 60000);

  // ---------- asistente ----------

  var panel = document.getElementById("asistente");
  var abrir = document.getElementById("asistente-abrir");
  if (!panel || !abrir) return;

  var mensajes = panel.querySelector("[data-mensajes]");
  var forma = panel.querySelector("form");
  var campo = panel.querySelector("input");
  var iniciado = false;

  function agregar(clase, partes) {
    var burbuja = document.createElement("div");
    burbuja.className = "mensaje " + clase;
    (Array.isArray(partes) ? partes : [partes]).forEach(function (parte) {
      if (typeof parte === "string") {
        burbuja.appendChild(document.createTextNode(parte));
      } else if (parte && parte.href) {
        var a = document.createElement("a");
        a.href = parte.href;
        a.textContent = parte.texto;
        if (/^https?:/.test(parte.href)) { a.target = "_blank"; a.rel = "noopener"; }
        burbuja.appendChild(a);
      }
    });
    mensajes.appendChild(burbuja);
    mensajes.scrollTop = mensajes.scrollHeight;
  }

  function tiene(q, palabras) {
    return palabras.some(function (p) { return q.indexOf(p) !== -1; });
  }

  // Solo cuentan las palabras que distinguen a un servicio de los demás:
  // "dental" aparece en varios y no dice cuál; "ortodoncia" sí.
  var GENERICAS = ["dental", "dentales", "consulta", "consultas", "general", "terapia", "terapias",
    "tratamiento", "tratamientos", "servicio", "servicios", "atencion", "clinica", "estudio", "estudios",
    "sesion", "sesiones", "valoracion", "adultos", "ninos", "pareja", "familiar"];

  function servicioMencionado(q) {
    var cuenta = {};
    var lista = (D.servicios || []).map(function (s) {
      var palabras = normalizar(s).split(" ").filter(function (p) {
        return p.length >= 5 && GENERICAS.indexOf(p) === -1;
      });
      palabras.forEach(function (p) { cuenta[p] = (cuenta[p] || 0) + 1; });
      return { nombre: s, palabras: palabras };
    });
    for (var i = 0; i < lista.length; i++) {
      for (var j = 0; j < lista[i].palabras.length; j++) {
        var p = lista[i].palabras[j];
        if (cuenta[p] === 1 && q.indexOf(p.slice(0, -1)) !== -1) return lista[i].nombre;
      }
    }
    return null;
  }

  function diaMencionado(q) {
    var ahora = ahoraMX();
    if (/\bhoy\b/.test(q)) return DIAS[ahora.dia];
    if (/\bmanana\b/.test(q) && !/\b(en|por|de) la manana\b/.test(q)) return DIAS[(ahora.dia + 1) % 7];
    var pares = [["domingo", "dom"], ["lunes", "lun"], ["martes", "mar"], ["miercoles", "mie"],
      ["jueves", "jue"], ["viernes", "vie"], ["sabado", "sab"]];
    for (var i = 0; i < pares.length; i++) {
      if (q.indexOf(pares[i][0]) !== -1) return pares[i][1];
    }
    return null;
  }

  function responder(pregunta) {
    var q = normalizar(pregunta);
    var c;

    // 1. Respuestas propias del negocio, si las hay.
    var propias = D.preguntas || [];
    for (var i = 0; i < propias.length; i++) {
      var claves = (propias[i].claves || []).map(normalizar);
      if (claves.length && tiene(q, claves)) return [propias[i].r];
    }

    var servicio = servicioMencionado(q);

    // 2. Precios: nunca se inventan.
    var esDuracion = tiene(q, ["tiempo", "dura", "tarda"]);
    if (!esDuracion && tiene(q, ["precio", "cuesta", "costo", "cuanto", "cobra", "tarifa", "barato", "promocion", "descuento"])) {
      c = contacto("Hola, quiero preguntar por el precio de " + (servicio ? servicio.toLowerCase() : "sus servicios") + ".");
      var inicio = servicio ? "Sí ofrecen " + servicio.toLowerCase() + ". " : "";
      return [inicio + "Los precios los confirma " + D.nombre + " directamente, porque dependen de cada caso. ", c || ""];
    }

    // 3. Citas.
    if (tiene(q, ["cita", "agend", "reserv", "consulta", "apart", "turno", "disponib"])) {
      c = contacto("Hola, quiero agendar una cita.");
      return ["Las citas se agendan directo con " + D.nombre + ". ", c || ""];
    }

    // 4. Horario.
    if (tiene(q, ["horario", " hora", "abren", "abre", "abiert", "cierr", "cerrad", "atienden", "hoy", "domingo", "sabado", "lunes", "martes", "miercoles", "jueves", "viernes"])) {
      if (!hayHorario()) {
        c = contacto("Hola, ¿cuál es su horario?");
        return ["El horario no está publicado. ", c || ""];
      }
      var dia = diaMencionado(q);
      if (dia) {
        var t = textoDia(dia);
        return [t === "cerrado"
          ? "El " + NOMBRES[dia] + " está cerrado."
          : "El " + NOMBRES[dia] + " atienden de " + t + "."];
      }
      var e = estadoActual();
      var resumen = DIAS.slice(1).concat("dom").map(function (d) {
        return NOMBRES[d].charAt(0).toUpperCase() + NOMBRES[d].slice(1) + ": " + textoDia(d);
      }).join("\n");
      return [(e ? e.titulo + ". " + e.detalle + ".\n\n" : "") + resumen];
    }

    // 5. Ubicación.
    if (tiene(q, ["donde", "direccion", "ubica", "llegar", "llego", "mapa", "calle", "colonia", "queda", "estan"])) {
      var partes = ["Están en " + D.direccion + ". "];
      if (D.referencia) partes[0] += D.referencia + ". ";
      if (D.maps_url) partes.push({ texto: "Abrir en Google Maps", href: D.maps_url });
      return partes;
    }

    // 6. Servicios.
    if (servicio && !esDuracion) {
      c = contacto("Hola, quiero preguntar por " + servicio.toLowerCase() + ".");
      return ["Sí, " + D.nombre + " ofrece " + servicio.toLowerCase() + ". Para detalles, pregunte directo. ", c || ""];
    }
    if (!esDuracion && tiene(q, ["servicio", "hacen", "ofrece", "tratamiento", "manejan", "realizan"])) {
      if (!D.servicios || !D.servicios.length) {
        c = contacto("Hola, quiero saber qué servicios ofrecen.");
        return ["La lista de servicios no está publicada. Lo mejor es preguntarlo directo a " + D.nombre + ". ", c || ""];
      }
      return ["Estos son los servicios publicados:\n" + D.servicios.map(function (s) { return "• " + s; }).join("\n")];
    }

    // 7. Contacto.
    if (tiene(q, ["telefono", "numero", "whatsapp", "llamar", "contact", "marcar", "instagram", "redes"])) {
      c = contacto();
      return [D.telefono_visible ? "El teléfono es " + D.telefono_visible + ". " : "", c || "",
        D.instagram ? ". También están en Instagram como " : "",
        D.instagram ? { texto: "@" + D.instagram, href: "https://www.instagram.com/" + D.instagram + "/" } : ""];
    }

    // 8. Cortesía.
    if (tiene(q, ["gracias", "perfecto", "listo", "ok"])) return ["Con gusto."];
    if (tiene(q, ["hola", "buenos dias", "buenas tardes", "buenas noches", "buen dia"])) {
      return ["Hola. Puedo decirle el horario, la ubicación y los servicios de " + D.nombre + "."];
    }

    // 9. No hay dato: se pasa la pregunta al negocio.
    c = contacto("Hola, vi su página y tengo una pregunta: " + pregunta);
    if (c && D.whatsapp) c.texto = "Enviar esta pregunta por WhatsApp";
    return ["No tengo ese dato. Lo mejor es preguntarlo directo a " + D.nombre + ". ", c || ""];
  }

  function preguntar(texto) {
    texto = texto.trim();
    if (!texto) return;
    agregar("mensaje-persona", texto);
    agregar("mensaje-asistente", responder(texto));
  }

  function abrirPanel() {
    panel.hidden = false;
    abrir.hidden = true;
    abrir.setAttribute("aria-expanded", "true");
    if (!iniciado) {
      iniciado = true;
      agregar("mensaje-asistente", "Hola. Puedo responder sobre el horario, la ubicación y los servicios de " + D.nombre + ". Elija una pregunta o escriba la suya.");
      agregar("mensaje-nota", "Respondo solo con la información publicada del negocio. Esta conversación no se guarda.");
    }
    campo.focus();
  }

  function cerrarPanel() {
    panel.hidden = true;
    abrir.hidden = false;
    abrir.setAttribute("aria-expanded", "false");
    abrir.focus();
  }

  // El botón flotante se quita de en medio cuando quedaría encima del horario
  // o de la tarjeta de estado (pasa sobre todo en celular). Al seguir bajando,
  // vuelve a aparecer. "Hacer otra pregunta" siempre abre el asistente.
  var protegidos = document.querySelectorAll(".horario, [data-estado-caja]");
  var pendiente = false;

  var HOLGURA = 8; // px de aire alrededor del botón

  function seTocan(a, b) {
    return a.left - HOLGURA < b.right && a.right + HOLGURA > b.left &&
      a.top - HOLGURA < b.bottom && a.bottom + HOLGURA > b.top;
  }

  function acomodarBoton() {
    pendiente = false;
    if (abrir.hidden) return;
    var caja = abrir.getBoundingClientRect();
    var tapa = Array.prototype.some.call(protegidos, function (el) {
      return seTocan(caja, el.getBoundingClientRect());
    });
    abrir.classList.toggle("asistente-abrir-oculto", tapa);
  }

  function programarAcomodo() {
    if (pendiente) return;
    pendiente = true;
    window.requestAnimationFrame(acomodarBoton);
  }

  window.addEventListener("scroll", programarAcomodo, { passive: true });
  window.addEventListener("resize", programarAcomodo);
  window.addEventListener("load", programarAcomodo);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(programarAcomodo);
  acomodarBoton();

  abrir.addEventListener("click", abrirPanel);
  panel.querySelector("[data-cerrar]").addEventListener("click", cerrarPanel);
  panel.addEventListener("keydown", function (ev) { if (ev.key === "Escape") cerrarPanel(); });

  document.querySelectorAll("[data-abrir-asistente]").forEach(function (b) {
    b.addEventListener("click", abrirPanel);
  });

  panel.querySelectorAll(".sugerencia").forEach(function (b) {
    b.addEventListener("click", function () { preguntar(b.textContent); campo.focus(); });
  });

  forma.addEventListener("submit", function (ev) {
    ev.preventDefault();
    preguntar(campo.value);
    campo.value = "";
  });
})();
