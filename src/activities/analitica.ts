import type { Context } from 'hono'
import type { Env } from '../env'

// Analítica del sitio: /js/analytics.js manda una baliza por visita con el id de la cookie lb_vid.

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const MAX = 300

const clip = (v: unknown): string | null => (typeof v === 'string' && v ? [...v].slice(0, MAX).join('') : null)

export async function handleCollect(c: Context<{ Bindings: Env }>): Promise<Response> {
  let data: { vid?: unknown; ruta?: unknown; referente?: unknown }
  try {
    data = JSON.parse(await c.req.text())
  } catch {
    return c.body(null, 400)
  }
  const ruta = clip(data?.ruta)
  if (typeof data?.vid !== 'string' || !UUID.test(data.vid) || !ruta) return c.body(null, 400)

  await c.env.DB.prepare(
    'INSERT INTO visitas (visitor_id, ruta, referente, user_agent, created_at) VALUES (?, ?, ?, ?, ?)',
  )
    .bind(data.vid, ruta, clip(data.referente), clip(c.req.header('user-agent')), new Date().toISOString())
    .run()
  return c.body(null, 204)
}
