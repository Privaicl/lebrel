// Preferencias del visitante. Cookie no esencial (lb_pref, 12 meses), categoría "functional".
// Recuerda el último servicio elegido en la reserva para dejarlo preseleccionado en la próxima visita.
// Solo se guarda en el navegador; no se envía a nuestros servidores.
(() => {
  const NAME = 'lb_pref'
  const MAX_AGE = 31536000 // 365 días
  const secure = location.protocol === 'https:' ? '; Secure' : ''
  const guardar = (valor) => {
    document.cookie = `${NAME}=${encodeURIComponent(valor)}; Max-Age=${MAX_AGE}; Path=/; SameSite=Lax${secure}`
  }
  const found = document.cookie.split('; ').find((c) => c.startsWith(`${NAME}=`))
  const guardado = found ? decodeURIComponent(found.slice(NAME.length + 1)) : ''
  if (!found) guardar('ninguno')

  const select = document.querySelector('#f-reserva select[name="servicio"]')
  if (!select) return
  if (guardado && !select.value && [...select.options].some((o) => o.value === guardado)) select.value = guardado
  select.addEventListener('change', () => {
    if (select.value) guardar(select.value)
  })
})()
