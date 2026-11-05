import { env } from 'cloudflare:test'
import { afterEach, describe, expect, it } from 'vitest'
import { hoyEnChile } from '../src/lib/fields'
import { post } from './helpers'

const MENSAJE_500 = 'Tuvimos un problema. Intenta de nuevo en unos minutos.'

const manana = () => hoyEnChile(new Date(Date.now() + 86_400_000))
const valid = () => ({
  nombre: 'José Peña',
  rut: '12.345.678-5',
  correo: 'Jose@Correo.example',
  telefono: '+56 9 1111 1111',
  perro_nombre: 'Bruno',
  perro_raza: 'Quiltro',
  servicio: 'bano_corte',
  fecha: manana(),
  vacunas: 'si',
  retiro: 'no',
  direccion: '',
  mayor_edad: 'si',
})

afterEach(async () => {
  await env.DB.exec('ALTER TABLE reservas_rota RENAME TO reservas').catch(() => {})
})

describe('server errors', () => {
  it('a database failure gets a branded 500, not plain text', async () => {
    await env.DB.exec('ALTER TABLE reservas RENAME TO reservas_rota')
    const res = await post('/api/reserva', valid())
    expect(res.status).toBe(500)
    expect(await res.json()).toEqual({ ok: false, mensaje: MENSAJE_500 })
  })

  it('the branded 500 is HTML for form posts', async () => {
    await env.DB.exec('ALTER TABLE reservas RENAME TO reservas_rota')
    const res = await post('/api/reserva', valid(), { accept: 'html' })
    expect(res.status).toBe(500)
    expect(res.headers.get('content-type')).toMatch(/^text\/html/)
    expect(await res.text()).toContain(MENSAJE_500)
  })
})
