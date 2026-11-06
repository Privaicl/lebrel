import { env } from 'cloudflare:test'
import { beforeEach, describe, expect, it } from 'vitest'
import { type Tarea, atenderPrivai, borrar, ejecutar, normalizarCorreo, recolectar } from '../src/derechos'
import type { Env } from '../src/env'

const count = async () =>
  (await env.DB.prepare('SELECT count(*) AS n FROM reservas').first<{ n: number }>())?.n

async function insertReserva(id: string, correo: string, compartida: string | null = null) {
  await env.DB.prepare(
    `INSERT INTO reservas
       (id, nombre, rut, correo, telefono, perro_nombre, perro_raza, servicio, fecha, vacunas_al_dia, retiro,
        direccion, declara_mayor_edad, compartida_veterinaria_at, created_at)
     VALUES (?, 'José Peña', '12345678-5', ?, '+56911111111', 'Kobold', 'Borzoi', 'guarderia', '2026-11-20', 1, 1,
        'Calle Los Aromos 0', 1, ?, '2026-10-25T00:00:00.000Z')`,
  )
    .bind(id, correo, compartida)
    .run()
}

async function insertPostulacion(id: string, correo: string) {
  await env.DB.prepare(
    `INSERT INTO postulaciones (id, nombre, correo, telefono, comuna, experiencia_anios, experiencia, created_at)
     VALUES (?, 'José Peña', ?, '+56911111111', 'Ñuñoa', 4, 'Peluquería canina', '2026-10-26T00:00:00.000Z')`,
  )
    .bind(id, correo)
    .run()
}
const countPost = async () =>
  (await env.DB.prepare('SELECT count(*) AS n FROM postulaciones').first<{ n: number }>())?.n

function stubFetch(status: number) {
  const calls: { url: string; method?: string }[] = []
  const impl = (async (url: string, init: RequestInit) => {
    calls.push({ url: String(url), method: init.method })
    return new Response(null, { status })
  }) as unknown as typeof fetch
  return { calls, impl }
}

// Simula la API de agentes de Privai: entrega `tareas` y anota cada llamada con su body.
function stubPrivai(tareas: Partial<Tarea>[], pickUp = 200) {
  const calls: { method: string; path: string; auth: string | null; body: unknown }[] = []
  const impl = (async (url: string, init: RequestInit) => {
    const path = new URL(url).pathname.replace('/api/dsar/agent', '')
    calls.push({
      method: String(init.method),
      path,
      auth: new Headers(init.headers).get('authorization'),
      body: init.body ? JSON.parse(String(init.body)) : undefined,
    })
    if (path === '/tasks') return Response.json({ items: tareas })
    if (path.endsWith('/pick-up')) return new Response(null, { status: pickUp })
    return new Response(null, { status: 200 })
  }) as unknown as typeof fetch
  return { calls, impl }
}

const conAgente = { ...env, PRIVAI_API_URL: 'https://api.privai.test', PRIVAI_AGENT_KEY: 'agent_k' } as Env
const conVeterinaria = { ...env, VETERINARIA_API_KEY: 'c' } as Env
const tarea = (t: Partial<Tarea>): Tarea => ({
  id: 't1',
  action: 'collect',
  node_key: 'lebrel_recopilar',
  requester_email: 'jose@correo.example',
  ...t,
})

beforeEach(async () => {
  await env.DB.exec('DELETE FROM reservas; DELETE FROM postulaciones')
})

