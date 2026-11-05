import { describe, expect, it } from 'vitest'
import { MSG, ValidationError, hoyEnChile, readFecha, readOpcion, readSiNo } from '../src/lib/fields'

const err = (fn: () => unknown) => { try { fn() } catch (e) { return e as ValidationError } throw new Error('no lanzó') }
// 2026-11-06T02:30Z es todavía 2026-11-05 en Chile (UTC-3).
const NOW = new Date('2026-11-06T02:30:00Z')

describe('fields', () => {
  it('hoyEnChile usa la hora de Santiago', () => expect(hoyEnChile(NOW)).toBe('2026-11-05'))
  it('readFecha acepta hoy en Chile', () => expect(readFecha({ f: '2026-11-05' }, 'f', NOW)).toBe('2026-11-05'))
  it('readFecha rechaza ayer', () => expect(err(() => readFecha({ f: '2026-11-04' }, 'f', NOW))).toMatchObject({ campo: 'f', message: MSG.fecha }))
  it('readFecha rechaza fechas que no existen', () => expect(err(() => readFecha({ f: '2026-11-31' }, 'f', NOW)).message).toBe(MSG.fecha))
  it('readFecha rechaza más de 90 días', () => {
    expect(readFecha({ f: '2027-02-03' }, 'f', NOW)).toBe('2027-02-03')
    expect(err(() => readFecha({ f: '2027-02-04' }, 'f', NOW)).message).toBe(MSG.fecha)
  })
  it('readFecha sin valor es falta', () => expect(err(() => readFecha({}, 'f', NOW)).message).toBe(MSG.falta))
  it('readSiNo', () => {
    expect(readSiNo({ x: 'si' }, 'x')).toBe(true)
    expect(readSiNo({ x: 'no' }, 'x')).toBe(false)
    expect(err(() => readSiNo({ x: 'quizas' }, 'x')).message).toBe(MSG.opcion)
  })
  it('readOpcion', () => {
    expect(readOpcion({ s: 'bano' }, 's', ['bano', 'guarderia'] as const)).toBe('bano')
    expect(err(() => readOpcion({ s: 'spa' }, 's', ['bano'] as const))).toMatchObject({ campo: 's', message: MSG.opcion })
  })
})
