// Analítica propia del sitio. Cookie no esencial (lb_vid, 13 meses).
(() => {
  const NAME = 'lb_vid'
  const MAX_AGE = 34128000 // 395 días
  const found = document.cookie.split('; ').find((c) => c.startsWith(`${NAME}=`))
  let vid = found ? found.slice(NAME.length + 1) : ''
  if (!vid) {
    vid = crypto.randomUUID()
    const secure = location.protocol === 'https:' ? '; Secure' : ''
    document.cookie = `${NAME}=${vid}; Max-Age=${MAX_AGE}; Path=/; SameSite=Lax${secure}`
  }
  navigator.sendBeacon(
    '/api/collect',
    JSON.stringify({ vid, ruta: location.pathname + location.hash, referente: document.referrer || null }),
  )
})()