describe('derechos: acceso', () => {
  it('returns every stored row for the email, as stored', async () => {
    await insertReserva('s1', 'jose@correo.example', '2026-10-25T00:01:00.000Z')
    await insertReserva('otro', 'otra@correo.example')

    expect(await recolectar(env.DB, 'jose@correo.example')).toEqual({
      correo: 'jose@correo.example',
      postulaciones: [],
      reservas: [
        {
          id: 's1',
          nombre: 'José Peña',
          rut: '12345678-5',
          correo: 'jose@correo.example',
          telefono: '+56911111111',
          perro_nombre: 'Kobold',
          perro_raza: 'Borzoi',
          servicio: 'guarderia',
          fecha: '2026-11-20',
          vacunas_al_dia: 1,
          retiro: 1,
          direccion: 'Calle Los Aromos 0',
          declara_mayor_edad: 1,
          compartida_veterinaria_at: '2026-10-25T00:01:00.000Z',
          created_at: '2026-10-25T00:00:00.000Z',
        },
      ],
    })
  })

  it('a collect task hands Privai one record per row, tagged with its table', async () => {
    await insertReserva('s1', 'jose@correo.example')
    const entrega = await ejecutar(tarea({ requester_email: ' JOSE@correo.example' }), env as Env)
    expect(entrega.ruta).toBe('complete')
    const { records } = (entrega.body as { result: { records: Record<string, unknown>[] } }).result
    expect(records).toHaveLength(1)
    expect(records[0]).toMatchObject({ tabla: 'reservas', id: 's1', rut: '12345678-5' })
  })

  it('access returns postulaciones too', async () => {
    await insertReserva('s1', 'jose@correo.example')
    await insertPostulacion('p1', 'jose@correo.example')
    await insertPostulacion('p2', 'otra@correo.example')
    const datos = await recolectar(env.DB, 'jose@correo.example')
    expect(datos.postulaciones).toHaveLength(1)
    expect(datos.postulaciones[0]).toMatchObject({ id: 'p1', comuna: 'Ñuñoa', experiencia_anios: 4 })

    const entrega = await ejecutar(tarea({}), env as Env)
    const { records } = (entrega.body as { result: { records: Record<string, unknown>[] } }).result
    expect(records.map((r) => `${r.tabla}:${r.id}`)).toEqual(['reservas:s1', 'postulaciones:p1'])
  })

  it('normalizes the email the way the forms store it', () => {
    expect(normalizarCorreo('  A@B.cl ')).toBe('a@b.cl')
    expect(normalizarCorreo('nope')).toBeNull()
  })
})

describe('derechos: supresión', () => {
  it('deletes every row for the email and leaves other people alone', async () => {
    await insertReserva('s1', 'jose@correo.example')
    await insertReserva('s2', 'jose@correo.example')
    await insertReserva('otro', 'otra@correo.example')

    const entrega = await ejecutar(tarea({ action: 'delete', node_key: 'lebrel_eliminar' }), env as Env)
    expect(entrega).toEqual({
      ruta: 'complete',
      body: { result: { records: [] }, evidence: { borrados: { reservas: 2, postulaciones: 0 }, terceros: { veterinaria: [] } } },
    })
    expect(await count()).toBe(1)
  })

  it('delete removes postulaciones, with no third party', async () => {
    await insertPostulacion('p1', 'jose@correo.example')
    await insertPostulacion('p2', 'otra@correo.example')
    const f = stubFetch(204)
    const res = await borrar(env.DB, conVeterinaria, 'jose@correo.example', f.impl)
    expect(res).toEqual({ ok: true, borrados: { reservas: 0, postulaciones: 1 }, terceros: { veterinaria: [] } })
    expect(f.calls).toHaveLength(0)
    expect(await countPost()).toBe(1)
  })

  it('is safe to repeat', async () => {
    await insertReserva('s1', 'jose@correo.example')
    await borrar(env.DB, env as Env, 'jose@correo.example')
    expect((await borrar(env.DB, env as Env, 'jose@correo.example')).borrados).toEqual({ reservas: 0, postulaciones: 0 })
  })

  it('tells the vet only about the bookings it received', async () => {
    await insertReserva('s1', 'jose@correo.example', '2026-10-25T00:01:00.000Z')
    await insertReserva('s2', 'jose@correo.example')
    const f = stubFetch(204)

    const res = await borrar(env.DB, conVeterinaria, 'jose@correo.example', f.impl)
    expect(res).toEqual({ ok: true, borrados: { reservas: 2, postulaciones: 0 }, terceros: { veterinaria: ['enviado'] } })
    expect(f.calls).toEqual([
      { url: 'https://api.veterinaria-los-aromos.example/v1/confirmaciones-vacunas/s1', method: 'DELETE' },
    ])
  })

  it('a booking already gone from the vet counts as deleted', async () => {
    await insertReserva('s1', 'jose@correo.example', '2026-10-25T00:01:00.000Z')
    expect((await borrar(env.DB, conVeterinaria, 'jose@correo.example', stubFetch(404).impl)).ok).toBe(true)
    expect(await count()).toBe(0)
  })

  it('delete skips the vet for bookings never shared', async () => {
    await insertReserva('s1', 'jose@correo.example', null)
    const f = stubFetch(204)

    const res = await borrar(env.DB, conVeterinaria, 'jose@correo.example', f.impl)
    expect(res.ok).toBe(true)
    expect(res.borrados.reservas).toBe(1)
    expect(f.calls).toHaveLength(0)
  })

  it('keeps everything and fails the task when the vet fails, so it goes to review', async () => {
    await insertReserva('s1', 'jose@correo.example', '2026-10-25T00:01:00.000Z')
    const entrega = await ejecutar(
      tarea({ action: 'delete', node_key: 'lebrel_eliminar' }),
      conVeterinaria,
      stubFetch(500).impl,
    )
    expect(entrega.ruta).toBe('fail')
    expect((entrega.body as { error: string }).error).toBe('La veterinaria no confirmó el borrado; no se borró nada en Lebrel.')
    expect(await count()).toBe(1)
  })
  it('fails without deleting when a shared booking cannot be deleted at the vet because its key is missing', async () => {
    await insertReserva('s1', 'jose@correo.example', '2026-10-25T00:01:00.000Z')
    await insertReserva('s2', 'jose@correo.example')
    const f = stubFetch(204)

    const res = await borrar(env.DB, { ...env, VETERINARIA_API_KEY: undefined } as Env, 'jose@correo.example', f.impl)
    expect(res).toEqual({ ok: false, borrados: { reservas: 0, postulaciones: 0 }, terceros: { veterinaria: ['omitido'] } })
    expect(f.calls).toHaveLength(0)
    expect(await count()).toBe(2)
  })
})

