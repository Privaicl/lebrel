-- Reservas de hora de peluquería y guardería.
-- Finalidad: agendar y prestar el servicio.
-- Conservación: 24 meses (ver src/retention.ts).
-- Destinatario: Clínica Veterinaria Los Aromos SpA, solo para guardería, para confirmar las vacunas
-- (ver src/partners/veterinaria.ts).
CREATE TABLE reservas (
  id TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  rut TEXT NOT NULL,
  correo TEXT NOT NULL,
  telefono TEXT NOT NULL,
  perro_nombre TEXT NOT NULL,
  perro_raza TEXT NOT NULL,
  servicio TEXT NOT NULL CHECK (servicio IN ('bano', 'bano_corte', 'guarderia')),
  fecha TEXT NOT NULL,
  vacunas_al_dia INTEGER NOT NULL CHECK (vacunas_al_dia IN (0, 1)),
  retiro INTEGER NOT NULL CHECK (retiro IN (0, 1)),
  direccion TEXT,
  declara_mayor_edad INTEGER NOT NULL CHECK (declara_mayor_edad = 1),
  compartida_veterinaria_at TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX reservas_created_at ON reservas (created_at);
