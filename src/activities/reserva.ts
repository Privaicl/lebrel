import type { Context } from 'hono'
import type { Env } from '../env'
import {
  MSG,
  ValidationError,
  readEmail,
  readFecha,
  readOpcion,
  readPhone,
  readSiNo,
  readText,
} from '../lib/fields'
import { fail, ok } from '../lib/respond'
import { isValidRut, normalizeRut } from '../lib/rut'
import { compartirConVeterinaria, debeCompartir } from '../partners/veterinaria'

// Reserva de hora de peluquería o guardería. Se guarda para agendar el servicio;
// en guardería, la veterinaria asociada confirma las vacunas.

export type Servicio = 'bano' | 'bano_corte' | 'guarderia'
export const SERVICIOS: readonly Servicio[] = ['bano', 'bano_corte', 'guarderia']

export type ReservaRow = {
  id: string
  nombre: string
  rut: string
  correo: string
  telefono: string
  perro_nombre: string
  perro_raza: string
  servicio: Servicio
  fecha: string
  vacunas_al_dia: 0 | 1
  retiro: 0 | 1
  direccion: string | null
  declara_mayor_edad: 1
  created_at: string
}

export const MENSAJE_OK = 'Recibimos tu reserva. Te contactaremos para confirmar la hora.'

export function parseReserva(body: Record<string, unknown>, now: Date): ReservaRow {
  const nombre = readText(body, 'nombre', 120)
  const rutRaw = readText(body, 'rut', 20)
  if (!isValidRut(rutRaw)) throw new ValidationError('rut', MSG.rut)
  const correo = readEmail(body, 'correo')
  const telefono = readPhone(body, 'telefono')
  const perro_nombre = readText(body, 'perro_nombre', 60)
  const perro_raza = readText(body, 'perro_raza', 60)
  const servicio = readOpcion(body, 'servicio', SERVICIOS)
  const fecha = readFecha(body, 'fecha', now)
  const vacunas = readSiNo(body, 'vacunas')
  if (servicio === 'guarderia' && !vacunas) throw new ValidationError('vacunas', MSG.vacunas)
  const retiro = readSiNo(body, 'retiro')
  // La dirección solo se lee si pidió retiro; si no, se descarta lo que venga.
  const direccion = retiro ? readText(body, 'direccion', 200) : null
  if (body.mayor_edad !== 'si') throw new ValidationError('mayor_edad', MSG.mayor_edad)
  return {
    id: crypto.randomUUID(),
    nombre,
    rut: normalizeRut(rutRaw) as string,
    correo,
    telefono,
    perro_nombre,
    perro_raza,
    servicio,
    fecha,
    vacunas_al_dia: vacunas ? 1 : 0,
    retiro: retiro ? 1 : 0,
    direccion,
    declara_mayor_edad: 1,
    created_at: now.toISOString(),
  }
}

export async function markShared(db: D1Database, id: string): Promise<void> {
  await db
    .prepare('UPDATE reservas SET compartida_veterinaria_at = ? WHERE id = ?')
    .bind(new Date().toISOString(), id)
    .run()
}

export async function handleReserva(c: Context<{ Bindings: Env }>): Promise<Response> {
  const body = await c.req.parseBody()
  if (body.sitio_web) return ok(c, MENSAJE_OK, 'reservar')

  let row: ReservaRow
  try {
    row = parseReserva(body, new Date())
  } catch (err) {
    if (err instanceof ValidationError) return fail(c, err, 'reservar')
    throw err
  }

  await c.env.DB.prepare(
    `INSERT INTO reservas
       (id, nombre, rut, correo, telefono, perro_nombre, perro_raza, servicio, fecha,
        vacunas_al_dia, retiro, direccion, declara_mayor_edad, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      row.id,
      row.nombre,
      row.rut,
      row.correo,
      row.telefono,
      row.perro_nombre,
      row.perro_raza,
      row.servicio,
      row.fecha,
      row.vacunas_al_dia,
      row.retiro,
      row.direccion,
      row.declara_mayor_edad,
      row.created_at,
    )
    .run()

  if (debeCompartir(row)) {
    c.executionCtx.waitUntil(
      compartirConVeterinaria(row, c.env).then((r) => (r === 'enviado' ? markShared(c.env.DB, row.id) : undefined)),
    )
  }

  return ok(c, MENSAJE_OK, 'reservar')
}
