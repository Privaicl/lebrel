import { Hono } from 'hono'
import { handleCollect } from './activities/analitica'
import { handleReserva } from './activities/reserva'
import { CRON_PRIVAI, atenderPrivai } from './derechos'
import type { Env } from './env'
import { fail } from './lib/respond'
import { ensureSession, hasSession } from './lib/session'
import { purgeExpired } from './retention'

const app = new Hono<{ Bindings: Env }>()

app.onError((err, c) => {
  console.error(JSON.stringify({ evento: 'error', ruta: c.req.path, mensaje: String(err) }))
  return fail(c, { mensaje: 'Tuvimos un problema. Intenta de nuevo en unos minutos.' }, 'top', 500)
})

app.get('/', async (c) => ensureSession(c.req.raw, await c.env.ASSETS.fetch(c.req.raw)))
app.get('/index.html', async (c) => ensureSession(c.req.raw, await c.env.ASSETS.fetch(c.req.raw)))

// Todo POST a la API tiene que venir de nuestra página (header Origin en la lista permitida).
// Los formularios además piden la cookie de sesión. La baliza de analítica (/api/collect, que manda
// navigator.sendBeacon con su Origin) no la pide: la cookie de sesión es solo para los formularios.
app.use('/api/*', async (c, next) => {
  if (c.req.method !== 'POST') return next()
  const allowed = c.env.ALLOWED_ORIGINS.split(',').map((o) => o.trim())
  const origin = c.req.header('origin') ?? ''
  const pideSesion = c.req.path !== '/api/collect'
  if (!allowed.includes(origin) || (pideSesion && !hasSession(c.req.raw))) {
    return fail(c, { mensaje: 'No pudimos validar el envío. Recarga la página e intenta de nuevo.' }, 'top', 403)
  }
  return next()
})

app.post('/api/reserva', handleReserva)
app.post('/api/collect', handleCollect)

export default {
  fetch: app.fetch,
  scheduled(event: ScheduledController, env: Env, ctx: ExecutionContext) {
    if (event.cron === CRON_PRIVAI) ctx.waitUntil(atenderPrivai(env))
    else ctx.waitUntil(purgeExpired(env.DB, new Date(event.scheduledTime)))
  },
}