describe('agente de Privai', () => {
  it('does nothing without the agent key', async () => {
    const p = stubPrivai([tarea({})])
    await atenderPrivai({ ...conAgente, PRIVAI_AGENT_KEY: undefined }, p.impl)
    expect(p.calls).toEqual([])
  })

  it('heartbeats, polls, takes its own task and completes it', async () => {
    await insertReserva('s1', 'jose@correo.example')
    const p = stubPrivai([tarea({ id: 'mia' }), tarea({ id: 'ajena', node_key: 'crm_recopilar' })])

    await atenderPrivai(conAgente, p.impl)
    expect(p.calls.map((c) => `${c.method} ${c.path}`)).toEqual([
      'POST /heartbeat',
      'GET /tasks',
      'POST /tasks/mia/pick-up',
      'POST /tasks/mia/complete',
    ])
    expect(p.calls.every((c) => c.auth === 'Bearer agent_k')).toBe(true)
    const complete = p.calls[3].body as { result: { records: { id: string }[] } }
    expect(complete.result.records.map((r) => r.id)).toEqual(['s1'])
  })

  it('skips a task another run already took', async () => {
    const p = stubPrivai([tarea({ id: 'mia' })], 409)
    await atenderPrivai(conAgente, p.impl)
    expect(p.calls.map((c) => c.path)).toEqual(['/heartbeat', '/tasks', '/tasks/mia/pick-up'])
  })

  it('fails tasks it cannot do instead of letting them expire', async () => {
    const p = stubPrivai([
      tarea({ id: 'rect', action: 'rectify' }),
      tarea({ id: 'sin-correo', requester_email: 'nope' }),
    ])
    await atenderPrivai(conAgente, p.impl)
    const fails = p.calls.filter((c) => c.path.endsWith('/fail'))
    expect(fails.map((c) => c.path)).toEqual(['/tasks/rect/fail', '/tasks/sin-correo/fail'])
    expect((fails[0].body as { error: string }).error).toMatch(/rectify/)
  })

  it('stops quietly when Privai answers without a task list', async () => {
    const raro = (async (url: string) =>
      new URL(url).pathname.endsWith('/tasks') ? Response.json({ error: 'x' }) : new Response(null, { status: 200 })) as unknown as typeof fetch
    await expect(atenderPrivai(conAgente, raro)).resolves.toBeUndefined()
  })

  it('stops quietly when Privai is down', async () => {
    const down = (async () => new Response(null, { status: 503 })) as unknown as typeof fetch
    await expect(atenderPrivai(conAgente, down)).resolves.toBeUndefined()
  })
})
