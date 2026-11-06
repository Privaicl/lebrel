// Campañas. Cookie no esencial (lb_campana, 90 días), categoría "marketing".
// Guarda por qué campaña llegó el visitante (?utm_source=…&utm_campaign=…), o "directo" si no vino de
// una campaña, para medir qué publicidad funciona. Solo se guarda en el navegador; no se envía a terceros.
(() => {
  const NAME = 'lb_campana'
  const MAX_AGE = 7776000 // 90 días
  const params = new URLSearchParams(location.search)
  const fuente = params.get('utm_source')
  const yaEsta = document.cookie.split('; ').some((c) => c.startsWith(`${NAME}=`))
  if (!fuente && yaEsta) return
  const valor = fuente
    ? encodeURIComponent(`${fuente.slice(0, 40)}|${(params.get('utm_campaign') || '').slice(0, 60)}`)
    : 'directo'
  const secure = location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${NAME}=${valor}; Max-Age=${MAX_AGE}; Path=/; SameSite=Lax${secure}`
})()
