"""Plantilla v2. Solo corre si el JSON trae "plantilla": "v2".

La v1 no importa este módulo. Reseñas textuales, fotos del perfil y cédula
se omiten salvo que el dato exista y permisos lo autorice.
"""

import json
import re
import shutil
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from generar import (
    DIAS_VIGENCIA,
    ICONO_CHAT,
    RAIZ,
    bloque_estado,
    bloque_horario,
    bloque_resenas,
    color_marca,
    e,
    favicon,
    fecha_larga,
    telefono_visible,
)

PLANTILLA = Path(__file__).resolve().parent / "plantilla-v2.html"
SITIO = "https://ferhuca.github.io/automia-sitios"
TEXTO_WA = "Quiero agendar una cita"

# schema.org: Dentist, Optician y VeterinaryCare son tipos de negocio.
# Physiotherapy y DietNutrition son valores de MedicalSpecialty, no tipos.
TIPOS = {
    "dental": "Dentist",
    "optica": "Optician",
    "veterinaria": "VeterinaryCare",
    "psicologia": "MedicalBusiness",
    "fisioterapia": "MedicalBusiness",
    "nutricion": "MedicalBusiness",
}
ESPECIALIDAD = {
    "fisioterapia": "https://schema.org/Physiotherapy",
    "nutricion": "https://schema.org/DietNutrition",
}
DIAS_EN = [
    ("lun", "Monday"), ("mar", "Tuesday"), ("mie", "Wednesday"),
    ("jue", "Thursday"), ("vie", "Friday"), ("sab", "Saturday"), ("dom", "Sunday"),
]
PERMISOS = ("resenas", "fotos", "cedula")
NINOS = re.compile(r"infantil|niñ|pediatric|beb[eé]|pediatr", re.I)
MARCADORES = ("por confirmar", "por descargar", "EJEMPLO", 'class="marcador"', "foto-vacia", "resena-ejemplo")

ICONO_TEL = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6'
    'A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7'
    'a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7'
    'a2 2 0 0 1 1.7 2z"/></svg>'
)

FUENTES = {
    "negra": (
        "/usr/share/fonts/truetype/macos/Inter-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    "media": (
        "/usr/share/fonts/truetype/macos/Inter-Medium.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "regular": (
        "/usr/share/fonts/truetype/macos/Inter-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
}


def normalizar(texto):
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9ñ\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def lista_es(items):
    items = [x for x in items if x]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} y {items[1]}"
    return ", ".join(items[:-1]) + " y " + items[-1]


def fallar(origen, mensaje):
    raise SystemExit(f"{origen}: {mensaje}")


def leer_permisos(d, origen):
    crudo = d.get("permisos") or {}
    if not isinstance(crudo, dict):
        fallar(origen, "permisos debe ser un objeto")
    for clave in crudo:
        if clave not in PERMISOS:
            fallar(origen, f"permiso desconocido '{clave}'. Opciones: {', '.join(PERMISOS)}")
        if not isinstance(crudo[clave], bool):
            fallar(origen, f"permisos.{clave} debe ser true o false")
    return {clave: bool(crudo.get(clave)) for clave in PERMISOS}


def normalizar_servicios(d, origen):
    crudo = d.get("servicios") or []
    if not isinstance(crudo, list):
        fallar(origen, "servicios debe ser una lista")
    salida = []
    for item in crudo:
        if isinstance(item, str):
            nombre, detalle = item.strip(), ""
        elif isinstance(item, dict):
            nombre = str(item.get("nombre") or "").strip()
            detalle = str(item.get("detalle") or "").strip()
        else:
            fallar(origen, "cada servicio es un texto o un objeto con nombre")
        if not nombre:
            continue
        texto = f"{nombre} ({detalle})" if detalle else nombre
        salida.append({"nombre": nombre, "detalle": detalle, "texto": texto})
    origen_srv = d.get("servicios_origen")
    if origen_srv not in (None, "categorias", "servicios"):
        fallar(origen, "servicios_origen debe ser 'categorias' o 'servicios'")
    if not origen_srv:
        origen_srv = "categorias" if any(s["detalle"] for s in salida) else "servicios"
    return salida, origen_srv


def distintivos_de(d, origen):
    crudo = d.get("distintivos") or []
    if not isinstance(crudo, list) or not all(isinstance(x, str) for x in crudo):
        fallar(origen, "distintivos debe ser una lista de textos")
    return [x.strip() for x in crudo if x.strip()]


