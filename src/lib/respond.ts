import type { Context } from 'hono'
import type { ContentfulStatusCode } from 'hono/utils/http-status'

// Los formularios funcionan con y sin JavaScript: con JS pedimos JSON;
// sin JS el navegador recibe una página corta con el mensaje.

function wantsJson(c: Context): boolean {
  return (c.req.header('accept') ?? '').includes('application/json')
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`)
}

function page(mensaje: string, seccion: string): string {
  return `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lebrel</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital@0;1&family=IBM+Plex+Mono&display=swap" rel="stylesheet">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f2eff8;color:#211a3a;font:400 18px/1.6 system-ui,sans-serif}
main{max-width:34em;padding:24px}p{font:400 clamp(28px,5vw,44px)/1.15 "Cormorant Garamond",Georgia,serif;margin:0 0 28px}
a{font:400 14px "IBM Plex Mono",monospace;color:#6236c9}</style></head>
<body><main><p>${escapeHtml(mensaje)}</p><a href="/#${escapeHtml(seccion)}">Volver</a></main></body></html>`
}

export function ok(c: Context, mensaje: string, seccion: string, status: ContentfulStatusCode = 201) {
  return wantsJson(c) ? c.json({ ok: true, mensaje }, status) : c.html(page(mensaje, seccion), status)
}

export function fail(
  c: Context,
  err: { message?: string; mensaje?: string; campo?: string },
  seccion: string,
  status: ContentfulStatusCode = 400,
) {
  const mensaje = err.mensaje ?? err.message ?? ''
  return wantsJson(c)
    ? c.json({ ok: false, campo: err.campo, mensaje }, status)
    : c.html(page(mensaje, seccion), status)
}
