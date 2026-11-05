# Datos ficticios de los documentos de Drive: la empresa, la veterinaria y las personas.
# Los RUT, teléfonos y correos de personas se generan con random.Random(2026), así que son
# siempre los mismos. Los RUT tienen dígito verificador válido pero son inventados.
import random
import re
import unicodedata
import uuid
from datetime import date, timedelta

EMPRESA = {
    "razon_social": "Peluquería Canina Lebrel SpA",
    "nombre": "Lebrel, peluquería y guardería canina",
    "rut": "77.123.456-9",
    "giro": "Peluquería y guardería canina",
    "direccion": "Calle Los Aromos 0",
    "comuna": "Ñuñoa",
    "ciudad": "Santiago",
    "correo": "hola@lebrel.cl",
    "telefono": "+56 2 2000 0000",
    "web": "lebrel.cl",
    "privacidad": "privacidad.lebrel.cl",
    "horario": "Lunes a sábado, 9:00 a 19:00",
    "representante": "Valentina Rojas Fuentes",
}

VETERINARIA = {
    "razon_social": "Clínica Veterinaria Los Aromos SpA",
    "rut": "76.987.654-5",
    "direccion": "Avenida Irarrázaval 0",
    "comuna": "Ñuñoa",
    "representante": "Ignacio Fernández Rivas",
    "cargo_representante": "director médico",
    "api": "https://api.veterinaria-los-aromos.example/v1/confirmaciones-vacunas",
}

PRECIOS = [
    ("Baño", "Shampoo suave según su piel, secado a mano y cepillado.", 15_000),
    ("Baño y corte", "Todo lo del baño, más corte a tijera o máquina, uñas y limpieza de oídos.", 22_000),
    ("Guardería por el día", "Juego, paseo y siesta en grupos chicos, de 9:00 a 19:00. Con las vacunas al día.", 18_000),
    ("Retiro y entrega a domicilio", "Lo buscamos en tu casa y te lo devolvemos listo. Se suma a cualquier servicio.", 5_000),
]

SERVICIOS = {"bano": "Baño", "bano_corte": "Baño y corte", "guarderia": "Guardería por el día"}
VALOR_SERVICIO = {"bano": 15_000, "bano_corte": 22_000, "guarderia": 18_000}
VALOR_RETIRO = 5_000

# Nada de lo generado puede coincidir con el barrido de las Global Constraints (los corchetes evitan
# que el barrido encuentre este archivo).
PROHIBIDO = re.compile(r"31[1]2|3[:]40")


def rut_dv(n: int) -> str:
    """Dígito verificador de un RUT (módulo 11), igual que src/lib/rut.ts."""
    suma, peso = 0, 2
    for digito in reversed(str(n)):
        suma += int(digito) * peso
        peso = 2 if peso == 7 else peso + 1
    r = 11 - suma % 11
    return "0" if r == 11 else "K" if r == 10 else str(r)


def formato_rut(n: int) -> str:
    return f"{n:,}".replace(",", ".") + "-" + rut_dv(n)


def pesos(n: int) -> str:
    return "$" + f"{n:,}".replace(",", ".")


def fecha_larga(d: date) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


_rng = random.Random(2026)


def _limpio(generar):
    while True:
        valor = generar()
        if not PROHIBIDO.search(valor):
            return valor


def _rut(desde=8_000_000, hasta=21_999_999):
    # El cuerpo del RUT crece con el año de nacimiento; los rangos lo hacen verosímil.
    return _limpio(lambda: formato_rut(_rng.randint(desde, hasta)))


def _celular():
    return _limpio(lambda: f"+56 9 {_rng.randint(2000, 9999)} {_rng.randint(1000, 9999)}")


def _uuid():
    return _limpio(lambda: str(uuid.UUID(int=_rng.getrandbits(128), version=4)))


def _correo(nombre, apellido):
    n, a = _sin_tildes(nombre.split()[0]).lower(), _sin_tildes(apellido).lower()
    estilo = _rng.choice(["{n}.{a}", "{i}{a}", "{n}{a}{k}", "{n}_{a}"])
    return estilo.format(n=n, a=a, i=n[0], k=_rng.randint(10, 99)) + "@correo.example"


# Personas con nombre propio en los documentos. El orden de generación es fijo.
_PERSONAS = {
    "valentina": {"nombre": "Valentina Rojas Fuentes", "cargo": "Representante legal", "rango": (16_800_000, 17_200_000)},
    "arrendador": {
        "nombre": "Hernán Eduardo Vergara Lillo",
        "domicilio": "Avenida Grecia 0, departamento 52, Ñuñoa, Santiago",
        "profesion": "ingeniero comercial",
        "estado_civil": "casado",
        "rango": (9_000_000, 10_400_000),
    },
    "camila": {
        "nombre": "Camila Andrea Soto Muñoz",
        "nombre_corto": "Camila Soto Muñoz",
        "domicilio": "Pasaje Los Quillayes 0, La Florida, Santiago",
        "nacimiento": date(1996, 7, 9),
        "estado_civil": "soltera",
        "afp": "AFP Modelo",
        "salud": "Isapre Banmédica",
        "plan_uf": 2.10,
        "cargo": "Peluquera canina",
        "ingreso": date(2025, 3, 3),
        "banco": "Banco del Estado de Chile, CuentaRUT",
        "rango": (19_150_000, 19_600_000),
    },
    "maria_jose": {"nombre": "María José Herrera Contreras", "nombre_corto": "María José Herrera"},
    "emergencia_bruno": {"nombre": "Rodrigo Herrera Contreras", "relacion": "Hermano"},
    "veterinario": {"nombre": VETERINARIA["representante"], "rango": (13_400_000, 14_400_000)},
}
for _p in _PERSONAS.values():
    _p["rut"] = _rut(*_p.pop("rango", (12_000_000, 19_999_999)))
    _p["telefono"] = _celular()
