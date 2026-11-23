#!/usr/bin/env python3
"""Pruebas de la plantilla v2 y de que las demos ya publicadas no cambian."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

import generar  # noqa: E402
import v2  # noqa: E402

EJEMPLO = RAIZ / "tools" / "ejemplos" / "consultorio-los-encinos.json"

# El HTML publicado de estas dos ya no coincide con su JSON: la dirección
# se ajustó en la página y el archivo de datos no se volvió a generar.
# El generador v1 sigue produciendo lo que dice el JSON. No es un cambio de la v2.
DIRECCION_PREVIA = {
    "odontologia-atm-coapa": (
        "Coapa 11-consultorio 506, Toriello Guerra, CDMX",
        "Coapa 11, Toriello Guerra, CDMX",
    ),
    "duovet-toluca": (
        "Av. J. M. Morelos Y P. 4 Ote. 925, Vértice, Toluca",
        "Av. J. M. Morelos 925, Vértice, Toluca",
    ),
}


def claves(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for clave, valor in obj.items():
            acc.add(clave)
            claves(valor, acc)
    elif isinstance(obj, list):
        for valor in obj:
            claves(valor, acc)
    return acc


def jsonld_de(html):
    inicio = html.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
    fin = html.index("</script>", inicio)
    return json.loads(html[inicio:fin].replace("\\u003c", "<"))


def ficha(giro, **extra):
    d = {
        "slug": "ficha-" + giro,
        "creada": "2026-11-23",
        "giro": giro,
        "giro_texto": "Giro de prueba",
        "nombre": "Negocio de prueba",
        "zona": "Centro, Toluca",
        "descripcion": "Horario y contacto de muestra.",
        "telefono": "7220000000",
        "telefono_visible": "722 000 0000",
        "direccion": "Calle Ficticia 100, Toluca",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Calle+Ficticia+100",
        "horario": {"lun": [["09:00", "14:00"]], "mar": [], "mie": [], "jue": [], "vie": [], "sab": [], "dom": []},
    }
    d.update(extra)
    return d


def prueba_tipos():
    esperados = {
        "dental": "Dentist",
        "optica": "Optician",
        "veterinaria": "VeterinaryCare",
        "psicologia": "MedicalBusiness",
        "fisioterapia": "MedicalBusiness",
        "nutricion": "MedicalBusiness",
    }
    for giro, tipo in esperados.items():
        datos = v2.construir_jsonld(ficha(giro), "https://ferhuca.github.io/automia-sitios/x/", "https://ferhuca.github.io/automia-sitios/x/og.png")
        assert datos["@type"] == tipo, (giro, datos["@type"])
        assert "aggregateRating" not in claves(datos)
        assert "review" not in claves(datos)
        assert "postalCode" not in datos["address"]
        if giro == "fisioterapia":
            assert datos["medicalSpecialty"] == "https://schema.org/Physiotherapy"
        elif giro == "nutricion":
            assert datos["medicalSpecialty"] == "https://schema.org/DietNutrition"
        else:
            assert "medicalSpecialty" not in datos
    con_cp = ficha("dental", direccion_partes={"calle": "Calle Ficticia 100", "localidad": "Toluca", "region": "Estado de México", "cp": "50000"}, geo={"latitud": 19.29, "longitud": -99.65})
    datos = v2.construir_jsonld(con_cp, "https://ferhuca.github.io/automia-sitios/x/", "https://ferhuca.github.io/automia-sitios/x/og.png")
    assert datos["address"]["postalCode"] == "50000"
    assert datos["address"]["addressLocality"] == "Toluca"
    assert datos["geo"]["latitude"] == 19.29
    assert datos["sameAs"] == [con_cp["maps_url"]]
    assert datos["telephone"] == "+52 722 000 0000"
    assert datos["openingHoursSpecification"][0]["dayOfWeek"] == ["Monday"]
    assert datos["openingHoursSpecification"][0]["opens"] == "09:00"
    partido = ficha("dental", horario={"lun": [["09:00", "14:00"], ["16:00", "19:00"]], "sab": [["09:00", "14:00"]]})
    specs = v2.horarios_jsonld(partido)
    assert {"opens": "09:00", "closes": "14:00", "dias": ["Monday", "Saturday"]} == {
        "opens": specs[0]["opens"], "closes": specs[0]["closes"], "dias": specs[0]["dayOfWeek"],
    }
    assert specs[1]["dayOfWeek"] == ["Monday"] and specs[1]["opens"] == "16:00"


def prueba_ejemplo(tmp):
    destino = Path(tmp)
    slug = generar.generar(EJEMPLO, destino)
    html = (destino / slug / "index.html").read_text(encoding="utf-8")
    assert "noindex, nofollow" in html
    assert "Vista previa preparada por Automia. No está publicada." in html
    assert "Negocio de ejemplo: los datos son ficticios." in html
    assert "Quiero%20agendar%20una%20cita" in html
    assert html.count("https://wa.me/527220000000?text=Quiero%20agendar%20una%20cita") == 4
    assert 'href="tel:+527220000000"' in html
    assert "Agendar por WhatsApp" in html
    assert "barra-contacto" in html
    assert "og:locale" in html and "es_MX" in html
    assert 'property="og:type" content="website"' in html
    assert 'property="og:url" content="https://ferhuca.github.io/automia-sitios/consultorio-los-encinos/"' in html
    assert 'property="og:image" content="https://ferhuca.github.io/automia-sitios/consultorio-los-encinos/og.png"' in html
    assert "og:image:width" in html and "1200" in html and "630" in html
    assert "Odontología general" in html and "Dentista infantil" in html
    assert "¿Qué servicios ofrecen?" in html
    assert "¿Atienden a niños?" in html
    assert "Dra. Elena Prado" in html
    assert "Cédula profesional: 00000000" in html
    assert "Me explicaron con calma" in html
    assert "img/recepcion.jpg" in html
    assert "por confirmar" not in html and "EJEMPLO" not in html and "foto-vacia" not in html
    assert "\u2014" not in html and "\u2013" not in html
    assert "sitio-v2.js" in html and "mejoras-v2.css" in html
    datos = jsonld_de(html)
    assert datos["@type"] == "Dentist"
    assert datos["address"]["postalCode"] == "50000"
    assert "aggregateRating" not in claves(datos) and "review" not in claves(datos)
    publico = json.loads(html.split('id="datos">', 1)[1].split("</script>", 1)[0])
    assert "Odontopediatría (Dentista infantil)" in publico["servicios"]
    assert any("servicios" in " ".join(p.get("claves", [])) for p in publico["preguntas"])
    assert publico["profesional"]["cedula"] == "00000000"
    from PIL import Image
    imagen = Image.open(destino / slug / "og.png")
    assert imagen.size == (1200, 630)
    claros = 0
    for pixel in imagen.crop((72, 180, 900, 420)).get_flattened_data():
        if sum(pixel) > 700:
            claros += 1
    assert claros > 20

    sin_permiso = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    sin_permiso["permisos"] = {"resenas": False, "fotos": False, "cedula": False}
    sin_permiso["slug"] = "consultorio-sin-permiso"
    ruta = Path(tmp) / "consultorio-sin-permiso.json"
    ruta.write_text(json.dumps(sin_permiso), encoding="utf-8")
    generar.generar(ruta, tmp)
    oculto = (Path(tmp) / "consultorio-sin-permiso" / "index.html").read_text(encoding="utf-8")
    assert "Dra. Elena Prado" not in oculto
    assert "Cédula profesional" not in oculto
    assert "Me explicaron con calma" not in oculto
    assert "id=\"resenas\"" not in oculto
    assert "<img " not in oculto
    assert "Odontología general" in oculto
    assert "Sanitarios accesibles" in oculto

    sin_wa = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    sin_wa.pop("whatsapp")
    sin_wa["permisos"] = {"resenas": False, "fotos": False, "cedula": False}
    sin_wa["slug"] = "consultorio-sin-whatsapp"
    ruta = Path(tmp) / "consultorio-sin-whatsapp.json"
    ruta.write_text(json.dumps(sin_wa), encoding="utf-8")
    generar.generar(ruta, tmp)
    solo = (Path(tmp) / "consultorio-sin-whatsapp" / "index.html").read_text(encoding="utf-8")
    assert "wa.me" not in solo
    assert "Agendar por WhatsApp" not in solo
    assert "barra-una" in solo
    assert solo.count("> Llamar<") >= 3
    assert "Llame para agendar." in solo


def prueba_publicadas_intactas():
    for rel in ("assets/sitio.js", "assets/sitio.css", "tools/plantilla.html"):
        comprometido = subprocess.check_output(["git", "show", f"HEAD:{rel}"], cwd=RAIZ)
        assert comprometido == (RAIZ / rel).read_bytes(), rel
    with tempfile.TemporaryDirectory() as tmp:
        for ruta in sorted((RAIZ / "datos").glob("*.json")):
            slug = generar.generar(ruta, tmp)
            generado = (Path(tmp) / slug / "index.html").read_text(encoding="utf-8")
            publicado = (RAIZ / slug / "index.html").read_text(encoding="utf-8")
            if slug in DIRECCION_PREVIA:
                vieja, nueva = DIRECCION_PREVIA[slug]
                publicado = publicado.replace(vieja, nueva)
            assert generado == publicado, slug
            assert "mejoras-v2" not in generado
            assert "sitio-v2.js" not in generado
            assert "og:title" not in generado
            assert "barra-contacto" not in generado
    estado = subprocess.check_output(["git", "status", "--porcelain"], cwd=RAIZ, text=True)
    for linea in estado.splitlines():
        ruta = linea[3:]
        if ruta.endswith("/index.html"):
            raise SystemExit("una demo publicada cambió: " + ruta)


def prueba_previa_local():
    subprocess.check_call(
        [sys.executable, "tools/generar.py", "--previa", "tools/ejemplos/consultorio-los-encinos.json"],
        cwd=RAIZ,
    )
    pagina = RAIZ / "vista-previa" / "consultorio-los-encinos" / "index.html"
    assert pagina.is_file()
    assert not (RAIZ / "consultorio-los-encinos").exists()
    html = pagina.read_text(encoding="utf-8")
    assert "../../assets/sitio-v2.js" in html
    assert "../../assets/mejoras-v2.css" in html
    assert (RAIZ / "vista-previa" / "consultorio-los-encinos" / "og.png").is_file()
    assert (RAIZ / "vista-previa" / "consultorio-los-encinos" / "img" / "recepcion.jpg").is_file()


def main():
    prueba_tipos()
    with tempfile.TemporaryDirectory() as tmp:
        prueba_ejemplo(tmp)
    prueba_publicadas_intactas()
    prueba_previa_local()
    print("ok")


if __name__ == "__main__":
    main()
