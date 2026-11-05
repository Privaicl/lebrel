# Revisa los documentos ficticios de drive/: que existan, que digan lo que deben decir y que no
# arrastren nada de la ficción anterior. Uso: .venv-drive/bin/python -I scripts/drive/revisar.py
import re
import sys
from pathlib import Path

import docx
import openpyxl
import pptx
import pypdf

sys.dont_write_bytecode = True  # no deja __pycache__ junto a los scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402

DRIVE = Path(__file__).resolve().parents[2] / "drive"

RUT_RE = re.compile(r"\d{1,2}\.\d{3}\.\d{3}-[\dK]")
TELEFONO_RE = re.compile(r"\+?56[\s-]?[29]|\b9[\s-]?\d{4}[\s-]?\d{4}\b|\b2[\s-]?\d{4}[\s-]?\d{4}\b")
# El mismo barrido de las Global Constraints, aplicado al texto de cada archivo. Los corchetes de más
# (como "colo[n]iz") no cambian lo que encuentra, pero evitan que el barrido encuentre este archivo.
BARRIDO_RE = re.compile(
    r"colo[n]iz|\bnave\b|avista[m]iento|\bmisi[oó]n\b|[oó]rbita|bre[v]o|lebre[l]es|anu[b]is|hune[f]er|tutan[k]am"
    r"|3[:]40|03[:]40|31[1]2|\bcredo\b|se[ñn]al con",
    re.IGNORECASE,
)
RUT_EMPRESAS = {datos.EMPRESA["rut"], datos.VETERINARIA["rut"]}


def texto_docx(path):
    d = docx.Document(path)
    partes = [p.text for p in d.paragraphs]
    for tabla in d.tables:
        for fila in tabla.rows:
            partes.extend(celda.text for celda in fila.cells)
    for seccion in d.sections:
        partes.extend(p.text for p in seccion.header.paragraphs)
        partes.extend(p.text for p in seccion.footer.paragraphs)
    return "\n".join(partes)


def texto_xlsx(path):
    wb = openpyxl.load_workbook(path)
    lineas = []
    for ws in wb.worksheets:
        for fila in ws.iter_rows(values_only=True):
            lineas.append("\t".join("" if v is None else str(v) for v in fila))
    return "\n".join(lineas)


def texto_pptx(path):
    prs = pptx.Presentation(path)
    partes = []
    for lamina in prs.slides:
        for forma in lamina.shapes:
            if forma.has_text_frame:
                partes.append(forma.text_frame.text)
            if forma.has_table:
                for fila in forma.table.rows:
                    partes.extend(celda.text for celda in fila.cells)
            if forma.has_chart:
                for serie in forma.chart.plots[0].series:
                    partes.append(serie.name or "")
        if lamina.has_notes_slide:
            partes.append(lamina.notes_slide.notes_text_frame.text)
    return "\n".join(partes)


def texto_pdf(path):
    return "\n".join(pagina.extract_text() or "" for pagina in pypdf.PdfReader(path).pages)


def texto(path):
    extractor = {
        ".docx": texto_docx,
        ".xlsx": texto_xlsx,
        ".pptx": texto_pptx,
        ".pdf": texto_pdf,
    }.get(path.suffix)
    return extractor(path) if extractor else path.read_text(encoding="utf-8")


def ruts_de_personas(t):
    return [r for r in RUT_RE.findall(t) if r not in RUT_EMPRESAS]


# --- Comprobaciones específicas: cada una devuelve una lista de problemas ---


def contiene(*frases):
    return lambda path, t: [f"falta {f!r}" for f in frases if f not in t]


def no_contiene_ruts_de_personas(path, t):
    return [f"RUT de persona {r}" for r in ruts_de_personas(t)]


def filas_xlsx(path, t):
    ws = openpyxl.load_workbook(path).worksheets[0]
    filas = [f for f in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in f)]
    return [] if len(filas) == 30 else [f"{len(filas)} filas de datos, se esperaban 30"]


