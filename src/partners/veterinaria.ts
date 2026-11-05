import type { ReservaRow } from '../activities/reserva'
import type { Env } from '../env'

// Clínica Veterinaria Los Aromos SpA confirma que las vacunas del perro estén
// al día antes de la guardería. Le enviamos solo lo necesario: el correo y la
// dirección del cliente no salen de aquí.
const DEFAULT_URL = 'https://api.veterinaria-los-aromos.example/v1/confirmaciones-vacunas'

type Resultado = 'enviado' | 'omitido' | 'error'

// Solo la guardería exige vacunas al día, así que solo ella se comparte.
export function debeCompartir(r: ReservaRow): boolean {
  return r.servicio === 'guarderia'
}

export async function compartirConVeterinaria(
  r: ReservaRow,
  env: Env,
  fetchImpl: typeof fetch = fetch,
): Promise<Resultado> {
  if (!env.VETERINARIA_API_KEY) {
    console.log(JSON.stringify({ evento: 'veterinaria.omitido', reserva: r.id }))
    return 'omitido'
  }
  const res = await fetchImpl(env.VETERINARIA_API_URL ?? DEFAULT_URL, {
    method: 'POST',
    headers: { authorization: `Bearer ${env.VETERINARIA_API_KEY}`, 'content-type': 'application/json' },
    body: JSON.stringify({
      referencia: r.id,
      cliente: { nombre: r.nombre, rut: r.rut, telefono: r.telefono },
      perro: { nombre: r.perro_nombre, raza: r.perro_raza },
      fecha: r.fecha,
      vacunas_al_dia: r.vacunas_al_dia === 1,
    }),
  }).catch(() => null)
  const resultado = res?.ok ? 'enviado' : 'error'
  console.log(JSON.stringify({ evento: `veterinaria.${resultado}`, reserva: r.id, status: res?.status ?? null }))
  return resultado
}

// Si la persona pide borrar sus datos, la veterinaria también debe borrar la confirmación que le enviamos.
export async function eliminarEnVeterinaria(
  referencia: string,
  env: Env,
  fetchImpl: typeof fetch = fetch,
): Promise<Resultado> {
  if (!env.VETERINARIA_API_KEY) {
    console.log(JSON.stringify({ evento: 'veterinaria.supresion.omitida', reserva: referencia }))
    return 'omitido'
  }
  const res = await fetchImpl(`${env.VETERINARIA_API_URL ?? DEFAULT_URL}/${encodeURIComponent(referencia)}`, {
    method: 'DELETE',
    headers: { authorization: `Bearer ${env.VETERINARIA_API_KEY}` },
  }).catch(() => null)
  const resultado = res?.ok || res?.status === 404 ? 'enviado' : 'error'
  console.log(JSON.stringify({ evento: `veterinaria.supresion.${resultado}`, reserva: referencia, status: res?.status ?? null }))
  return resultado
}
