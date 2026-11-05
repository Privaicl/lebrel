import { SELF } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import { ensureSession } from '../src/lib/session'
import { post } from './helpers'

describe('lb_session', () => {
  it('ensureSession sets lb_session when absent', () => {
    const res = ensureSession(new Request('https://lebrel.cl/'), new Response('ok'))
    expect(res.headers.get('set-cookie')).toMatch(
      /^lb_session=[0-9a-f-]{36}; Path=\/; HttpOnly; Secure; SameSite=Lax$/,
    )
  })

  it('ensureSession leaves an existing session alone', () => {
    const req = new Request('https://lebrel.cl/', { headers: { cookie: 'lb_session=abc' } })
    const res = ensureSession(req, new Response('ok'))
    expect(res.headers.get('set-cookie')).toBeNull()
  })
})

describe('form origin check', () => {
  it('POST /api/reserva without lb_session is 403', async () => {
    const res = await post('/api/reserva', {}, { cookie: null })
    expect(res.status).toBe(403)
    expect(((await res.json()) as { mensaje: string }).mensaje).toBe('No pudimos validar el envío. Recarga la página e intenta de nuevo.')
  })

  it('POST /api/reserva from another origin is 403', async () => {
    const res = await post('/api/reserva', {}, { origin: 'https://evil.example' })
    expect(res.status).toBe(403)
  })

  it('POST /api/collect needs an allowed origin but no lb_session', async () => {
    const res = await SELF.fetch('https://lebrel.cl/api/collect', {
      method: 'POST',
      headers: { origin: 'https://lebrel.cl' },
      body: '{}',
    })
    expect(res.status).not.toBe(403)
    const sinOrigen = await SELF.fetch('https://lebrel.cl/api/collect', { method: 'POST', body: '{}' })
    expect(sinOrigen.status).toBe(403)
  })
})
