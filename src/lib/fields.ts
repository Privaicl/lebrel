// Lectura y validación de campos de formulario. Los mensajes son los que ve el visitante.

export const MSG = {
  falta: 'Falta completar este campo.',
  largo: 'Este campo es demasiado largo.',
  correo: 'Revisa el correo: parece incompleto.',
  telefono: 'Revisa el teléfono: debe tener entre 8 y 15 dígitos.',
  rut: 'Revisa el RUT: el dígito verificador no calza.',
  opcion: 'Elige una de las opciones.',
  fecha: 'Elige una fecha entre hoy y los próximos 90 días.',
  vacunas: 'Para la guardería, las vacunas deben estar al día.',
  mayor_edad: 'Para reservar debes ser mayor de 18 años.',
} as const

export class ValidationError extends Error {
  constructor(
    readonly campo: string,
    message: string,
  ) {
    super(message)
  }
}

type Body = Record<string, unknown>

export function readText(body: Body, campo: string, max: number): string {
  const raw = body[campo]
  const value = typeof raw === 'string' ? raw.trim() : ''
  if (!value) throw new ValidationError(campo, MSG.falta)
  if ([...value].length > max) throw new ValidationError(campo, MSG.largo)
  return value
}

export function readEmail(body: Body, campo: string): string {
  const value = readText(body, campo, 254).toLowerCase()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) throw new ValidationError(campo, MSG.correo)
  return value
}

export function readPhone(body: Body, campo: string): string {
  const value = readText(body, campo, 30).replace(/[^\d+]/g, '')
  const digits = value.replace(/\D/g, '').length
  if (digits < 8 || digits > 15) throw new ValidationError(campo, MSG.telefono)
  return value
}

export function readOpcion<T extends string>(body: Body, campo: string, opciones: readonly T[]): T {
  const value = readText(body, campo, 50)
  if (!(opciones as readonly string[]).includes(value)) throw new ValidationError(campo, MSG.opcion)
  return value as T
}

export function readSiNo(body: Body, campo: string): boolean {
  return readOpcion(body, campo, ['si', 'no'] as const) === 'si'
}

/** Fecha de hoy en Chile, como YYYY-MM-DD. */
export function hoyEnChile(now: Date): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Santiago' }).format(now)
}

/** Fecha YYYY-MM-DD real, entre hoy (hora de Chile) y hoy + maxDias. */
export function readFecha(body: Body, campo: string, now: Date, maxDias = 90): string {
  const v = readText(body, campo, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new ValidationError(campo, MSG.fecha)
  const d = new Date(`${v}T12:00:00Z`)
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== v) throw new ValidationError(campo, MSG.fecha)
  const hoy = hoyEnChile(now)
  const limite = new Date(`${hoy}T12:00:00Z`)
  limite.setUTCDate(limite.getUTCDate() + maxDias)
  if (v < hoy || v > limite.toISOString().slice(0, 10)) throw new ValidationError(campo, MSG.fecha)
  return v
}
