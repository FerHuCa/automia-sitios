#!/usr/bin/env python3
"""Genera la vista previa de un negocio a partir de su archivo en datos/.

Uso:
    python3 tools/generar.py                 genera todas las de datos/
    python3 tools/generar.py ejemplo-dental  genera solo esa
    python3 tools/generar.py --vencidas      lista las que ya pasaron de 14 días

Solo usa la biblioteca estándar. Cada archivo datos/<slug>.json produce
<slug>/index.html. Si a un negocio le falta un dato, se omite ese bloque:
nunca se inventa.
"""

import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
PLANTILLA = Path(__file__).resolve().parent / "plantilla.html"

DIAS_VIGENCIA = 14

GIROS = {
    "dental": "#0b4f4a",
    "psicologia": "#3b2f63",
    "fisioterapia": "#12477a",
    "nutricion": "#2f5d1e",
    "veterinaria": "#6b3f12",
    "optica": "#1e2a78",
}

DIAS = [
    ("lun", "Lunes"), ("mar", "Martes"), ("mie", "Miércoles"), ("jue", "Jueves"),
    ("vie", "Viernes"), ("sab", "Sábado"), ("dom", "Domingo"),
]

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]

OBLIGATORIOS = ["slug", "creada", "giro", "giro_texto", "nombre", "zona",
                "descripcion", "direccion", "maps_url"]

ICONO_CHAT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>'
)
ICONO_TEL = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>'
)


def e(texto):
    return html.escape(str(texto), quote=True)


def hora(hhmm):
    h, m = hhmm.split(":")
    h = int(h)
    sufijo = "pm" if h >= 12 else "am"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}:{m} {sufijo}"


def fecha_larga(d):
    return f"{d.day} de {MESES[d.month - 1]}"


def telefono_visible(digitos):
    d = re.sub(r"\D", "", digitos)
    if len(d) != 10:
        return digitos
    # CDMX, Guadalajara y Monterrey usan lada de 2 dígitos; el resto, de 3.
    if d[:2] in ("55", "56", "33", "81"):
        return f"{d[:2]} {d[2:6]} {d[6:]}"
    return f"{d[:3]} {d[3:6]} {d[6:]}"


def validar(d, origen):
    faltan = [c for c in OBLIGATORIOS if not d.get(c)]
    if faltan:
        raise SystemExit(f"{origen}: faltan campos obligatorios: {', '.join(faltan)}")
    if d["giro"] not in GIROS:
        raise SystemExit(f"{origen}: giro '{d['giro']}' no existe. Opciones: {', '.join(GIROS)}")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", d["slug"]):
        raise SystemExit(f"{origen}: el slug solo lleva minúsculas, números y guiones")
    if d["slug"] != Path(origen).stem:
        raise SystemExit(f"{origen}: el slug debe ser igual al nombre del archivo")
    for campo in ("telefono", "whatsapp"):
        if d.get(campo) and not re.fullmatch(r"\d+", d[campo]):
            raise SystemExit(f"{origen}: {campo} lleva solo dígitos")
    if d.get("telefono") and len(d["telefono"]) != 10:
        raise SystemExit(f"{origen}: telefono lleva 10 dígitos, sin lada de país")
    for dia, tramos in (d.get("horario") or {}).items():
        if dia not in dict(DIAS):
            raise SystemExit(f"{origen}: día desconocido en horario: {dia}")
        for tramo in tramos:
            if len(tramo) != 2 or not all(re.fullmatch(r"\d\d:\d\d", t) for t in tramo):
                raise SystemExit(f"{origen}: tramo de horario mal escrito en {dia}: {tramo}")
    date.fromisoformat(d["creada"])


def favicon(d):
    letra = e(d["nombre"].strip()[0].upper())
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
           f"<rect width='64' height='64' rx='14' fill='{GIROS[d['giro']]}'/>"
           f"<text x='32' y='45' font-family='Arial,sans-serif' font-size='38' font-weight='700' "
           f"text-anchor='middle' fill='white'>{letra}</text></svg>")
    return "data:image/svg+xml," + quote(svg)


def boton_contacto(d):
    if d.get("whatsapp"):
        texto = quote("Hola, vi su página y quiero más información.")
        return (f'<a class="boton boton-principal" href="https://wa.me/{e(d["whatsapp"])}?text={texto}" '
                f'target="_blank" rel="noopener">{ICONO_CHAT} Escribir por WhatsApp</a>')
    if d.get("telefono"):
        return (f'<a class="boton boton-principal" href="tel:+52{e(d["telefono"])}">'
                f'{ICONO_TEL} Llamar al {e(telefono_visible(d["telefono"]))}</a>')
    return ""


def bloque_estado(d):
    if not any((d.get("horario") or {}).values()):
        return ('<p class="estado-ahora">Horario por confirmar</p>'
                '<p class="estado-detalle">Pregunte directo al negocio.</p>')
    return ('<p class="estado-ahora"><span class="estado-punto"></span>'
            '<span data-estado-titulo>Consulte el horario</span></p>'
            '<p class="estado-detalle" data-estado-detalle>Vea la tabla de horario más abajo.</p>')


def bloque_resenas(d):
    if not d.get("calificacion") or not d.get("resenas"):
        return ""
    return ('<p class="estado-resenas"><strong>{cal}</strong>'
            '<span class="estrella" aria-hidden="true">★</span>'
            '<span>{n} reseñas en <a href="{url}" target="_blank" rel="noopener">Google</a></span></p>'
            ).format(cal=e(d["calificacion"]), n=e(d["resenas"]), url=e(d["maps_url"]))


