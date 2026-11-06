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

  it('el formulario de reserva explica para qué usamos los datos y enlaza el centro de privacidad', async () => {
    const html = await get('/')
    const form = html.match(/<form[^>]*id="f-reserva"[\s\S]*?<\/form>/)?.[0] ?? ''
    expect(form).toContain(
      'Usamos tus datos para agendar y prestar el servicio. Más información en nuestro <a href="https://privacidad.lebrel.cl">Centro de privacidad</a>.',
    )
  })

  it('el banner usa la cookie de .lebrel.cl solo en lebrel.cl y sus subdominios', async () => {
    const html = await get('/')
    const script = html.match(/<script>([\s\S]*?window\.privaiConfig[\s\S]*?)<\/script>/)?.[1] ?? ''
    const config = (hostname: string) => {
      const window: { privaiConfig?: Record<string, unknown> } = {}
      new Function('window', 'location', script)(window, { hostname })
      return window.privaiConfig ?? {}
    }
    expect(config('lebrel.cl').cookieDomain).toBe('.lebrel.cl')
    expect(config('www.lebrel.cl').cookieDomain).toBe('.lebrel.cl')
    for (const host of ['lebrel.privai-demo.workers.dev', 'localhost', 'notlebrel.cl']) {
      expect(config(host)).not.toHaveProperty('cookieDomain')
    }
    expect(config('lebrel.cl').deploymentId).toBe('0c1691ab-13e5-453e-b365-641e012ecff1')
  })

  it('las cookies no esenciales se crean al cargar la página, para que el escáner de Privai las detecte', async () => {
    const html = await get('/')
    const scripts = {
      analytics: '/js/analytics.js',
      functional: '/js/preferencias.js',
      marketing: '/js/campanas.js',
    }
    for (const [categoria, src] of Object.entries(scripts)) {
      // Se cargan como scripts normales; data-category queda marcado para cuando Privai las bloquee.
      expect(html).toContain(`<script data-category="${categoria}" src="${src}" defer></script>`)
      expect(html).not.toContain(`type="text/plain" data-category="${categoria}"`)
    }
  })

  it('preferencias y campañas crean su cookie sin esperar a que el visitante haga algo', async () => {
    const correr = async (src: string, search = '') => {
      const doc = { cookie: '', querySelector: () => null }
      new Function('document', 'location', await get(src))(doc, { protocol: 'https:', search })
      return doc.cookie
    }
    expect(await correr('/js/preferencias.js')).toMatch(/^lb_pref=[^;]+; Max-Age=31536000; Path=\/; SameSite=Lax; Secure$/)
    expect(await correr('/js/campanas.js')).toMatch(/^lb_campana=directo; Max-Age=7776000;/)
    expect(await correr('/js/campanas.js', '?utm_source=instagram&utm_campaign=verano')).toMatch(
      /^lb_campana=instagram%7Cverano;/,
    )
  })
})