def profesional_de(d, origen, permiso):
    if not permiso:
        return None
    prof = d.get("profesional") or {}
    if prof and not isinstance(prof, dict):
        fallar(origen, "profesional debe ser un objeto con nombre y cedula")
    nombre = str(prof.get("nombre") or "").strip()
    cedula = str(prof.get("cedula") or "").strip()
    if not nombre and not cedula:
        return None
    dato = {}
    if nombre:
        dato["nombre"] = nombre
    if cedula:
        dato["cedula"] = cedula
    return dato


def partes_direccion(d, origen):
    partes = d.get("direccion_partes") or {}
    if not isinstance(partes, dict):
        fallar(origen, "direccion_partes debe ser un objeto")
    cp = str(partes.get("cp") or "").strip()
    if cp and not re.fullmatch(r"\d{5}", cp):
        fallar(origen, "el código postal debe tener 5 dígitos, o quitarse")
    return {
        "calle": str(partes.get("calle") or "").strip(),
        "localidad": str(partes.get("localidad") or "").strip(),
        "region": str(partes.get("region") or "").strip(),
        "cp": cp,
    }


def geo_de(d, origen):
    if not d.get("geo"):
        return None
    geo = d["geo"]
    if not isinstance(geo, dict) or "latitud" not in geo or "longitud" not in geo:
        fallar(origen, "geo necesita latitud y longitud")
    try:
        lat = float(geo["latitud"])
        lng = float(geo["longitud"])
    except (TypeError, ValueError):
        fallar(origen, "geo.latitud y geo.longitud deben ser números")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        fallar(origen, "geo está fuera de rango")
    return {"latitud": lat, "longitud": lng}


def liga_whatsapp(numero):
    return f"https://wa.me/{numero}?text={quote(TEXTO_WA)}"


def liga_tel(numero):
    return f"tel:+52{numero}"


def enlace(clase, href, icono, texto, externo):
    extra = ' target="_blank" rel="noopener"' if externo else ""
    return f'<a class="boton {clase}" href="{e(href)}"{extra}>{icono} {e(texto)}</a>'


def boton_hero(d):
    if d.get("whatsapp"):
        return enlace("boton-principal", liga_whatsapp(d["whatsapp"]), ICONO_CHAT, "Agendar por WhatsApp", True)
    if d.get("telefono"):
        return enlace("boton-principal", liga_tel(d["telefono"]), ICONO_TEL, f"Llamar al {d['telefono_visible']}", False)
    return ""


def bloque_agendar(d):
    botones = []
    if d.get("whatsapp"):
        botones.append(enlace("boton-whatsapp", liga_whatsapp(d["whatsapp"]), ICONO_CHAT, "Agendar por WhatsApp", True))
    if d.get("telefono"):
        botones.append(enlace("boton-llamar", liga_tel(d["telefono"]), ICONO_TEL, "Llamar", False))
    if not botones:
        return ""
    return '<div class="agendar-bloque">\n          ' + "\n          ".join(botones) + "\n        </div>"


def barra_contacto(d):
    botones = []
    if d.get("whatsapp"):
        botones.append(enlace("boton-whatsapp", liga_whatsapp(d["whatsapp"]), ICONO_CHAT, "Agendar por WhatsApp", True))
    if d.get("telefono"):
        botones.append(enlace("boton-llamar", liga_tel(d["telefono"]), ICONO_TEL, "Llamar", False))
    if not botones:
        return ""
    clase = "barra-contacto barra-una" if len(botones) == 1 else "barra-contacto"
    return f'<nav class="{clase}" aria-label="Contacto rápido">\n  ' + "\n  ".join(botones) + "\n</nav>\n"


def texto_cita(d):
    nombre = d["nombre"]
    if d.get("whatsapp") and d.get("telefono"):
        return (f"Las citas se agendan directo con {nombre}, por WhatsApp o por teléfono "
                f"al {d['telefono_visible']}. Use el botón Agendar por WhatsApp.")
    if d.get("whatsapp"):
        return f"Las citas se agendan directo con {nombre}, por WhatsApp. Use el botón Agendar por WhatsApp."
    if d.get("telefono"):
        return f"Las citas se agendan directo con {nombre}, por teléfono al {d['telefono_visible']}. Use el botón Llamar."
    return f"Las citas se agendan directo con {nombre}."


