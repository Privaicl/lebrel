import { SELF, env } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import { SERVICIOS } from '../src/activities/reserva'
import { MSG } from '../src/lib/fields'

// La página y la API tienen que calzar: mismos nombres de campo, mismas opciones y mismos mensajes.

// La portada pasa por el Worker; el resto son archivos estáticos que sirve ASSETS.
async function get(path: string): Promise<string> {
  const url = `https://lebrel.cl${path}`
  const res = await (path === '/' ? SELF.fetch(url) : env.ASSETS.fetch(url))
  expect(res.status).toBe(200)
  return res.text()
}

describe('página', () => {
  it('tiene las secciones que enlazan la nav y las tareas siguientes', async () => {
    const html = await get('/')
    for (const id of ['top', 'servicios', 'reservar', 'contacto']) expect(html).toContain(`id="${id}"`)
    expect(html).toMatch(/<nav>[\s\S]*class="links"/)
    expect(html).toContain('Sitio ficticio de demostración — no ingreses datos reales.')
    expect(html).toContain('Peluquería Canina Lebrel SpA · RUT 77.123.456-9')
  })

  it('el formulario de reserva envía los campos que la API lee', async () => {
    const html = await get('/')
    const form = html.match(/<form[^>]*id="f-reserva"[\s\S]*?<\/form>/)?.[0] ?? ''
    expect(form).toContain('action="/api/reserva"')
    const campos = [
      'nombre', 'rut', 'correo', 'telefono', 'perro_nombre', 'perro_raza', 'servicio',
      'fecha', 'vacunas', 'retiro', 'direccion', 'mayor_edad', 'sitio_web',
    ]
    for (const campo of campos) expect(form).toContain(`name="${campo}"`)
    const servicios = [...form.matchAll(/<option value="([a-z_]+)"/g)].map((m) => m[1])
    for (const s of SERVICIOS) expect(servicios).toContain(s)
    expect(form).toMatch(/name="mayor_edad"[^>]*value="si"|value="si"[^>]*name="mayor_edad"/)
  })

  it('la revisión del navegador usa los mismos mensajes que el servidor', async () => {
    const js = await get('/js/site.js')
    for (const texto of [MSG.falta, MSG.rut, MSG.correo, MSG.vacunas, MSG.mayor_edad]) expect(js).toContain(texto)
    expect(js).toContain("wire(document.getElementById('f-reserva')")
  })
})
