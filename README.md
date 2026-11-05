# Lebrel · lebrel.cl

Sitio de demostración **ficticio** de una peluquería y guardería canina. Lo usa Privai para mostrar sus
módulos funcionando sobre algo parecido a un sitio real: un Worker de Cloudflare que recibe un formulario,
guarda datos personales en D1 y comparte algunos con un tercero.

Nada de esto es real. El negocio no existe y nadie lee las reservas.

## Qué debería encontrar Veil

| Actividad | Datos | Finalidad | Conservación | Destinatario | Código |
|---|---|---|---|---|---|
| Reserva de hora | nombre, RUT, correo, teléfono, nombre y raza del perro, servicio, fecha, si tiene las vacunas al día, si pide retiro y dirección (solo con retiro) | Agendar y prestar el servicio de peluquería o guardería | 24 meses | Clínica Veterinaria Los Aromos SpA (solo guardería, para confirmar las vacunas; no recibe el correo ni la dirección) | `src/activities/reserva.ts`, `src/partners/veterinaria.ts`, `migrations/0001_reservas.sql` |
| Analítica del sitio | identificador aleatorio del visitante (cookie `lb_vid`), página visitada, sitio de origen y navegador | Estadísticas de uso del sitio, solo si el visitante acepta "Analítica" en el banner de Privai | 13 meses | Ninguno | `src/activities/analitica.ts`, `public/js/analytics.js`, `migrations/0002_visitas.sql` |

Cookies:

- `lb_session`: esencial. Solo comprueba que el formulario sale de nuestra página.
- `lb_vid`: no esencial, 13 meses. Solo se crea si la persona acepta "Analítica" en el banner de Privai.

Los plazos se aplican con un cron diario a las 04:00 (hora de Chile), en `src/retention.ts`.
La veterinaria solo recibe datos si su clave está configurada. En producción no lo está.

## Derechos ARSOP

Lebrel es un agente de Privai (`src/derechos.ts`). Cada minuto consulta las tareas pendientes de Privai,
toma las que le corresponden por `node_key`, las ejecuta y entrega el resultado. Privai nunca llama a Lebrel.
Sin `PRIVAI_AGENT_KEY` no hace nada. La persona se identifica por su correo.

| `node_key` | Acción | Qué hace |
|---|---|---|
| `lebrel_recopilar` | acceso (`collect`) | Entrega todas las reservas de la persona |
| `lebrel_eliminar` | supresión (`delete`) | Avisa a la veterinaria si recibió datos y borra las reservas |

La supresión es en cascada: las reservas que se compartieron con la veterinaria (guardería) se borran
primero allá. Si la veterinaria no confirma, no se borra nada y la tarea falla para que Privai la reintente.
Las reservas que nunca se compartieron (por ejemplo, un baño) se borran sin llamar a la veterinaria.
La analítica del sitio queda fuera: las visitas solo tienen el identificador de la cookie `lb_vid`.

Las personas ejercen sus derechos en el centro de privacidad: https://privacidad.lebrel.cl.

**Importante:** los bloques "Agente" de los workflows de Privai deben usar estas `node_key`
(`lebrel_recopilar` y `lebrel_eliminar`). Hay que actualizarlas en los workflows, porque si no coinciden
el agente no toma ninguna tarea.

## Cómo probarlo

Una persona puede cambiar el código y ver cómo cambia el RAT en Veil antes de hacer merge.

1. Agrega a la persona (o una cuenta de demo) como **colaboradora** del repo. Veil analiza los PR
   abiertos solo si los abre un colaborador; los de forks o externos los analiza recién al hacer merge.
2. La persona abre el repo en GitHub y aprieta `.` para abrir el editor en el navegador.
3. Agrega un campo a la reserva, por ejemplo "fecha de nacimiento del perro":
   en `public/index.html` (el formulario), en `src/activities/reserva.ts` (leerlo y guardarlo) y
   en una migración nueva en `migrations/` (la columna).
4. Hace commit en una rama nueva y abre un PR.
5. En Veil, el RAT muestra el dato nuevo en la actividad "Reserva de hora".

## Desarrollo

```bash
npm install
npm run db:migrate:local
npx wrangler dev        # http://localhost:8787
npm test
npm run typecheck
```

Las imágenes ya están en `public/`. Para volver a descargarlas:
`node scripts/fetch-media.mjs && python3 scripts/compress-images.py`
(créditos en `docs/media-credits.md`).

## Despliegue

A mano, desde una máquina con `wrangler login`:

```bash
npm run db:migrate:remote
npm run deploy
```

La CI (`.github/workflows/ci.yml`) corre `typecheck` y los tests en cada PR y en cada push a `main`.
Solo despliega (aplica las migraciones de D1 pendientes y publica el Worker) si la variable del repo
`DEPLOY_ENABLED` es `true`. Para eso necesita los secretos `CLOUDFLARE_API_TOKEN` (permisos de
Workers Scripts y D1, edición) y `CLOUDFLARE_ACCOUNT_ID`.

La base D1 se llama `lebrel`. El dominio `lebrel.cl` se conecta al Worker desde `wrangler.jsonc`
cuando la zona esté activa en Cloudflare.
