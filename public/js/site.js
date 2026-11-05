// Formularios: revisamos en el navegador y enviamos a la API. Sin JavaScript, el formulario se envía igual.
(() => {
  // Mismos textos que MSG en src/lib/fields.ts.
  const MSG = {
    falta: 'Falta completar este campo.',
    correo: 'Revisa el correo: parece incompleto.',
    rut: 'Revisa el RUT: el dígito verificador no calza.',
    vacunas: 'Para la guardería, las vacunas deben estar al día.',
    mayor_edad: 'Para reservar debes ser mayor de 18 años.',
    largo: 'Este campo es demasiado largo.',
    anios: 'Escribe un número de años entre 0 y 50.',
  }
  // Mismo algoritmo que src/lib/rut.ts.
  const rutOk = (v) => {
    const m = v.replace(/[.\s-]/g, '').toUpperCase().match(/^(\d{7,8})([\dK])$/)
    if (!m) return false
    let sum = 0, mul = 2
    for (const d of m[1].split('').reverse()) { sum += +d * mul; mul = mul === 7 ? 2 : mul + 1 }
    const r = 11 - (sum % 11)
    return (r === 11 ? '0' : r === 10 ? 'K' : String(r)) === m[2]
  }
  // Misma expresión que readEmail en src/lib/fields.ts.
  const correoOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

  function show(form, text, isErr) {
    const msg = form.querySelector('.form-msg')
    msg.textContent = text
    msg.className = 'form-msg ' + (isErr ? 'err' : 'ok')
  }
  function wire(form, check) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault()
      form.querySelectorAll('.bad').forEach((x) => x.classList.remove('bad'))
      const err = check(form)
      if (err) { show(form, err.text, true); err.el.classList.add('bad'); err.el.focus(); return }
      const button = form.querySelector('button[type=submit]')
      button.disabled = true
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: new URLSearchParams(new FormData(form)),
        })
        const data = await res.json()
        if (data.ok) { show(form, data.mensaje, false); form.classList.add('done'); return }
        show(form, data.mensaje, true)
        const field = data.campo && form.querySelector(`[name="${data.campo}"]`)
        if (field) { field.classList.add('bad'); field.focus() }
      } catch {
        show(form, 'No pudimos enviar el formulario. Revisa tu conexión e intenta de nuevo.', true)
      } finally {
        button.disabled = false
      }
    })
  }

  // Fecha local como YYYY-MM-DD (toISOString usaría UTC y podría saltar al día siguiente).
  const iso = (d) => [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-')

  // La reserva acepta desde hoy hasta 90 días más (el servidor revisa lo mismo con la hora de Chile).
  const fecha = document.querySelector('#f-reserva [name=fecha]')
  const hoy = new Date()
  fecha.min = iso(hoy)
  fecha.max = iso(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() + 90))

  wire(document.getElementById('f-reserva'), (f) => {
    for (const el of f.querySelectorAll('[required]')) if (!el.value.trim()) return { el, text: MSG.falta }
    if (!rutOk(f.rut.value)) return { el: f.rut, text: MSG.rut }
    if (!correoOk(f.correo.value)) return { el: f.correo, text: MSG.correo }
    if (f.retiro.value === 'si' && !f.direccion.value.trim()) return { el: f.direccion, text: MSG.falta }
    if (f.servicio.value === 'guarderia' && f.vacunas.value === 'no') return { el: f.vacunas, text: MSG.vacunas }
    if (!f.mayor_edad.checked) return { el: f.mayor_edad, text: MSG.mayor_edad }
    return null
  })
  // Mismas reglas que parsePostulacion en src/activities/postulacion.ts.
  wire(document.getElementById('f-postulacion'), (f) => {
    for (const el of f.querySelectorAll('[required]')) if (!el.value.trim()) return { el, text: MSG.falta }
    if (!correoOk(f.correo.value)) return { el: f.correo, text: MSG.correo }
    const anios = f.experiencia_anios.value.trim()
    if (!/^\d{1,2}$/.test(anios) || Number(anios) > 50) return { el: f.experiencia_anios, text: MSG.anios }
    if ([...f.experiencia.value.trim()].length > 1000) return { el: f.experiencia, text: MSG.largo }
    return null
  })
})();
