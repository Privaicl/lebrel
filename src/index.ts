import { Hono } from 'hono'
import type { Env } from './env'
import { fail } from './lib/respond'
import { ensureSession, hasSession } from './lib/session'

const app = new Hono<{ Bindings: Env }>()

app.onError((err, c) => {
  console.error(JSON.stringify({ evento: 'error', ruta: c.req.path, mensaje: String(err) }))
  return fail(c, { mensaje: 'Tuvimos un problema. Intenta de nuevo en unos minutos.' }, 'top', 500)
})

app.get('/', async (c) => ensureSession(c.req.raw, await c.env.ASSETS.fetch(c.req.raw)))
app.get('/index.html', async (c) => ensureSession(c.req.raw, await c.env.ASSETS.fetch(c.req.raw)))

// Los formularios solo se aceptan desde nuestra página: mismo origen y con cookie de sesión.
app.use('/api/*', async (c, next) => {
  if (c.req.method !== 'POST') return next()
  const allowed = c.env.ALLOWED_ORIGINS.split(',').map((o) => o.trim())
  const origin = c.req.header('origin') ?? ''
  if (!allowed.includes(origin) || !hasSession(c.req.raw)) {
    return fail(c, { mensaje: 'No pudimos validar el envío. Recarga la página e intenta de nuevo.' }, 'top', 403)
  }
  return next()
})

export default { fetch: app.fetch }
