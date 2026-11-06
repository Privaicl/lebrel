-- Postulaciones de "Trabaja con nosotros".
-- Finalidad: evaluar postulantes a peluquero/a.
-- Datos: nombre, correo, teléfono, comuna, años de experiencia y descripción de la experiencia.
-- Conservación: 6 meses (ver src/retention.ts). Destinatarios: ninguno.
CREATE TABLE postulaciones (
  id TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  correo TEXT NOT NULL,
  telefono TEXT NOT NULL,
  comuna TEXT NOT NULL,
  experiencia_anios INTEGER NOT NULL CHECK (experiencia_anios BETWEEN 0 AND 50),
  experiencia TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX postulaciones_correo ON postulaciones (correo);
CREATE INDEX postulaciones_created_at ON postulaciones (created_at);
