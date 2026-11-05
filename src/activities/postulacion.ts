import type { Context } from 'hono'
import type { Env } from '../env'
import { ValidationError, readEmail, readPhone, readText } from '../lib/fields'
import { fail, ok } from '../lib/respond'

// Postulación a peluquero/a ("Trabaja con nosotros"). Se guarda para evaluar al postulante;
// no se comparte con nadie.

export type PostulacionRow = {
  id: string
  nombre: string
  correo: string
  telefono: string
  comuna: string
  experiencia_anios: number
  experiencia: string
  created_at: string
}

export const MENSAJE_OK_POSTULACION = 'Recibimos tu postulación. Si tu perfil calza, te contactaremos.'
export const MSG_ANIOS = 'Escribe un número de años entre 0 y 50.'

// Solo enteros 0–50 escritos con dígitos ('2.5', '-1' o 'abc' no pasan).
function readAnios(body: Record<string, unknown>, campo: string): number {
  const v = readText(body, campo, 10)
  if (!/^\d{1,2}$/.test(v) || Number(v) > 50) throw new ValidationError(campo, MSG_ANIOS)
  return Number(v)
}

export function parsePostulacion(body: Record<string, unknown>, now: Date): PostulacionRow {
  return {
    id: crypto.randomUUID(),
    nombre: readText(body, 'nombre', 120),
    correo: readEmail(body, 'correo'),
    telefono: readPhone(body, 'telefono'),
    comuna: readText(body, 'comuna', 60),
    experiencia_anios: readAnios(body, 'experiencia_anios'),
    experiencia: readText(body, 'experiencia', 1000),
    created_at: now.toISOString(),
  }
}

export async function handlePostulacion(c: Context<{ Bindings: Env }>): Promise<Response> {
  const body = await c.req.parseBody()
  if (body.sitio_web) return ok(c, MENSAJE_OK_POSTULACION, 'trabaja')

  let row: PostulacionRow
  try {
    row = parsePostulacion(body, new Date())
  } catch (err) {
    if (err instanceof ValidationError) return fail(c, err, 'trabaja')
    throw err
  }

  await c.env.DB.prepare(
    `INSERT INTO postulaciones
       (id, nombre, correo, telefono, comuna, experiencia_anios, experiencia, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(row.id, row.nombre, row.correo, row.telefono, row.comuna, row.experiencia_anios, row.experiencia, row.created_at)
    .run()

  return ok(c, MENSAJE_OK_POSTULACION, 'trabaja')
}
