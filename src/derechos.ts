import type { Env } from './env'
import { eliminarEnVeterinaria } from './partners/veterinaria'

// Derechos ARSOP: Lebrel es un agente de Privai. Privai recibe la solicitud en su centro de
// privacidad, verifica a la persona y deja una tarea en el bloque "Agente" del workflow. Cada minuto
// (cron, ver wrangler.jsonc) este agente consulta las tareas pendientes, toma las suyas por node_key,
// las ejecuta aquí y entrega el resultado. Privai nunca llama a Lebrel.
//   lebrel_recopilar (acceso, action collect): entrega todas las filas de la persona
//   lebrel_eliminar (supresión, action delete): avisa a la veterinaria si recibió datos y borra aquí
// Contrato: PRIVAI_API_URL/api/dsar/agent/* con "Authorization: Bearer <PRIVAI_AGENT_KEY>".
// Sin la clave, el agente no hace nada.
//
// La persona se identifica por su correo. La Analítica del sitio queda fuera: las visitas solo tienen
// el id de la cookie lb_vid y no hay cómo ligarlas a un correo.

export const CRON_PRIVAI = '* * * * *'
export const CLAVES = ['lebrel_recopilar', 'lebrel_eliminar']
// Privai permite 60 llamadas por minuto por agente; cada tarea usa 2 (pick-up y complete o fail).
const MAX_TAREAS = 25

type Row = Record<string, unknown>

export type Datos = {
  correo: string
  reservas: Row[]
}

export type Supresion = {
  borrados: { reservas: number }
  terceros: { veterinaria: string[] }
}

export type Tarea = { id: string; action: string; node_key: string; requester_email: string }
type Entrega =
  | { ruta: 'complete'; body: { result: { records: Row[] }; evidence?: Row } }
  | { ruta: 'fail'; body: { error: string } }

const CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Los formularios guardan el correo en minúsculas (ver readEmail).
export function normalizarCorreo(v: unknown): string | null {
  if (typeof v !== 'string') return null
  const correo = v.trim().toLowerCase()
  return correo.length <= 254 && CORREO.test(correo) ? correo : null
}

export async function recolectar(db: D1Database, correo: string): Promise<Datos> {
  const filas = await db
    .prepare('SELECT * FROM reservas WHERE correo = ? ORDER BY created_at')
    .bind(correo)
    .all<Row>()
  return { correo, reservas: filas.results }
}

// Primero avisa a la veterinaria y solo si confirma borra aquí. Si no confirma (falla, o falta su
// clave y no se le pudo avisar), la tarea queda fallida en Privai para revisión y puede reintentarse;
// no se borra nada a medias. La operación se puede repetir sin efectos raros.
export async function borrar(
  db: D1Database,
  env: Env,
  correo: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ ok: boolean } & Supresion> {
  const filas = await db
    .prepare('SELECT id, compartida_veterinaria_at FROM reservas WHERE correo = ?')
    .bind(correo)
    .all<Row>()

  const veterinaria = await Promise.all(
    filas.results
      .filter((s) => s.compartida_veterinaria_at)
      .map((s) => eliminarEnVeterinaria(String(s.id), env, fetchImpl)),
  )
  if (veterinaria.some((r) => r !== 'enviado')) {
    return { ok: false, borrados: { reservas: 0 }, terceros: { veterinaria } }
  }

  const res = await db.prepare('DELETE FROM reservas WHERE correo = ?').bind(correo).run()
  const borrados = { reservas: res.meta.changes }
  console.log(JSON.stringify({ evento: 'derechos.supresion', ...borrados }))
  return { ok: true, borrados, terceros: { veterinaria } }
}

export async function ejecutar(t: Tarea, env: Env, fetchImpl: typeof fetch = fetch): Promise<Entrega> {
  const correo = normalizarCorreo(t.requester_email)
  if (!correo) return { ruta: 'fail', body: { error: 'La solicitud no trae un correo válido.' } }

  if (t.action === 'collect') {
    const datos = await recolectar(env.DB, correo)
    // Privai copia los records tal cual al reporte del titular: uno por fila, con su tabla.
    const records = datos.reservas.map((fila) => ({ tabla: 'reservas', ...fila }))
    return { ruta: 'complete', body: { result: { records } } }
  }
  if (t.action === 'delete') {
    const res = await borrar(env.DB, env, correo, fetchImpl)
    if (!res.ok) {
      return { ruta: 'fail', body: { error: 'La veterinaria no confirmó el borrado; no se borró nada en Lebrel.' } }
    }
    return { ruta: 'complete', body: { result: { records: [] }, evidence: { borrados: res.borrados, terceros: res.terceros } } }
  }
  return { ruta: 'fail', body: { error: `Lebrel no ejecuta la acción "${t.action}".` } }
}

export async function atenderPrivai(env: Env, fetchImpl: typeof fetch = fetch): Promise<void> {
  if (!env.PRIVAI_AGENT_KEY) return
  const api = (method: 'GET' | 'POST', ruta: string, body?: unknown) =>
    fetchImpl(`${env.PRIVAI_API_URL}/api/dsar/agent${ruta}`, {
      method,
      headers: { authorization: `Bearer ${env.PRIVAI_AGENT_KEY}`, 'content-type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).catch(() => null)

  await api('POST', '/heartbeat')
  const res = await api('GET', '/tasks')
  if (!res?.ok) {
    console.log(JSON.stringify({ evento: 'privai.tareas.error', status: res?.status ?? null }))
    return
  }
  // Si Privai responde algo inesperado, no hay tareas que atender.
  const data = (await res.json().catch(() => null)) as { items?: unknown } | null
  const items = Array.isArray(data?.items) ? (data.items as Tarea[]) : []
  const nuestras = items.filter((t) => CLAVES.includes(t.node_key)).slice(0, MAX_TAREAS)

  for (const t of nuestras) {
    // 409: otra ejecución del agente ya la tomó.
    const tomada = await api('POST', `/tasks/${t.id}/pick-up`)
    if (!tomada?.ok) continue

    const entrega = await ejecutar(t, env, fetchImpl).catch(
      (err): Entrega => ({ ruta: 'fail', body: { error: String(err) } }),
    )
    const fin = await api('POST', `/tasks/${t.id}/${entrega.ruta}`, entrega.body)
    console.log(
      JSON.stringify({ evento: `privai.tarea.${entrega.ruta}`, tarea: t.id, node_key: t.node_key, status: fin?.status ?? null }),
    )
  }
}