def preguntas_de(d, origen, servicios, origen_srv, distintivos):
    propias = d.get("preguntas") or []
    if not isinstance(propias, list):
        fallar(origen, "preguntas debe ser una lista")
    hechas = set()
    html_items = []
    asistente = []

    def agregar(pregunta, respuesta, claves=None, al_asistente=False):
        clave_pregunta = normalizar(pregunta)
        if not pregunta or not respuesta or clave_pregunta in hechas:
            return
        hechas.add(clave_pregunta)
        html_items.append({"p": pregunta, "r": respuesta})
        if al_asistente:
            item = {"p": pregunta, "r": respuesta}
            if claves:
                item["claves"] = claves
            asistente.append(item)

    for item in propias:
        if not isinstance(item, dict) or not item.get("p") or not item.get("r"):
            fallar(origen, "cada pregunta necesita p y r")
        claves = item.get("claves") or []
        if not isinstance(claves, list):
            fallar(origen, "las claves de una pregunta deben ser una lista")
        agregar(str(item["p"]).strip(), str(item["r"]).strip(), [str(c) for c in claves], True)

    agregar("¿Cómo agendo una cita?", texto_cita(d))
    if servicios:
        textos = [s["texto"] for s in servicios]
        if origen_srv == "categorias":
            respuesta = (f"Según las categorías de su perfil de Google: {lista_es(textos)}. "
                         "Para detalles de cada servicio, pregunte directo.")
        else:
            respuesta = (f"Según su perfil de Google: {lista_es(textos)}. "
                         "Para detalles de cada servicio, pregunte directo.")
        agregar("¿Qué servicios ofrecen?", respuesta, [
            "que servicios", "cuales servicios", "servicios tienen", "servicios ofrecen",
            "lista de servicios", "que especialidades", "especialidades",
        ], True)
        de_ninos = [s["texto"] for s in servicios if NINOS.search(s["texto"])]
        if de_ninos:
            cierre = ("Para confirmar la atención a niños, pregunte directo por WhatsApp."
                      if d.get("whatsapp") else
                      "Para confirmar la atención a niños, pregunte directo.")
            agregar(
                "¿Atienden a niños?",
                f"Su perfil de Google incluye {lista_es(de_ninos)}. {cierre}",
                ["nino", "ninos", "nina", "infantil", "hijo", "hija", "bebe", "pediatric"],
                True,
            )
    if distintivos:
        agregar(
            "¿Qué más publica su perfil de Google?",
            f"Su perfil de Google indica: {lista_es(distintivos)}.",
            palabras_clave(distintivos),
            True,
        )
    agregar(
        "¿Cuánto cuesta?",
        f"Los precios los confirma {d['nombre']} directamente, porque dependen de cada caso.",
    )
    return html_items, asistente


def palabras_clave(frases):
    claves = []
    for frase in frases:
        for palabra in normalizar(frase).split():
            if len(palabra) >= 6 and palabra not in claves:
                claves.append(palabra)
    return claves[:12]


def html_preguntas(items):
    piezas = []
    for item in items:
        piezas.append(
            f"        <details>\n          <summary>{e(item['p'])}</summary>\n"
            f"          <p>{e(item['r'])}</p>\n        </details>"
        )
    return "\n".join(piezas)


def resolver_archivo(ruta_json, archivo, origen):
    if not isinstance(archivo, str) or not archivo.strip():
        fallar(origen, "la foto necesita archivo")
    relativo = Path(archivo)
    if relativo.is_absolute() or ".." in relativo.parts:
        fallar(origen, f"la ruta de la foto no es válida: {archivo}")
    bases = [ruta_json.parent / ruta_json.stem, ruta_json.parent]
    for base in bases:
        candidato = (base / relativo).resolve()
        try:
            candidato.relative_to(base.resolve())
        except ValueError:
            continue
        if candidato.is_file():
            return candidato
    return None


