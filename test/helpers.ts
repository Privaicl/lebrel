import { SELF } from 'cloudflare:test'

type PostOpts = { accept?: 'json' | 'html'; origin?: string | null; cookie?: string | null }

export function post(path: string, body: Record<string, string>, opts: PostOpts = {}): Promise<Response> {
  const headers: Record<string, string> = { 'content-type': 'application/x-www-form-urlencoded' }
  const origin = opts.origin === undefined ? 'https://lebrel.cl' : opts.origin
  const cookie = opts.cookie === undefined ? 'lb_session=test' : opts.cookie
  if (origin) headers.origin = origin
  if (cookie) headers.cookie = cookie
  headers.accept = opts.accept === 'html' ? 'text/html' : 'application/json'
  return SELF.fetch(`https://lebrel.cl${path}`, { method: 'POST', headers, body: new URLSearchParams(body) })
}