_PERSONAS["maria_jose"]["correo"] = "mariajose.herrera@correo.example"
_PERSONAS["camila"]["correo"] = "camila.soto.m@correo.example"


def persona(clave: str) -> dict:
    return _PERSONAS[clave]


# --- Clientes y reservas de 2026 ---

_NOMBRES = ["Francisco", "Josefa", "Benjamín", "Antonia", "Tomás", "Catalina", "Vicente", "Fernanda",
            "Joaquín", "Constanza", "Martín", "Isidora", "Sebastián", "Daniela", "Diego", "Javiera",
            "Cristóbal", "Valeria", "Ignacio", "Paula", "Felipe", "Carolina", "Andrés", "Florencia",
            "Nicolás", "Macarena", "Gonzalo", "Trinidad", "Rodrigo", "Bárbara", "Pablo", "Francisca"]
_APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez",
              "Sepúlveda", "Morales", "Rodríguez", "López", "Araya", "Fuentes", "Hernández", "Torres",
              "Espinoza", "Flores", "Castillo", "Valenzuela", "Ramírez", "Reyes", "Gutiérrez", "Castro",
              "Vargas", "Álvarez", "Vásquez", "Tapia", "Carrasco", "Cortés", "Gómez", "Núñez", "Jara"]
_PERROS = ["Luna", "Simón", "Canela", "Rocco", "Nala", "Max", "Maite", "Coco", "Lola", "Tobías",
           "Kira", "Pancho", "Mora", "Thor", "Frida", "Bobby", "Olivia", "Milo", "Pelusa", "Zeus",
           "Chispa", "Oso", "Matilda", "Rufo", "Cleo", "Paco", "Nina", "Charlie", "Manchas", "Duna"]
_RAZAS = ["Poodle toy", "Schnauzer miniatura", "Golden retriever", "Labrador retriever", "Mestizo",
          "Shih tzu", "Bichón frisé", "Yorkshire terrier", "Cocker spaniel", "Border collie",
          "Beagle", "Bulldog francés", "Pastor alemán", "Maltés", "Dachshund", "Samoyedo", "Galgo"]
_CALLES = ["Avenida Irarrázaval", "Calle Dublé Almeyda", "Avenida Simón Bolívar", "Calle Suecia",
           "Avenida Pedro de Valdivia", "Calle José Domingo Cañas", "Avenida Ossandón", "Calle Exequiel Fernández"]

CLIENTE_RECLAMO = {
    "nombre": "Matías Fuenzalida Ortega",
    "correo": "matias.fuenzalida@correo.example",
    "perro": "Toby",
    "raza": "Schnauzer miniatura",
    "servicio": "bano_corte",
    "fecha": date(2026, 9, 12),
    "retiro": False,
}


def _fecha_2026():
    while True:
        d = date(2026, 1, 5) + timedelta(days=_rng.randint(0, 299))
        if d.weekday() != 6:  # el domingo está cerrado
            return d


def _clientes():
    usados = {"María José Herrera Contreras", CLIENTE_RECLAMO["nombre"]}
    filas = []
    while len(filas) < 28:
        nombre = f"{_rng.choice(_NOMBRES)} {_rng.choice(_APELLIDOS)} {_rng.choice(_APELLIDOS)}"
        if nombre in usados:
            continue
        usados.add(nombre)
        servicio = _rng.choices(["bano", "bano_corte", "guarderia"], weights=[4, 4, 3])[0]
        retiro = _rng.random() < 0.3
        filas.append({
            "nombre": nombre,
            "rut": _rut(),
            "correo": _correo(nombre.split()[0], nombre.split()[1]),
            "telefono": _celular(),
            "perro": _rng.choice(_PERROS),
            "raza": _rng.choice(_RAZAS),
            "servicio": servicio,
            "fecha": _fecha_2026(),
            "retiro": retiro,
            "direccion": f"{_rng.choice(_CALLES)} 0, Ñuñoa" if retiro else None,
        })
    mj = _PERSONAS["maria_jose"]
    filas.append({
        "nombre": mj["nombre"], "rut": mj["rut"], "correo": mj["correo"], "telefono": mj["telefono"],
        "perro": "Bruno", "raza": "Labrador retriever", "servicio": "guarderia",
        "fecha": date(2026, 6, 15), "retiro": False, "direccion": None,
    })
    filas.append({**CLIENTE_RECLAMO, "rut": _rut(), "telefono": _celular(), "direccion": None})
    for f in filas:
        f["id"] = _uuid()
    return sorted(filas, key=lambda f: (f["fecha"], f["nombre"]))


CLIENTES = _clientes()
CLIENTE_RECLAMO = next(c for c in CLIENTES if c["nombre"] == CLIENTE_RECLAMO["nombre"])


def valor_reserva(c: dict) -> int:
    return VALOR_SERVICIO[c["servicio"]] + (VALOR_RETIRO if c["retiro"] else 0)


def reservas_octubre():
    """Reservas de octubre de 2026 para el log del sistema: clientes de la lista que vuelven."""
    reservas = []
    for _ in range(34):
        c = _rng.choice(CLIENTES)
        while True:
            d = date(2026, 10, 1) + timedelta(days=_rng.randint(0, 30))
            if d.weekday() != 6:
                break
        reservas.append({**c, "fecha": d, "id": _uuid(), "servicio": _rng.choice(list(SERVICIOS)),
                         "creada": _rng.randint(9 * 3600, 21 * 3600)})
    return sorted(reservas, key=lambda r: (r["fecha"], r["creada"]))


def rng():
    return _rng