def fotos_de(d, ruta_json, origen, permiso):
    crudo = d.get("fotos") or []
    if not isinstance(crudo, list):
        fallar(origen, "fotos debe ser una lista")
    if not permiso:
        return []
    listas = []
    for item in crudo:
        if not isinstance(item, dict):
            fallar(origen, "cada foto es un objeto con archivo y alt")
        alt = str(item.get("alt") or "").strip()
        archivo = item.get("archivo")
        if not alt or not archivo:
            fallar(origen, "cada foto autorizada necesita archivo y alt")
        origen_archivo = resolver_archivo(ruta_json, archivo, origen)
        if origen_archivo is None:
            fallar(origen, f"no está el archivo de la foto: {archivo}")
        pie = str(item.get("pie") or "").strip()
        listas.append({"archivo": archivo, "alt": alt, "pie": pie, "origen": origen_archivo})
    return listas


def resenas_de(d, origen, permiso):
    crudo = d.get("resenas_texto") or []
    if not isinstance(crudo, list):
        fallar(origen, "resenas_texto debe ser una lista")
    if not permiso:
        return []
    salida = []
    for item in crudo:
        if not isinstance(item, dict):
            fallar(origen, "cada reseña es un objeto con texto y autor")
        texto = str(item.get("texto") or "").strip()
        autor = str(item.get("autor") or "").strip()
        if not texto or not autor:
            fallar(origen, "cada reseña autorizada necesita texto y autor")
        estrellas = item.get("estrellas")
        if estrellas is not None and (not isinstance(estrellas, int) or not 1 <= estrellas <= 5):
            fallar(origen, "estrellas debe ser un entero del 1 al 5, o quitarse")
        salida.append({"texto": texto, "autor": autor, "estrellas": estrellas})
    return salida


def seccion_servicios(d, servicios, origen_srv, distintivos, profesional, fotos):
    bloques = []
    if servicios:
        items = []
        for servicio in servicios:
            extra = f"<small>{e(servicio['detalle'])}</small>" if servicio["detalle"] else ""
            items.append(f"        <li>{e(servicio['nombre'])}{extra}</li>")
        etiqueta = ("Categorías del perfil de Google." if origen_srv == "categorias"
                    else "Servicios del perfil de Google.")
        intro = (f"Lo que {d['nombre']} publica en su perfil de Google. "
                 "Para detalles de cada servicio, pregunte directo.")
        bloques.append(
            f"      <h2>Servicios y especialidades</h2>\n"
            f"      <p class=\"seccion-entrada\">{e(intro)}</p>\n"
            f"      <ul class=\"servicios servicios-v2\">\n" + "\n".join(items) + "\n      </ul>\n"
            f"      <p class=\"fuente\">{etiqueta} "
            f"<a href=\"{e(d['maps_url'])}\" target=\"_blank\" rel=\"noopener\">Ver en Google</a></p>"
        )
    if fotos:
        figuras = []
        for foto in fotos:
            pie = f"<figcaption>{e(foto['pie'])}</figcaption>" if foto["pie"] else ""
            figuras.append(
                f"        <figure><img src=\"{e(foto['archivo'])}\" alt=\"{e(foto['alt'])}\" loading=\"lazy\">{pie}</figure>"
            )
        bloques.append('      <div class="fotos">\n' + "\n".join(figuras) + "\n      </div>")
    tarjetas = []
    if profesional:
        lineas = []
        if profesional.get("nombre"):
            lineas.append(f"          <p>{e(profesional['nombre'])}</p>")
        if profesional.get("cedula"):
            lineas.append(f"          <p>Cédula profesional: {e(profesional['cedula'])}</p>")
        tarjetas.append(
            "        <article class=\"tarjeta\">\n          <h3>Quién le atiende</h3>\n"
            + "\n".join(lineas) + "\n        </article>"
        )
    if distintivos:
        lis = "\n".join(f"            <li>{e(item)}</li>" for item in distintivos)
        tarjetas.append(
            "        <article class=\"tarjeta\">\n          <h3>En su perfil de Google</h3>\n"
            f"          <ul class=\"distintivos\">\n{lis}\n          </ul>\n        </article>"
        )
    if tarjetas:
        if not servicios:
            bloques.insert(0, "      <h2>Del perfil de Google</h2>")
        bloques.append('      <div class="confianza">\n' + "\n".join(tarjetas) + "\n      </div>")
    elif not servicios and fotos:
        bloques.insert(0, "      <h2>Del perfil de Google</h2>")
    if not bloques:
        return ""
    return ('  <section class="seccion" id="servicios">\n    <div class="contenedor">\n'
            + "\n".join(bloques) + "\n    </div>\n  </section>\n")