def laminas_pptx(path, t):
    n = len(pptx.Presentation(path).slides)
    return [] if n == 6 else [f"{n} láminas, se esperaban 6"]


def cabeceras_eml(path, t):
    cabecera = t.split("\n\n", 1)[0]
    faltan = [h for h in ("From:", "To:", "Date:", "Subject:") if not re.search(rf"^{h}", cabecera, re.M)]
    return [f"falta la cabecera {h}" for h in faltan]


def sin_arroba(path, t):
    return ["contiene '@'"] if "@" in t else []


def sin_telefono(path, t):
    return [f"teléfono {m.group(0)!r}" for m in TELEFONO_RE.finditer(t)]


def sin_ningun_rut(path, t):
    return [f"RUT {r}" for r in RUT_RE.findall(t)]


def palabras(minimo):
    def comprobar(path, t):
        n = len(t.split())
        return [] if n > minimo else [f"{n} palabras, se esperaban más de {minimo}"]

    return comprobar


CAMILA = datos.persona("camila")

ARCHIVOS = {
    "contrato-arriendo-local.docx": [contiene(datos.EMPRESA["rut"])],
    "contrato-trabajo-camila-soto.docx": [contiene("Isapre", CAMILA["rut"])],
    "liquidacion-sueldo-camila-soto-2026-10.pdf": [contiene(CAMILA["rut"], "AFP", "Isapre", "cesantía")],
    "convenio-veterinaria-los-aromos.pdf": [contiene(datos.VETERINARIA["rut"])],
    "clientes-y-reservas-2026.xlsx": [filas_xlsx, contiene("@correo.example")],
    "ficha-guarderia-bruno.pdf": [contiene("contacto de emergencia", "Bruno", datos.persona("maria_jose")["rut"])],
    "presentacion-credito-banco.pptx": [laminas_pptx, no_contiene_ruts_de_personas],
    "reclamo-cliente-2026-09-14.eml": [cabeceras_eml, contiene(datos.CLIENTE_RECLAMO["correo"])],
    "sistema-reservas-export-2026-10.log": [contiene("@correo.example")],
    "lista-de-precios-2026.pdf": [
        sin_arroba,
        no_contiene_ruts_de_personas,
        contiene("$15.000", "$22.000", "$18.000", "$5.000"),
    ],
    "entrevista-procesos-lebrel.docx": [
        contiene("Previred", "WhatsApp", "Instagram", "veterinaria", "[00:00]"),
        sin_ningun_rut,
        sin_arroba,
        sin_telefono,
        palabras(3500),
    ],
}


def revisar(nombre, comprobaciones):
    path = DRIVE / nombre
    if not path.exists():
        return ["no existe"]
    t = texto(path)
    problemas = []
    for comprobar in comprobaciones:
        problemas.extend(comprobar(path, t))
    for r in RUT_RE.findall(t):
        cuerpo, dv = r.replace(".", "").split("-")
        if datos.rut_dv(int(cuerpo)) != dv:
            problemas.append(f"RUT con dígito verificador inválido {r}")
    problemas.extend(f"barrido: {m.group(0)!r}" for m in BARRIDO_RE.finditer(t))
    return problemas


def main():
    ok = 0
    for nombre, comprobaciones in ARCHIVOS.items():
        problemas = revisar(nombre, comprobaciones)
        if problemas:
            print(f"FAIL {nombre}")
            for p in problemas:
                print(f"     - {p}")
        else:
            ok += 1
            print(f"OK   {nombre}")
    extras = sorted(p.name for p in DRIVE.glob("*") if p.name not in ARCHIVOS) if DRIVE.exists() else []
    for nombre in extras:
        print(f"FAIL {nombre}: archivo inesperado")
    print(f"{ok}/{len(ARCHIVOS)} OK")
    return 0 if ok == len(ARCHIVOS) and not extras else 1


if __name__ == "__main__":
    sys.exit(main())
