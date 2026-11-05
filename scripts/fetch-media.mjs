// Descarga las fotos del sitio a public/img y escribe docs/media-credits.md.
// Uso: node scripts/fetch-media.mjs && python3 scripts/compress-images.py
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const UA = { 'User-Agent': 'lebrel-demo/0.1' }

// Fotos de Wikimedia Commons, todas con licencia libre.
const images = [
  ['img/hero-borzoi.jpg', 'File:Kobold (my first Explore photo) - Flickr - Ferlinka Borzoi (Deb West).jpg'],
  ['img/servicio-bano.jpg', 'File:Washing a dog in a bath tub.jpg'],
  ['img/servicio-corte.jpg', 'File:White dog being groomed on table.jpg'],
  ['img/servicio-guarderia.jpg', 'File:Dogs playing 002.jpg'],
  ['img/servicio-retiro.jpg', 'File:A Beagle sitting in a car looking outside the window.jpg'],
]

const strip = (html = '') => html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function save(rel, url) {
  const res = await fetch(url, { headers: UA })
  if (!res.ok) throw new Error(`${res.status} ${url}`)
  const out = join(root, 'public', rel)
  await mkdir(dirname(out), { recursive: true })
  await writeFile(out, Buffer.from(await res.arrayBuffer()))
}

const rows = []
for (const [rel, title] of images) {
  const q = new URLSearchParams({
    action: 'query', format: 'json', titles: title, prop: 'imageinfo',
    iiprop: 'url|extmetadata|size', iiurlwidth: '1600',
  })
  const data = await (await fetch(`https://commons.wikimedia.org/w/api.php?${q}`, { headers: UA })).json()
  const page = Object.values(data.query.pages)[0]
  const info = page.imageinfo[0]
  const meta = info.extmetadata
  await save(rel, info.width > 1600 ? info.thumburl : info.url)
  rows.push(`| \`${rel}\` | ${strip(meta.Artist?.value) || '—'} | ${meta.LicenseShortName?.value ?? '—'} | ${info.descriptionurl} |`)
  console.log('ok', rel)
  await pause(1500) // Commons limita las descargas seguidas.
}

await writeFile(
  join(root, 'docs/media-credits.md'),
  `# Créditos de imágenes\n\nGenerado por \`scripts/fetch-media.mjs\`.\n\n| Archivo | Autor | Licencia | Fuente |\n|---|---|---|---|\n${rows.join('\n')}\n`,
)