def seccion_resenas(d, resenas):
    if not resenas:
        return ""
    tarjetas = []
    for resena in resenas:
        estrellas = ""
        if resena["estrellas"]:
            n = resena["estrellas"]
            estrellas = f'          <span class="resena-estrellas" aria-label="{n} de 5">{"★" * n}</span>\n'
        tarjetas.append(
            "        <article class=\"tarjeta resena\">\n"
            f"{estrellas}"
            f"          <blockquote>{e(resena['texto'])}</blockquote>\n"
            f"          <p class=\"resena-autor\">{e(resena['autor'])}</p>\n"
            f"          <a href=\"{e(d['maps_url'])}\" target=\"_blank\" rel=\"noopener\">Ver en Google</a>\n"
            "        </article>"
        )
    cabecera = ""
    if d.get("calificacion") and d.get("resenas"):
        cabecera = (
            f'      <div class="resenas-cabecera"><strong>{e(d["calificacion"])}</strong>'
            f'<span>{e(d["resenas"])} reseñas en Google</span></div>\n'
        )
    return (
        '  <section class="seccion seccion-tinte" id="resenas">\n    <div class="contenedor">\n'
        "      <h2>Lo que dicen en Google</h2>\n"
        f"{cabecera}"
        '      <div class="resenas">\n' + "\n".join(tarjetas) + "\n      </div>\n"
        f'      <p class="resenas-cierre"><a class="boton boton-marca" href="{e(d["maps_url"])}" '
        'target="_blank" rel="noopener">Ver todas las reseñas en Google</a></p>\n'
        "    </div>\n  </section>\n"
    )


def horarios_jsonld(d):
    horario = d.get("horario") or {}
    grupos = {}
    orden = []
    for clave, nombre in DIAS_EN:
        vistos = set()
        for abre, cierra in horario.get(clave) or []:
            firma = (abre, cierra)
            if firma in vistos:
                continue
            vistos.add(firma)
            if firma not in grupos:
                grupos[firma] = []
                orden.append(firma)
            grupos[firma].append(nombre)
    specs = []
    for abre, cierra in orden:
        specs.append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": grupos[(abre, cierra)],
            "opens": abre,
            "closes": cierra,
        })
    return specs


def construir_jsonld(d, url, imagen):
    partes = partes_direccion(d, d["slug"])
    direccion = {"@type": "PostalAddress", "streetAddress": partes["calle"] or d["direccion"], "addressCountry": "MX"}
    if partes["localidad"]:
        direccion["addressLocality"] = partes["localidad"]
    if partes["region"]:
        direccion["addressRegion"] = partes["region"]
    if partes["cp"]:
        direccion["postalCode"] = partes["cp"]
    datos = {
        "@context": "https://schema.org",
        "@type": TIPOS[d["giro"]],
        "@id": url + "#negocio",
        "name": d["nombre"],
        "description": d["descripcion"],
        "url": url,
        "image": imagen,
        "address": direccion,
        "hasMap": d["maps_url"],
        "sameAs": [d["maps_url"]],
    }
    if d.get("telefono"):
        datos["telephone"] = "+52 " + d["telefono_visible"]
    geo = geo_de(d, d["slug"])
    if geo:
        datos["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": geo["latitud"],
            "longitude": geo["longitud"],
        }
    specs = horarios_jsonld(d)
    if specs:
        datos["openingHoursSpecification"] = specs
    if d["giro"] in ESPECIALIDAD:
        datos["medicalSpecialty"] = ESPECIALIDAD[d["giro"]]
    return datos


def json_script(datos):
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    return texto.replace("<", "\\u003c")


def prefijo_assets(destino):
    try:
        relativo = destino.resolve().relative_to(RAIZ.resolve())
    except ValueError:
        return "../assets"
    return "../" * len(relativo.parts) + "assets"


def fuente(estilo, tamano):
    from PIL import ImageFont
    for ruta in FUENTES[estilo]:
        if Path(ruta).is_file():
            return ImageFont.truetype(ruta, tamano)
    raise SystemExit("No hay una fuente para la imagen de redes.")


def hex_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mezclar(color, hacia, factor):
    return tuple(int(a + (b - a) * factor) for a, b in zip(color, hacia))


def recortar_texto(draw, texto, font, ancho):
    if draw.textlength(texto, font=font) <= ancho:
        return texto
    corte = texto
    while corte and draw.textlength(corte + "...", font=font) > ancho:
        corte = corte[:-1].rstrip()
    if " " in corte:
        corte = corte.rsplit(" ", 1)[0].rstrip()
    return (corte + "...") if corte else "..."


