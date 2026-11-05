-- Visitas al sitio de Lebrel (analítica propia, solo con consentimiento).
-- Finalidad: estadísticas de uso del sitio (qué secciones se visitan y desde dónde llegan).
-- Datos: identificador aleatorio del visitante (cookie lb_vid), ruta, sitio de origen y navegador.
-- Conservación: 13 meses (ver src/retention.ts). Destinatarios: ninguno.
CREATE TABLE visitas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  visitor_id TEXT NOT NULL,
  ruta TEXT NOT NULL,
  referente TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX visitas_created_at ON visitas (created_at);
