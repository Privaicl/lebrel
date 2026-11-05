// Cookie esencial de sesión: solo sirve para comprobar que un formulario
// se envió desde nuestra propia página. No identifica a nadie ni se guarda.
export const SESSION_COOKIE = 'lb_session'

export function hasSession(req: Request): boolean {
  const cookie = req.headers.get('cookie') ?? ''
  return cookie.split(';').some((part) => part.trim().startsWith(`${SESSION_COOKIE}=`))
}

export function ensureSession(req: Request, res: Response): Response {
  if (hasSession(req)) return res
  const out = new Response(res.body, res)
  out.headers.append(
    'set-cookie',
    `${SESSION_COOKIE}=${crypto.randomUUID()}; Path=/; HttpOnly; Secure; SameSite=Lax`,
  )
  return out
}
