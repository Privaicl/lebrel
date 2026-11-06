import { SELF, env } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import { MSG_ANIOS } from '../src/activities/postulacion'
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
    for (const id of ['top', 'servicios', 'reservar', 'trabaja', 'contacto']) expect(html).toContain(`id="${id}"`)
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

  it('el formulario de postulación envía los campos que la API lee', async () => {
    const html = await get('/')
    const form = html.match(/<form[^>]*id="f-postulacion"[\s\S]*?<\/form>/)?.[0] ?? ''
    expect(form).toContain('action="/api/postulacion"')
    for (const campo of ['nombre', 'correo', 'telefono', 'comuna', 'experiencia_anios', 'experiencia', 'sitio_web'])
      expect(form).toContain(`name="${campo}"`)
  })

  it('la revisión del navegador usa los mismos mensajes que el servidor', async () => {
    const js = await get('/js/site.js')
    for (const texto of [MSG.falta, MSG.rut, MSG.correo, MSG.vacunas, MSG.mayor_edad]) expect(js).toContain(texto)
    expect(js).toContain("wire(document.getElementById('f-reserva')")
    expect(js).toContain("wire(document.getElementById('f-postulacion')")
    for (const texto of [MSG.largo, MSG_ANIOS]) expect(js).toContain(texto)
  })

  it('el formulario de reserva explica para qué usamos los datos y enlaza el centro de privacidad', async () => {
    const html = await get('/')
    const form = html.match(/<form[^>]*id="f-reserva"[\s\S]*?<\/form>/)?.[0] ?? ''
    expect(form).toContain(
      'Usamos tus datos para agendar y prestar el servicio. Más información en nuestro <a href="https://privacidad.lebrel.cl">Centro de privacidad</a>.',
    )
  })

  it('el formulario de postulación explica para qué usamos los datos y enlaza el centro de privacidad', async () => {
    const html = await get('/')
    const form = html.match(/<form[^>]*id="f-postulacion"[\s\S]*?<\/form>/)?.[0] ?? ''
    expect(form).toContain(
      'Usamos tus datos solo para evaluar tu postulación. Más información en nuestro <a href="https://privacidad.lebrel.cl">Centro de privacidad</a>.',
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

  it('cada cookie no esencial queda bloqueada hasta que se acepta su categoría en el banner', async () => {
    const html = await get('/')
    const scripts = {
      analytics: '/js/analytics.js',
      functional: '/js/preferencias.js',
      marketing: '/js/campanas.js',
    }
    for (const [categoria, src] of Object.entries(scripts)) {
      expect(html).toContain(`<script type="text/plain" data-category="${categoria}" src="${src}" defer></script>`)
      expect(html).not.toContain(`<script data-category="${categoria}"`)
    }
    // Ningún otro script de la página crea esas cookies.
    expect(await get('/js/site.js')).not.toMatch(/lb_(vid|pref|campana)/)
  })

  it('la dirección solo aparece, y es obligatoria, si se pide retiro a domicilio', async () => {
    const html = await get('/')
    expect(html).toContain('<div class="full" id="r-dir-campo">')
    expect(html).not.toMatch(/Dirección <span class="opt">\(opcional\)<\/span>/)

    // Corre site.js con un DOM mínimo y cambia el retiro.
    const el = () => ({ value: '', hidden: false, required: false, min: '', max: '', listeners: {} as Record<string, () => void>,
      addEventListener(tipo: string, fn: () => void) { this.listeners[tipo] = fn } })
    const retiro = el()
    const campo = el()
    const direccion = el()
    direccion.value = 'Av. Siempre Viva 742'
    const porSelector: Record<string, unknown> = {
      '#f-reserva [name=retiro]': retiro,
      '#r-dir-campo': campo,
      '#f-reserva [name=direccion]': direccion,
    }
    const document = { querySelector: (s: string) => porSelector[s] ?? el(), getElementById: () => el() }
    new Function('document', await get('/js/site.js'))(document)

    expect(campo.hidden).toBe(true)
    expect(direccion.required).toBe(false)
    expect(direccion.value).toBe('')

    retiro.value = 'si'
    retiro.listeners.change()
    expect(campo.hidden).toBe(false)
    expect(direccion.required).toBe(true)

    direccion.value = 'Av. Siempre Viva 742'
    retiro.value = 'no'
    retiro.listeners.change()
    expect(campo.hidden).toBe(true)
    expect(direccion.required).toBe(false)
    expect(direccion.value).toBe('')
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
