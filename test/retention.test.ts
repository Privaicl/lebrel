import { env } from 'cloudflare:test'
import { beforeEach, describe, expect, it } from 'vitest'
import { cutoff, purgeExpired } from '../src/retention'

const NOW = new Date('2026-11-05T07:00:00Z')

async function insertReserva(id: string, created: string) {
  await env.DB.prepare(
    `INSERT INTO reservas (id, nombre, rut, correo, telefono, perro_nombre, perro_raza, servicio, fecha,
       vacunas_al_dia, retiro, direccion, declara_mayor_edad, created_at)
     VALUES (?, 'N', '12345678-5', 'a@correo.example', '+56911111111', 'Bruno', 'Quiltro', 'bano', '2026-12-01',
       1, 0, NULL, 1, ?)`,
  )
    .bind(id, created)
    .run()
}
async function insertVisita(vid: string, created: string) {
  await env.DB.prepare('INSERT INTO visitas (visitor_id, ruta, created_at) VALUES (?, ?, ?)').bind(vid, '/', created).run()
}
const ids = async (sql: string) => (await env.DB.prepare(sql).all<{ k: string }>()).results.map((r) => r.k)

beforeEach(async () => {
  await env.DB.exec('DELETE FROM reservas; DELETE FROM visitas;')
})

describe('retention', () => {
  it('cutoff subtracts calendar months', () => {
    expect(cutoff(NOW, 24)).toBe('2024-11-05T07:00:00.000Z')
  })

  it('purges only expired rows', async () => {
    await insertReserva('old', '2024-11-04T00:00:00.000Z')
    await insertReserva('new', '2024-11-06T00:00:00.000Z')
    await insertVisita('old', '2025-10-04T00:00:00.000Z')
    await insertVisita('new', '2025-10-06T00:00:00.000Z')
    expect(await purgeExpired(env.DB, NOW)).toEqual({ reservas: 1, visitas: 1 })
    expect(await ids('SELECT id AS k FROM reservas')).toEqual(['new'])
    expect(await ids('SELECT visitor_id AS k FROM visitas')).toEqual(['new'])
  })

  it('empty tables are fine', async () => {
    expect(await purgeExpired(env.DB, NOW)).toEqual({ reservas: 0, visitas: 0 })
  })
})
