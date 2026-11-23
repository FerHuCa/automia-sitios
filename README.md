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

## Reglas

- Solo datos que el propio negocio publica. Si falta un dato, ese bloque no aparece.
- No se copian reseñas ni fotos.
- El asistente responde con esos mismos datos, nunca da precios y no guarda nada.

## Demo de autofacturación

`autofacturacion-demo/` es una sola página estática con datos ficticios que muestra el flujo del portal de autofacturación CFDI 4.0 (constancia, claves SAT, listo). No guarda ni envía datos, no usa servicios externos ni cookies, no aparece en buscadores y avisa en cada pantalla que las facturas son de prueba, sin validez ante el SAT. No lleva precios ni promete fecha de salida en vivo. Liga: `https://ferhuca.github.io/automia-sitios/autofacturacion-demo/`.
