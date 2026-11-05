// RUT chileno: cuerpo de 7 u 8 dígitos y dígito verificador (módulo 11).

export function normalizeRut(input: string): string | null {
  const clean = input.replace(/[.\s-]/g, '').toUpperCase()
  const m = clean.match(/^(\d{7,8})([\dK])$/)
  return m ? `${m[1]}-${m[2]}` : null
}

function checkDigit(body: string): string {
  let sum = 0
  let weight = 2
  for (const digit of [...body].reverse()) {
    sum += Number(digit) * weight
    weight = weight === 7 ? 2 : weight + 1
  }
  const r = 11 - (sum % 11)
  return r === 11 ? '0' : r === 10 ? 'K' : String(r)
}

export function isValidRut(input: string): boolean {
  const rut = normalizeRut(input)
  if (!rut) return false
  const [body, dv] = rut.split('-')
  return checkDigit(body) === dv
}