def partir_lineas(draw, texto, font, ancho):
    palabras = texto.split()
    if not palabras:
        return []
    lineas = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        prueba = actual + " " + palabra
        if draw.textlength(prueba, font=font) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def escribir_og(d, destino, imagen_url):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise SystemExit("Para la plantilla v2 hace falta Pillow: python3 -m pip install pillow")
    ancho, alto = 1200, 630
    marca = hex_rgb(color_marca(d))
    imagen = Image.new("RGB", (ancho, alto), marca)
    draw = ImageDraw.Draw(imagen)
    claro = mezclar(marca, (255, 255, 255), 0.18)
    draw.ellipse((820, -180, 1380, 380), fill=claro)
    draw.rounded_rectangle((72, 56, 164, 148), radius=22, fill=(255, 255, 255))
    letra = d["nombre"].strip()[:1].upper()
    fuente_letra = fuente("negra", 64)
    caja = draw.textbbox((0, 0), letra, font=fuente_letra)
    draw.text((118 - (caja[2] - caja[0]) / 2, 102 - (caja[3] - caja[1]) / 2), letra, font=fuente_letra, fill=marca)

    max_texto = 860
    tamano = 78
    fuente_nombre = fuente("negra", tamano)
    lineas = partir_lineas(draw, d["nombre"], fuente_nombre, max_texto)
    while tamano > 46 and (len(lineas) > 3 or any(draw.textlength(linea, font=fuente_nombre) > max_texto for linea in lineas)):
        tamano -= 4
        fuente_nombre = fuente("negra", tamano)
        lineas = partir_lineas(draw, d["nombre"], fuente_nombre, max_texto)
    y = 188
    for linea in lineas[:3]:
        draw.text((72, y), linea, font=fuente_nombre, fill=(255, 255, 255))
        y += tamano + 6

    subtitulo = f"{d['giro_texto']} en {d['zona']}"
    fuente_sub = fuente("media", 32)
    draw.text((72, y + 16), subtitulo, font=fuente_sub, fill=(255, 255, 255))
    draw.line((72, 500, 1128, 500), fill=mezclar(marca, (255, 255, 255), 0.35), width=2)

    fuente_pill = fuente("media", 26)
    etiqueta = "Agende por WhatsApp" if d.get("whatsapp") else ("Llame para agendar" if d.get("telefono") else "")
    pill_ancho = (draw.textlength(etiqueta, font=fuente_pill) + 56) if etiqueta else 0
    ancho_direccion = 1056 - (pill_ancho + 28 if pill_ancho else 0)
    fuente_dir = fuente("regular", 26)
    direccion = recortar_texto(draw, d["direccion"], fuente_dir, ancho_direccion)
    draw.text((72, 532), direccion, font=fuente_dir, fill=(255, 255, 255))

    if etiqueta:
        x2, y1, y2 = 1128, 522, 578
        x1 = x2 - pill_ancho
        draw.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=(255, 255, 255))
        draw.text((x1 + 28, 536), etiqueta, font=fuente_pill, fill=marca)

    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino, "PNG")
    return imagen_url


def copiar_fotos(fotos, destino):
    for foto in fotos:
        salida = destino / foto["archivo"]
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(foto["origen"], salida)


def describir(d):
    texto = f"{d['giro_texto']} en {d['zona']}. {d['descripcion']}"
    if d.get("whatsapp"):
        return texto + " Agende por WhatsApp."
    if d.get("telefono"):
        return texto + " Llame para agendar."
    return texto


def revisar_marcadores(pagina, origen):
    for marca in MARCADORES:
        if marca in pagina:
            fallar(origen, f"la página trae un marcador que no debe publicarse: {marca}")
    if "\u2014" in pagina or "\u2013" in pagina:
        fallar(origen, "la página trae un guion largo")


