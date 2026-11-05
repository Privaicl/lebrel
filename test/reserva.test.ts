import { env } from 'cloudflare:test'
import { beforeEach, describe, expect, it } from 'vitest'
import { MENSAJE_OK } from '../src/activities/reserva'
import { MSG, hoyEnChile } from '../src/lib/fields'
import { post } from './helpers'

const manana = () => {
  const d = new Date(Date.now() + 86_400_000)
  return hoyEnChile(d)
}
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

type Row = Record<string, unknown>
const rows = async () => (await env.DB.prepare('SELECT * FROM reservas').all<Row>()).results

beforeEach(async () => {
  await env.DB.exec('DELETE FROM reservas')
})

describe('POST /api/reserva', () => {
  it('stores a valid booking', async () => {
    const res = await post('/api/reserva', valid())
    expect(res.status).toBe(201)
    expect(((await res.json()) as Row).mensaje).toBe(MENSAJE_OK)
    const all = await rows()
    expect(all.length).toBe(1)
    expect(all[0]).toMatchObject({
      rut: '12345678-5',
      correo: 'jose@correo.example',
      servicio: 'bano_corte',
      vacunas_al_dia: 1,
      retiro: 0,
      direccion: null,
      declara_mayor_edad: 1,
    })
  })

  it('keeps ñ and accents', async () => {
    await post('/api/reserva', valid())
    const [row] = await rows()
    expect(row.nombre).toBe('José Peña')
  })

  it('retiro=no ignores the address', async () => {
    await post('/api/reserva', { ...valid(), retiro: 'no', direccion: 'Calle Falsa 0' })
    const [row] = await rows()
    expect(row.direccion).toBeNull()
  })

  it('retiro=si requires the address', async () => {
    const res = await post('/api/reserva', { ...valid(), retiro: 'si', direccion: '' })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'direccion', mensaje: MSG.falta })
    expect((await rows()).length).toBe(0)
  })

  it('retiro=si stores the address', async () => {
    await post('/api/reserva', { ...valid(), retiro: 'si', direccion: 'Calle Falsa 0, Ñuñoa' })
    const [row] = await rows()
    expect(row.direccion).toBe('Calle Falsa 0, Ñuñoa')
  })

  it('guardería without vaccines is rejected', async () => {
    const res = await post('/api/reserva', { ...valid(), servicio: 'guarderia', vacunas: 'no' })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'vacunas', mensaje: MSG.vacunas })
    expect((await rows()).length).toBe(0)
  })

  it('rejects missing mayor_edad', async () => {
    const { mayor_edad: _m, ...rest } = valid()
    const res = await post('/api/reserva', rest)
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'mayor_edad', mensaje: MSG.mayor_edad })
    expect((await rows()).length).toBe(0)
  })

  it('rejects a past date', async () => {
    const res = await post('/api/reserva', { ...valid(), fecha: '2020-01-01' })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'fecha' })
  })

  it('rejects an unknown service', async () => {
    const res = await post('/api/reserva', { ...valid(), servicio: 'spa' })
    expect(res.status).toBe(400)
    expect(await res.json()).toMatchObject({ campo: 'servicio', mensaje: MSG.opcion })
  })

  it('rejects bad RUT', async () => {
    const res = await post('/api/reserva', { ...valid(), rut: '11.111.111-2' })
    expect(res.status).toBe(400)
    expect(((await res.json()) as Row).mensaje).toBe(MSG.rut)
  })

  it('rejects over-long field', async () => {
    const res = await post('/api/reserva', { ...valid(), perro_nombre: 'ñ'.repeat(500) })
    expect(res.status).toBe(400)
    expect(((await res.json()) as Row).mensaje).toBe(MSG.largo)
    expect((await rows()).length).toBe(0)
  })

  it('honeypot pretends success', async () => {
    const res = await post('/api/reserva', { ...valid(), sitio_web: 'x' })
    expect(res.status).toBe(201)
    expect((await rows()).length).toBe(0)
  })

  it('form post without JSON gets HTML', async () => {
    const res = await post('/api/reserva', valid(), { accept: 'html' })
    expect(res.status).toBe(201)
    expect(res.headers.get('content-type')).toMatch(/^text\/html/)
    const html = await res.text()
    expect(html).toContain(MENSAJE_OK)
    expect(html).toContain('href="/#reservar"')
  })
})
