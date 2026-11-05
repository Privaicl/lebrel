import { describe, expect, it } from 'vitest'
import { isValidRut, normalizeRut } from '../src/lib/rut'

describe('RUT', () => {
  it('accepts valid RUTs', () => {
    for (const rut of ['11.111.111-1', '12.345.678-5', '1.000.005-K']) expect(isValidRut(rut)).toBe(true)
  })

  it('rejects wrong check digit', () => {
    for (const rut of ['11.111.111-2', '12.345.678-K']) expect(isValidRut(rut)).toBe(false)
  })

  it('normalizes loose RUT input', () => {
    expect(normalizeRut(' 12.345.678-5 ')).toBe('12345678-5')
    expect(normalizeRut('123456785')).toBe('12345678-5')
    expect(normalizeRut('12345678-5')).toBe('12345678-5')
    expect(normalizeRut('1.000.005-k')).toBe('1000005-K')
    expect(normalizeRut('abc')).toBeNull()
  })
})
