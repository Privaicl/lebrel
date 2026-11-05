export interface Env {
  DB: D1Database
  ASSETS: Fetcher
  /** Orígenes desde los que aceptamos formularios, separados por coma. */
  ALLOWED_ORIGINS: string
  /** Secretos opcionales. Sin ellos, el envío a la veterinaria se omite. */
  VETERINARIA_API_KEY?: string
  VETERINARIA_API_URL?: string
  /** API de Privai a la que el agente de derechos ARSOP pide sus tareas. */
  PRIVAI_API_URL: string
  /** Clave del agente registrado en Privai (agent_…). Sin ella, el agente no hace nada. */
  PRIVAI_AGENT_KEY?: string
}