def generar_v2(d, ruta, destino_raiz=None):
    origen = ruta.name
    if d.get("telefono"):
        d["telefono_visible"] = telefono_visible(d["telefono"])
    permisos = leer_permisos(d, origen)
    servicios, origen_srv = normalizar_servicios(d, origen)
    distintivos = distintivos_de(d, origen)
    profesional = profesional_de(d, origen, permisos["cedula"])
    fotos = fotos_de(d, ruta, origen, permisos["fotos"])
    resenas = resenas_de(d, origen, permisos["resenas"])
    partes_direccion(d, origen)
    geo_de(d, origen)

    creada = date.fromisoformat(d["creada"])
    aviso = "Vista previa preparada por Automia. No está publicada."
    if d.get("ejemplo"):
        aviso += " Negocio de ejemplo: los datos son ficticios."

    url = f"{SITIO}/{d['slug']}/"
    imagen = f"{SITIO}/{d['slug']}/og.png"
    jsonld = construir_jsonld(d, url, imagen)
    html_items, asistente = preguntas_de(d, origen, servicios, origen_srv, distintivos)

    publicos = {k: d[k] for k in (
        "nombre", "direccion", "referencia", "maps_url", "telefono", "telefono_visible",
        "whatsapp", "instagram") if d.get(k)}
    if servicios:
        publicos["servicios"] = [s["texto"] for s in servicios]
    if d.get("horario"):
        publicos["horario"] = d["horario"]
    if asistente:
        publicos["preguntas"] = asistente
    if profesional:
        publicos["profesional"] = profesional
    if distintivos:
        publicos["distintivos"] = distintivos

    consulta = d.get("maps_consulta") or f"{d['nombre']}, {d['direccion']}"
    referencia = f'<span class="direccion-ref">{e(d["referencia"])}</span>' if d.get("referencia") else ""
    pie_tel = f'<p>Tel. {e(d["telefono_visible"])}</p>' if d.get("telefono") else ""
    if d.get("instagram"):
        pie_tel += (f'\n    <p>Instagram: <a href="https://www.instagram.com/{e(d["instagram"])}/" '
                    f'target="_blank" rel="noopener">@{e(d["instagram"])}</a></p>')

    titulo = f"{d['nombre']} | {d['giro_texto']} en {d['zona']}"
    descripcion = describir(d)
    base = Path(destino_raiz) if destino_raiz else RAIZ
    destino = base / d["slug"]
    valores = {
        "assets": prefijo_assets(destino),
        "giro": e(d["giro"]),
        "color_marca": color_marca(d),
        "attr_paleta": f' data-paleta="{e(d["paleta"])}"' if d.get("paleta") else "",
        "favicon": favicon(d),
        "giro_texto": e(d["giro_texto"]),
        "nombre": e(d["nombre"]),
        "zona": e(d["zona"]),
        "descripcion": e(d["descripcion"]),
        "descripcion_meta": e(descripcion),
        "aviso": e(aviso),
        "boton_contacto": boton_hero(d),
        "bloque_estado": bloque_estado(d),
        "bloque_resenas": bloque_resenas(d),
        "seccion_servicios": seccion_servicios(d, servicios, origen_srv, distintivos, profesional, fotos),
        "seccion_resenas": seccion_resenas(d, resenas),
        "bloque_horario": bloque_horario(d),
        "agendar_bloque": bloque_agendar(d),
        "direccion": e(d["direccion"]),
        "referencia": referencia,
        "mapa_src": e("https://www.google.com/maps?q=" + quote(consulta) + "&output=embed"),
        "maps_url": e(d["maps_url"]),
        "preguntas": html_preguntas(html_items),
        "pie_telefono": pie_tel,
        "caduca": fecha_larga(creada + timedelta(days=DIAS_VIGENCIA)),
        "datos_json": json.dumps(publicos, ensure_ascii=False).replace("</", "<\\/"),
        "og_title": e(titulo),
        "og_description": e(descripcion),
        "og_url": e(url),
        "og_image": e(imagen),
        "og_image_alt": e(f"{d['nombre']}, {d['giro_texto']} en {d['zona']}"),
        "json_ld": json_script(jsonld),
        "barra_contacto": barra_contacto(d),
    }
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    pendientes = set(re.findall(r"\{\{(\w+)\}\}", plantilla)) - set(valores)
    if pendientes:
        fallar(origen, "la plantilla v2 pide valores que no existen: " + ", ".join(sorted(pendientes)))
    pagina = re.sub(r"\{\{(\w+)\}\}", lambda m: valores[m.group(1)], plantilla)
    revisar_marcadores(pagina, origen)

    destino.mkdir(parents=True, exist_ok=True)
    escribir_og(d, destino / "og.png", imagen)
    copiar_fotos(fotos, destino)
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    return d["slug"]
