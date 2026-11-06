// Campañas. Cookie no esencial (lb_campana, 90 días), categoría "marketing".
// Si el visitante llega desde un enlace de campaña (?utm_source=…&utm_campaign=…), guarda de qué
// campaña vino para medir qué publicidad funciona. Solo se guarda en el navegador; no se envía a terceros.
(() => {
  const NAME = 'lb_campana'
  const MAX_AGE = 7776000 // 90 días
  const params = new URLSearchParams(location.search)
  const fuente = params.get('utm_source')
  if (!fuente) return
  const campana = params.get('utm_campaign') || ''
  const valor = encodeURIComponent(`${fuente.slice(0, 40)}|${campana.slice(0, 60)}`)
  const secure = location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${NAME}=${valor}; Max-Age=${MAX_AGE}; Path=/; SameSite=Lax${secure}`
})()
