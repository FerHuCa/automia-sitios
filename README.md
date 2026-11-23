# automia-sitios

Vistas previas de páginas web que Automia prepara para negocios locales.

Cada carpeta es la vista previa de un negocio. Se arma solo con la información
que el negocio ya publica en su perfil de Google. Todas llevan un aviso visible
de que son una muestra, no aparecen en buscadores y se borran a los 14 días si
el negocio no responde.

Si una de estas páginas es de su negocio y quiere que la quitemos, escriba a
automia.consultoria@gmail.com y la borramos el mismo día.

## Cómo se arma una vista previa

1. Crear `datos/<slug>.json` con los datos públicos del negocio (ver `datos/ejemplo-dental.json`).
2. Ejecutar `python3 tools/generar.py <slug>`.
3. Subir los cambios. La página queda en `https://ferhuca.github.io/automia-sitios/<slug>/`.

`python3 tools/generar.py --vencidas` lista las que ya pasaron de 14 días.

## Plantilla v2

Las vistas previas que ya están en el repositorio siguen con la plantilla actual. Una demo nueva usa la v2 solo si su JSON trae `"plantilla": "v2"`. Sin esa marca, `generar.py` arma la página de siempre.

1. Crear `datos/<slug>.json` como siempre, con `"plantilla": "v2"`.
2. Servicios: una lista de textos, o de objetos `{"nombre": "...", "detalle": "..."}` cuando el perfil de Google trae la categoría y un detalle. `"servicios_origen": "categorias"` indica que esa lista sale de las categorías del perfil.
3. Dirección para los datos estructurados, solo con lo que sí está publicado: `direccion_partes` con `calle`, `localidad`, `region` y `cp` (5 dígitos). Si no hay código postal, no se pone el campo. `geo` con `latitud` y `longitud`, si el perfil las trae.
4. Ejecutar `python3 tools/generar.py <slug>`. Hace falta Pillow para la imagen de 1200 x 630: `python3 -m pip install pillow`.

Para ver el ejemplo ficticio sin publicarlo:

```
python3 tools/generar.py --previa tools/ejemplos/consultorio-los-encinos.json
```

Eso escribe `vista-previa/consultorio-los-encinos/`. Esa carpeta está en `.gitignore` y no se sube. Sirva el repositorio y abra `/vista-previa/consultorio-los-encinos/`.

### Permiso para reseñas, fotos y cédula

Esas tres partes no se generan solas. Hacen falta el dato y el permiso del negocio, en `permisos`. Si el permiso está en false, o no viene, esa parte no se pinta aunque el dato esté en el archivo.

```json
"permisos": {
  "resenas": true,
  "fotos": true,
  "cedula": true
}
```

- `resenas`: lista `resenas_texto` con `texto`, `autor` y, si viene en la reseña, `estrellas` del 1 al 5.
- `fotos`: lista `fotos` con `archivo` (ruta junto al JSON, por ejemplo `img/recepcion.jpg`) y `alt`. `pie` es opcional.
- `cedula`: objeto `profesional` con `nombre`, `cedula`, o los dos.

`distintivos` (atributos que el perfil ya publica, como acceso en silla de ruedas) se muestra si la lista trae textos. No usa estos permisos.

No se dejan recuadros vacíos ni textos de "por confirmar".

### Tipo de negocio (JSON-LD)

| Giro | @type | Nota |
| --- | --- | --- |
| dental | Dentist | tipo de negocio en schema.org |
| optica | Optician | tipo de negocio en schema.org |
| veterinaria | VeterinaryCare | tipo de negocio en schema.org |
| psicologia | MedicalBusiness | como se pidió para este giro |
| fisioterapia | MedicalBusiness | `Physiotherapy` es una especialidad, no un tipo de negocio. Se anota en `medicalSpecialty`. |
| nutricion | MedicalBusiness | `DietNutrition` también es una especialidad, no un tipo de negocio. Se anota en `medicalSpecialty`. |

El bloque lleva nombre, dirección, teléfono, horario, coordenadas si existen, url y `sameAs` a la ficha de Google. No lleva calificación ni reseñas. Si falta el código postal, ese campo no va.

## Reglas

- Solo datos que el propio negocio publica. Si falta un dato, ese bloque no aparece.
- No se copian reseñas ni fotos.
- El asistente responde con esos mismos datos, nunca da precios y no guarda nada.

## Demo de autofacturación

`autofacturacion-demo/` es una sola página estática con datos ficticios que muestra el flujo del portal de autofacturación CFDI 4.0 (constancia, claves SAT, listo). No guarda ni envía datos, no usa servicios externos ni cookies, no aparece en buscadores y avisa en cada pantalla que las facturas son de prueba, sin validez ante el SAT. No lleva precios ni promete fecha de salida en vivo. Liga: `https://ferhuca.github.io/automia-sitios/autofacturacion-demo/`.