def seccion_servicios(d):
    # Si el perfil no publica servicios, la sección no aparece.
    if not d.get("servicios"):
        return ""
    items = "\n".join(f"        <li>{e(s)}</li>" for s in d["servicios"])
    return ('  <section class="seccion" id="servicios">\n    <div class="contenedor">\n'
            '      <h2>Servicios</h2>\n      <ul class="servicios">\n'
            f'{items}\n      </ul>\n    </div>\n  </section>\n')


def bloque_horario(d):
    horario = d.get("horario") or {}
    if not any(horario.values()):
        return '<p class="seccion-entrada">El horario no está publicado. Pregunte directo al negocio.</p>'
    filas = []
    for clave, nombre in DIAS:
        tramos = horario.get(clave) or []
        if tramos:
            celda = "<td>" + "".join(f"<span>{hora(a)} a {hora(b)}</span>" for a, b in tramos) + "</td>"
        else:
            celda = '<td class="cerrado">Cerrado</td>'
        filas.append(
            f'          <tr data-dia="{clave}"><th scope="row">{nombre}'
            f'<span data-hoy hidden> (hoy)</span></th>{celda}</tr>'
        )
    return '<table class="horario">\n          <tbody>\n' + "\n".join(filas) + "\n          </tbody>\n        </table>"


def bloque_preguntas(d):
    medio = "WhatsApp" if d.get("whatsapp") else "teléfono"
    base = [
        ("¿Cómo agendo una cita?",
         f"Las citas se agendan directo con {d['nombre']}, por {medio}. Use el botón de contacto de esta página."),
        ("¿Cuánto cuesta?",
         f"Los precios los confirma {d['nombre']} directamente, porque dependen de cada caso."),
    ]
    propias = [(p["p"], p["r"]) for p in d.get("preguntas") or []]
    piezas = []
    for pregunta, respuesta in propias + base:
        piezas.append(
            f"        <details>\n          <summary>{e(pregunta)}</summary>\n"
            f"          <p>{e(respuesta)}</p>\n        </details>"
        )
    return "\n".join(piezas)


def generar(ruta):
    d = json.loads(ruta.read_text(encoding="utf-8"))
    validar(d, ruta.name)

    creada = date.fromisoformat(d["creada"])
    if d.get("telefono"):
        d["telefono_visible"] = telefono_visible(d["telefono"])

    aviso = "Vista previa preparada por Automia. No está publicada."
    if d.get("ejemplo"):
        aviso += " Negocio de ejemplo: los datos son ficticios."

    consulta = d.get("maps_consulta") or f"{d['nombre']}, {d['direccion']}"
    referencia = f'<span class="direccion-ref">{e(d["referencia"])}</span>' if d.get("referencia") else ""
    pie_tel = f'<p>Tel. {e(d["telefono_visible"])}</p>' if d.get("telefono") else ""

    # Lo que lee el asistente en el navegador. Solo datos públicos del negocio.
    publicos = {k: d[k] for k in (
        "nombre", "direccion", "referencia", "maps_url", "telefono", "telefono_visible",
        "whatsapp", "servicios", "horario", "preguntas") if d.get(k)}
    datos_json = json.dumps(publicos, ensure_ascii=False).replace("</", "<\\/")

    valores = {
        "giro": e(d["giro"]),
        "color_marca": GIROS[d["giro"]],
        "favicon": favicon(d),
        "giro_texto": e(d["giro_texto"]),
        "nombre": e(d["nombre"]),
        "zona": e(d["zona"]),
        "descripcion": e(d["descripcion"]),
        "aviso": e(aviso),
        "boton_contacto": boton_contacto(d),
        "bloque_estado": bloque_estado(d),
        "bloque_resenas": bloque_resenas(d),
        "seccion_servicios": seccion_servicios(d),
        "bloque_horario": bloque_horario(d),
        "direccion": e(d["direccion"]),
        "referencia": referencia,
        "mapa_src": e("https://www.google.com/maps?q=" + quote(consulta) + "&output=embed"),
        "maps_url": e(d["maps_url"]),
        "preguntas": bloque_preguntas(d),
        "pie_telefono": pie_tel,
        "caduca": fecha_larga(creada + timedelta(days=DIAS_VIGENCIA)),
        "datos_json": datos_json,
    }

    plantilla = PLANTILLA.read_text(encoding="utf-8")
    pendientes = set(re.findall(r"\{\{(\w+)\}\}", plantilla)) - set(valores)
    if pendientes:
        raise SystemExit(f"La plantilla pide valores que no existen: {', '.join(sorted(pendientes))}")
    pagina = re.sub(r"\{\{(\w+)\}\}", lambda m: valores[m.group(1)], plantilla)

    destino = RAIZ / d["slug"]
    destino.mkdir(exist_ok=True)
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    return d["slug"]


def vencidas():
    hoy = date.today()
    hay = False
    for ruta in sorted(DATOS.glob("*.json")):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        if d.get("ejemplo") or d.get("cliente"):
            continue
        limite = date.fromisoformat(d["creada"]) + timedelta(days=DIAS_VIGENCIA)
        if hoy > limite:
            hay = True
            print(f"{d['slug']}: venció el {fecha_larga(limite)}")
    if not hay:
        print("Ninguna vista previa vencida.")


def main():
    args = sys.argv[1:]
    if args == ["--vencidas"]:
        vencidas()
        return
    rutas = [DATOS / f"{a}.json" for a in args] if args else sorted(DATOS.glob("*.json"))
    if not rutas:
        raise SystemExit("No hay archivos en datos/")
    for ruta in rutas:
        if not ruta.exists():
            raise SystemExit(f"No existe {ruta}")
        print("Generada:", generar(ruta))


if __name__ == "__main__":
    main()
