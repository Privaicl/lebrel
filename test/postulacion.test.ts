import { env } from 'cloudflare:test'
import { beforeEach, describe, expect, it } from 'vitest'
import { MENSAJE_OK_POSTULACION, MSG_ANIOS } from '../src/activities/postulacion'
import { MSG } from '../src/lib/fields'
import { post } from './helpers'

const valid = () => ({
  nombre: 'Ñancu Peña',
  correo: 'Nancu@Correo.example',
  telefono: '+56 9 2222 2222',
  comuna: 'Ñuñoa',
  experiencia_anios: '3',
  experiencia: 'Peluquería canina en una clínica durante tres años.',
})

type Row = Record<string, unknown>
const rows = async () => (await env.DB.prepare('SELECT * FROM postulaciones').all<Row>()).results

beforeEach(async () => {
  await env.DB.exec('DELETE FROM postulaciones')
})

describe('POST /api/postulacion', () => {
  it('stores a valid application', async () => {
    const res = await post('/api/postulacion', valid())
    expect(res.status).toBe(201)
    expect(((await res.json()) as Row).mensaje).toBe(MENSAJE_OK_POSTULACION)
    const all = await rows()
    expect(all.length).toBe(1)
    expect(all[0]).toMatchObject({
      nombre: 'Ñancu Peña',
      correo: 'nancu@correo.example',
      telefono: '+56922222222',
      comuna: 'Ñuñoa',
      experiencia_anios: 3,
    })
  })

  it.each(['abc', '-1', '51', '2.5'])('experiencia_anios must be 0–50 (%s)', async (v) => {
    const res = await post('/api/postulacion', { ...valid(), experiencia_anios: v })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'experiencia_anios', mensaje: 'Escribe un número de años entre 0 y 50.' })
    expect(MSG_ANIOS).toBe('Escribe un número de años entre 0 y 50.')
    expect((await rows()).length).toBe(0)
  })

  it('accepts the limits 0 and 50', async () => {
    expect((await post('/api/postulacion', { ...valid(), experiencia_anios: '0' })).status).toBe(201)
    expect((await post('/api/postulacion', { ...valid(), experiencia_anios: '50' })).status).toBe(201)
  })

  it('experiencia max 1000 chars', async () => {
    const res = await post('/api/postulacion', { ...valid(), experiencia: 'ñ'.repeat(1001) })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'experiencia', mensaje: MSG.largo })
    expect((await rows()).length).toBe(0)
  })

  it('honeypot pretends success', async () => {
    const res = await post('/api/postulacion', { ...valid(), sitio_web: 'x' })
    expect(res.status).toBe(201)
    expect((await rows()).length).toBe(0)
  })

  it('HTML response links to #trabaja', async () => {
    const res = await post('/api/postulacion', valid(), { accept: 'html' })
    expect(res.status).toBe(201)
    const html = await res.text()
    expect(html).toContain(MENSAJE_OK_POSTULACION)
    expect(html).toContain('href="/#trabaja"')
  })
})
