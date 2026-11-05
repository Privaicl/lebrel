import { describe, expect, it } from 'vitest'
import type { ReservaRow } from '../src/activities/reserva'
import type { Env } from '../src/env'
import { compartirConVeterinaria, debeCompartir, eliminarEnVeterinaria } from '../src/partners/veterinaria'

type Call = { url: string; init: RequestInit }
function stubFetch(status: number) {
  const calls: Call[] = []
  const impl = (async (url: string, init: RequestInit) => {
    calls.push({ url: String(url), init })
    return new Response(null, { status })
  }) as unknown as typeof fetch
  return { calls, impl }
}

const baseEnv = { ALLOWED_ORIGINS: '' } as Env
const URL_VET = 'https://api.veterinaria-los-aromos.example/v1/confirmaciones-vacunas'

const reserva: ReservaRow = {
  id: 'abc',
  nombre: 'José Peña',
  rut: '12345678-5',
  correo: 'jose@correo.example',
  telefono: '+56911111111',
  perro_nombre: 'Canela',
  perro_raza: 'Galgo',
  servicio: 'guarderia',
  fecha: '2026-11-20',
  vacunas_al_dia: 1,
  retiro: 1,
  direccion: 'Calle Los Aromos 0',
  declara_mayor_edad: 1,
  created_at: '2026-11-05T00:00:00.000Z',
}

describe('veterinaria', () => {
  it('skips without key', async () => {
    const f = stubFetch(200)
    expect(await compartirConVeterinaria(reserva, baseEnv, f.impl)).toBe('omitido')
    expect(f.calls.length).toBe(0)
  })

  it('sends only what the vet needs', async () => {
    const f = stubFetch(200)
    const env = { ...baseEnv, VETERINARIA_API_KEY: 'k' }
    expect(await compartirConVeterinaria(reserva, env, f.impl)).toBe('enviado')
    expect(f.calls.length).toBe(1)
    expect(f.calls[0].url).toBe(URL_VET)
    expect(f.calls[0].init.method).toBe('POST')
    expect(new Headers(f.calls[0].init.headers).get('authorization')).toBe('Bearer k')
    const body = JSON.parse(String(f.calls[0].init.body))
    expect(body).toEqual({
      referencia: 'abc',
      cliente: { nombre: 'José Peña', rut: '12345678-5', telefono: '+56911111111' },
      perro: { nombre: 'Canela', raza: 'Galgo' },
      fecha: '2026-11-20',
      vacunas_al_dia: true,
    })
    const json = JSON.stringify(body)
    expect(json).not.toContain('correo')
    expect(json).not.toContain('direccion')
  })

  it('uses VETERINARIA_API_URL when set', async () => {
    const f = stubFetch(200)
    const env = { ...baseEnv, VETERINARIA_API_KEY: 'k', VETERINARIA_API_URL: 'https://vet.test/x' }
    await compartirConVeterinaria(reserva, env, f.impl)
    expect(f.calls[0].url).toBe('https://vet.test/x')
  })

  it('error on 500 or network failure', async () => {
    const env = { ...baseEnv, VETERINARIA_API_KEY: 'k' }
    expect(await compartirConVeterinaria(reserva, env, stubFetch(500).impl)).toBe('error')
    const boom = (async () => {
      throw new Error('red caída')
    }) as unknown as typeof fetch
    expect(await compartirConVeterinaria(reserva, env, boom)).toBe('error')
  })

  it('delete calls DELETE /<referencia>', async () => {
    const env = { ...baseEnv, VETERINARIA_API_KEY: 'k' }
    const f = stubFetch(200)
    expect(await eliminarEnVeterinaria('abc', env, f.impl)).toBe('enviado')
    expect(f.calls[0].url).toBe(`${URL_VET}/abc`)
    expect(f.calls[0].init.method).toBe('DELETE')
    expect(await eliminarEnVeterinaria('abc', env, stubFetch(404).impl)).toBe('enviado')
    expect(await eliminarEnVeterinaria('abc', env, stubFetch(500).impl)).toBe('error')
    expect(await eliminarEnVeterinaria('abc', baseEnv, f.impl)).toBe('omitido')
  })

  it('only guardería is shared', () => {
    expect(debeCompartir({ ...reserva, servicio: 'guarderia' })).toBe(true)
    expect(debeCompartir({ ...reserva, servicio: 'bano' })).toBe(false)
    expect(debeCompartir({ ...reserva, servicio: 'bano_corte' })).toBe(false)
  })
})
