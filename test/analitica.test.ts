import { SELF, env } from 'cloudflare:test'
import { beforeEach, describe, expect, it } from 'vitest'

type Row = Record<string, unknown>
const rows = async () => (await env.DB.prepare('SELECT * FROM visitas').all<Row>()).results
const VID = '0b5c3a52-8f0e-4f1e-9d6e-3c1f2a7b9e10'

// navigator.sendBeacon manda el Origin de la página, pero no hace falta la cookie de sesión.
function collect(payload: unknown, origin = 'https://lebrel.cl') {
  return SELF.fetch('https://lebrel.cl/api/collect', {
    method: 'POST',
    headers: { 'content-type': 'text/plain;charset=UTF-8', 'user-agent': 'TestUA/1.0', origin },
    body: JSON.stringify(payload),
  })
}

beforeEach(async () => {
  await env.DB.exec('DELETE FROM visitas')
})

describe('POST /api/collect', () => {
  it('records a visit', async () => {
    const res = await collect({ vid: VID, ruta: '/', referente: null })
    expect(res.status).toBe(204)
    const [row] = await rows()
    expect(row).toMatchObject({ visitor_id: VID, ruta: '/', user_agent: 'TestUA/1.0' })
  })

  it('accepts a beacon from an allowed origin without a session cookie', async () => {
    const res = await collect({ vid: VID, ruta: '/#servicios' }, 'https://lebrel.privai-demo.workers.dev')
    expect(res.status).toBe(204)
    expect((await rows()).length).toBe(1)
  })

  it('rejects a beacon from a foreign origin', async () => {
    const res = await collect({ vid: VID, ruta: '/' }, 'https://otro.example')
    expect(res.status).toBe(403)
    expect((await rows()).length).toBe(0)
  })

  it('rejects a beacon without an origin', async () => {
    const res = await collect({ vid: VID, ruta: '/' }, '')
    expect(res.status).toBe(403)
    expect((await rows()).length).toBe(0)
  })

  it('rejects a non-uuid visitor id', async () => {
    const res = await collect({ vid: 'nope', ruta: '/' })
    expect(res.status).toBe(400)
    expect((await rows()).length).toBe(0)
  })

  it('truncates long paths', async () => {
    await collect({ vid: VID, ruta: `/${'a'.repeat(999)}` })
    const [row] = await rows()
    expect(String(row.ruta)).toHaveLength(300)
  })
})
