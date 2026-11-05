# Genera los documentos ficticios de la carpeta de Drive de Lebrel en drive/.
# Uso: .venv-drive/bin/python -I scripts/drive/generar.py
import random
import re
import sys
from datetime import date, datetime, timedelta
from email.header import Header
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import docx
import openpyxl
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor as PptxRGB
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches
from pptx.util import Pt as PPt
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.dont_write_bytecode = True  # no deja __pycache__ junto a los scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402
from datos import EMPRESA, VETERINARIA, fecha_larga, pesos  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
DRIVE = RAIZ / "drive"
IMG = RAIZ / "public" / "img"
CHILE = ZoneInfo("America/Santiago")
rl_config.invariant = 1  # PDFs reproducibles: sin fecha de creación variable

# Colores del sitio (public/css/site.css)
MORADO = "#6236c9"
CIRUELA = "#9b3a6c"
TINTA = "#211a3a"
NIEBLA = "#5f5779"
LAVANDA = "#f2eff8"
LAVANDA_2 = "#e6e0f2"
PAPEL = "#fbf9fe"

RAZON_MAYUS = EMPRESA["razon_social"].upper().replace(" SPA", " SpA")  # "SpA" se escribe así también en mayúsculas
CAMILA = datos.persona("camila")
VALENTINA = datos.persona("valentina")


# ---------------------------------------------------------------- utilidades


def en_palabras(n: int) -> str:
    """Número en palabras, como se escribe en una liquidación ("Son: ... pesos")."""
    unidades = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
                "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho",
                "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
                "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
    decenas = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
    centenas = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos",
                "setecientos", "ochocientos", "novecientos"]

    def menor_mil(x):
        if x == 100:
            return "cien"
        c, r = divmod(x, 100)
        partes = [centenas[c]] if c else []
        if r:
            if r < 30:
                partes.append(unidades[r])
            else:
                d, u = divmod(r, 10)
                partes.append(decenas[d] + (f" y {unidades[u]}" if u else ""))
        return " ".join(partes)

    millones, resto = divmod(n, 1_000_000)
    miles, simples = divmod(resto, 1000)
    partes = []
    if millones:
        partes.append("un millón" if millones == 1 else f"{menor_mil(millones)} millones")
    if miles:
        partes.append("mil" if miles == 1 else f"{menor_mil(miles)} mil")
    if simples:
        partes.append(menor_mil(simples))
    texto = " ".join(partes) or "cero"
    texto = re.sub(r"veintiuno (mil|millones)", r"veintiún \1", texto)
    texto = re.sub(r"\buno (mil|millones)", r"un \1", texto)
    return re.sub(r"uno$", "un", texto)


def miles(n) -> str:
    return f"{round(n):,}".replace(",", ".")


# ---------------------------------------------------------------- Word


def nuevo_docx(titulo: str, autor: str, creado: datetime, encabezado: str):
    d = docx.Document()
    estilo = d.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)
    rpr = estilo.element.get_or_add_rPr()
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "es-CL")
    rpr.append(lang)
    estilo.paragraph_format.space_after = Pt(6)
    estilo.paragraph_format.line_spacing = 1.15
    for nombre in ("Title", "Heading 1", "Heading 2"):
        s = d.styles[nombre]
        s.font.name = "Calibri"
        s.font.color.rgb = RGBColor.from_string(TINTA[1:])
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin, sec.bottom_margin = Cm(2.3), Cm(2.2)
    cab = sec.header.paragraphs[0]
    cab.text = encabezado
    cab.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in cab.runs:
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor.from_string(NIEBLA[1:])
    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = pie.add_run("Página ")
    r.font.size = Pt(8.5)
    campo_pagina(pie)
    cp = d.core_properties
    cp.title, cp.author, cp.last_modified_by = titulo, autor, autor
    cp.created = cp.modified = creado
    cp.language = "es-CL"
    cp.revision = 3
    return d


def campo_pagina(parrafo):
    run = parrafo.add_run()
    run.font.size = Pt(8.5)
    for tipo, instr in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = instr
        run._r.append(el)


def parrafo(d, texto="", negrita_inicial=None, alinear=WD_ALIGN_PARAGRAPH.JUSTIFY, tam=None, despues=None):
    p = d.add_paragraph()
    p.alignment = alinear
    if negrita_inicial:
        r = p.add_run(negrita_inicial + " ")
        r.bold = True
        if tam:
            r.font.size = Pt(tam)
    r = p.add_run(texto)
    if tam:
        r.font.size = Pt(tam)
    if despues is not None:
        p.paragraph_format.space_after = Pt(despues)
    return p


def centrado(d, texto, tam=11, negrita=False, despues=6, color=None):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.bold = negrita
    r.font.size = Pt(tam)
    if color:
        r.font.color.rgb = RGBColor.from_string(color[1:])
    p.paragraph_format.space_after = Pt(despues)
    return p


def sin_bordes(tabla):
    tbl_pr = tabla._tbl.tblPr
    bordes = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "nil")
        bordes.append(el)
    tbl_pr.append(bordes)


def sombrear(celda, color):
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color.lstrip("#"))
    tc_pr.append(shd)


def firmas(d, columnas):
    d.add_paragraph().paragraph_format.space_after = Pt(36)
    t = d.add_table(rows=1, cols=len(columnas))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    sin_bordes(t)
    for celda, lineas in zip(t.rows[0].cells, columnas):
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run("_______________________________\n")
        for i, linea in enumerate(lineas):
            r = p.add_run(linea + ("\n" if i < len(lineas) - 1 else ""))
            r.bold = i == 0
            r.font.size = Pt(10)


# ---------------------------------------------------------------- 1. contrato de arriendo


def contrato_arriendo(path):
    a = datos.persona("arrendador")
    d = nuevo_docx("Contrato de arrendamiento local Calle Los Aromos 0", "Valentina Rojas Fuentes",
                   datetime(2023, 2, 13, 11, 20), "Contrato de arrendamiento · Calle Los Aromos 0, Ñuñoa")
    centrado(d, "CONTRATO DE ARRENDAMIENTO DE LOCAL COMERCIAL", 14, True, 4)
    centrado(d, a["nombre"].upper(), 11, True, 0)
    centrado(d, "A", 11, False, 0)
    centrado(d, RAZON_MAYUS, 11, True, 18)

    parrafo(d, (
        f"En Santiago de Chile, a {fecha_larga(date(2023, 2, 15))}, entre don {a['nombre'].upper()}, chileno, "
        f"{a['estado_civil']}, {a['profesion']}, cédula nacional de identidad N° {a['rut']}, domiciliado en "
        f"{a['domicilio']}, en adelante también \"el Arrendador\"; y {RAZON_MAYUS}, "
        f"sociedad del giro peluquería y guardería canina, rol único tributario N° {EMPRESA['rut']}, "
        f"representada, según se acreditará, por doña {VALENTINA['nombre'].upper()}, chilena, cédula nacional "
        f"de identidad N° {VALENTINA['rut']}, ambas domiciliadas para estos efectos en {EMPRESA['direccion']}, "
        f"comuna de {EMPRESA['comuna']}, {EMPRESA['ciudad']}, en adelante también \"la Arrendataria\"; se ha "
        "convenido el siguiente contrato de arrendamiento:"
    ))
    clausulas = [
        ("PRIMERO: Propiedad.", (
            "El Arrendador es dueño del local comercial ubicado en Calle Los Aromos 0, comuna de Ñuñoa, "
            "Región Metropolitana, de aproximadamente 140 metros cuadrados construidos y un patio interior de "
            "90 metros cuadrados, inscrito a su nombre a fojas 48.215 número 70.418 del Registro de Propiedad "
            "del Conservador de Bienes Raíces de Santiago correspondiente al año 2009, rol de avalúo fiscal "
            "N° 2617-24 de la comuna de Ñuñoa. Por el presente instrumento, el Arrendador da en arrendamiento "
            "a la Arrendataria el referido inmueble, quien lo acepta para sí."
        )),
        ("SEGUNDO: Destino.", (
            "La Arrendataria destinará el inmueble exclusivamente al funcionamiento de una peluquería canina, "
            "una guardería diurna de perros y la venta de accesorios para mascotas. Queda prohibido que los "
            "animales pernocten en el local. Será de cargo de la Arrendataria obtener y mantener vigentes la "
            "patente municipal y las autorizaciones sanitarias que exija la actividad."
        )),
        ("TERCERO: Plazo.", (
            "El arrendamiento comenzará a regir el 1 de marzo de 2023 y durará tres años, hasta el 28 de "
            "febrero de 2026. Se renovará tácita y automáticamente por períodos sucesivos de un año cada uno, "
            "salvo que cualquiera de las partes manifieste su voluntad de ponerle término mediante carta "
            "certificada enviada al domicilio de la otra con a lo menos noventa días de anticipación al "
            "vencimiento del período en curso."
        )),
        ("CUARTO: Renta.", (
            "La renta mensual de arrendamiento será la suma equivalente en pesos a 30 Unidades de Fomento "
            "(UF 30), según el valor de la Unidad de Fomento del día de pago. La renta se pagará por "
            "anticipado, dentro de los primeros cinco días de cada mes, mediante transferencia electrónica a "
            "la cuenta bancaria que el Arrendador indique por escrito. El simple retardo en el pago de la "
            "renta constituirá en mora a la Arrendataria y devengará, a título de multa, un interés "
            "equivalente al máximo convencional por cada día de atraso."
        )),
        ("QUINTO: Garantía.", (
            "A fin de garantizar la conservación de la propiedad y su restitución en el mismo estado en que "
            "la recibe, la Arrendataria entrega en este acto al Arrendador la suma equivalente a un mes de "
            "renta, que este declara recibir a su entera satisfacción. El Arrendador devolverá la garantía, "
            "reajustada, dentro de los treinta días siguientes a la restitución del inmueble, descontando "
            "los deterioros y los consumos impagos, si los hubiere. La Arrendataria no podrá imputar la "
            "garantía al pago de la renta del último mes."
        )),
        ("SEXTO: Gastos y consumos.", (
            "Serán de cargo de la Arrendataria los consumos de electricidad, agua potable, gas y extracción "
            "extraordinaria de residuos, que deberá pagar puntualmente, exhibiendo los comprobantes cuando el "
            "Arrendador lo solicite. Las contribuciones de bienes raíces serán de cargo del Arrendador."
        )),
        ("SÉPTIMO: Mejoras.", (
            "La Arrendataria podrá instalar tinas, mesas de peluquería, desagües, revestimientos lavables y el "
            "cierre perimetral del patio, previa autorización escrita del Arrendador. Las mejoras que no "
            "puedan separarse sin detrimento del inmueble quedarán a beneficio de la propiedad, sin cargo "
            "para el Arrendador. Las instalaciones que puedan retirarse sin daño podrán ser retiradas por la "
            "Arrendataria al término del contrato."
        )),
        ("OCTAVO: Obligaciones de la Arrendataria.", (
            "La Arrendataria se obliga a mantener el inmueble en perfecto estado de aseo y conservación; a "
            "retirar diariamente los desechos de los animales y disponerlos conforme a la normativa municipal; "
            "a adoptar medidas razonables para que los ladridos no perturben a los vecinos fuera del horario "
            "de atención; a reparar a su costa los desperfectos de llaves, enchufes, vidrios y cerraduras; y a "
            "no subarrendar ni ceder el contrato sin autorización escrita del Arrendador."
        )),
        ("NOVENO: Terminación anticipada.", (
            "El Arrendador podrá poner término inmediato al contrato si la Arrendataria no paga la renta "
            "dentro de los diez días siguientes a su vencimiento, destina el inmueble a un fin distinto del "
            "pactado, causa daños graves a la propiedad o infringe cualquiera de las obligaciones de la "
            "cláusula octava."
        )),
        ("DÉCIMO: Visitas.", (
            "La Arrendataria facilitará al Arrendador, o a quien este designe, la visita del inmueble una vez "
            "al mes, en día y hora hábil, avisándole con a lo menos 48 horas de anticipación."
        )),
        ("UNDÉCIMO: Entrega.", (
            "El inmueble se entrega en buen estado de conservación, con sus instalaciones de agua, gas y "
            "electricidad funcionando y libre de consumos pendientes, según consta en el acta de entrega e "
            "inventario que, firmada por ambas partes, forma parte integrante de este contrato como Anexo N° 1."
        )),
        ("DUODÉCIMO: Domicilio.", (
            "Para todos los efectos de este contrato, las partes fijan su domicilio en la comuna y ciudad de "
            "Santiago y se someten a la jurisdicción de sus tribunales ordinarios de justicia."
        )),
        ("DECIMOTERCERO: Personería.", (
            f"La personería de doña {VALENTINA['nombre']} para representar a {EMPRESA['razon_social']} consta "
            "en el estatuto de constitución de la sociedad, inscrito en el Registro de Empresas y Sociedades "
            "con fecha 9 de enero de 2023, documento que no se inserta por ser conocido de las partes."
        )),
        ("DECIMOCUARTO: Ejemplares.", (
            "El presente contrato se firma en dos ejemplares de idéntico tenor y fecha, quedando uno en poder "
            "de cada parte."
        )),
    ]
    for titulo, texto in clausulas:
        parrafo(d, texto, titulo)
    firmas(d, [
        [a["nombre"].upper(), "ARRENDADOR", f"C.I. N° {a['rut']}"],
        [f"p.p. {RAZON_MAYUS}", VALENTINA["nombre"].upper(), "ARRENDATARIA",
         f"RUT {EMPRESA['rut']}"],
    ])
    d.save(path)


# ---------------------------------------------------------------- 2. contrato de trabajo

SUELDO_BASE = 620_000
COMISION = 85_000
MOVILIZACION = 40_000
COLACION = 50_000
ANTICIPO = 100_000
UF_31_OCT = 40_318.52
UTM_OCT = 69_874
IMM = 539_000
TASA_AFP = 0.1058  # 10% + comisión AFP Modelo
CESANTIA_TRABAJADOR = 0.006


def contrato_trabajo(path):
    c = CAMILA
    ingreso = c["ingreso"]
    d = nuevo_docx("Contrato de trabajo Camila Soto Muñoz", "Valentina Rojas Fuentes",
                   datetime(2025, 2, 27, 18, 5), f"{EMPRESA['razon_social']} · Contrato individual de trabajo")
    centrado(d, "CONTRATO INDIVIDUAL DE TRABAJO", 14, True, 18)
    parrafo(d, (
        f"En Santiago, a {fecha_larga(ingreso)}, entre {RAZON_MAYUS}, RUT {EMPRESA['rut']}, "
        f"representada por doña {VALENTINA['nombre']}, cédula nacional de identidad N° {VALENTINA['rut']}, "
        f"ambas con domicilio en {EMPRESA['direccion']}, comuna de {EMPRESA['comuna']}, {EMPRESA['ciudad']}, en "
        f"adelante \"el Empleador\"; y doña {c['nombre'].upper()}, de nacionalidad chilena, nacida el "
        f"{fecha_larga(c['nacimiento'])}, cédula nacional de identidad N° {c['rut']}, {c['estado_civil']}, "
        f"domiciliada en {c['domicilio']}, en adelante \"la Trabajadora\", se ha convenido el siguiente "
        "contrato individual de trabajo:"
    ))
    clausulas = [
        ("PRIMERO: Naturaleza de los servicios.", (
            "La Trabajadora se obliga a prestar servicios como peluquera canina, que comprenden el baño, "
            "secado y cepillado de los perros, el corte a tijera y a máquina, el corte de uñas y la limpieza "
            "de oídos, así como la mantención y limpieza de los equipos y del área de trabajo. "
            "Ocasionalmente podrá apoyar la recepción y la entrega de los perros a sus dueños."
        )),
        ("SEGUNDO: Lugar de trabajo.", (
            f"Los servicios se prestarán en el local del Empleador ubicado en {EMPRESA['direccion']}, comuna "
            f"de {EMPRESA['comuna']}, {EMPRESA['ciudad']}."
        )),
        ("TERCERO: Jornada de trabajo.", (
            "La jornada ordinaria será de 44 horas semanales, distribuidas de lunes a viernes de 9:30 a 18:30 "
            "horas y los sábados de 9:00 a 13:00 horas, con una interrupción de 60 minutos para colación de "
            "lunes a viernes, que no se imputa a la jornada. De conformidad con la Ley N° 21.561, la jornada "
            "se reducirá a 42 horas semanales a contar del 26 de abril de 2026, sin disminución de la "
            "remuneración; la nueva distribución se acordará por escrito en un anexo de este contrato. La "
            "asistencia se registrará en el libro de asistencia que el Empleador mantiene en el local."
        )),
        ("CUARTO: Remuneración.", (
            f"El Empleador pagará a la Trabajadora un sueldo base mensual de {pesos(SUELDO_BASE)} "
            f"({en_palabras(SUELDO_BASE)} pesos); una comisión equivalente al 5% del valor neto de los "
            "servicios de baño y de baño y corte realizados por ella en el mes; y una gratificación legal "
            "conforme al artículo 50 del Código del Trabajo, equivalente al 25% de lo devengado en el mes por "
            "concepto de remuneraciones, con el tope de 4,75 ingresos mínimos mensuales al año, que se pagará "
            f"mensualmente. Además, pagará una asignación de movilización de {pesos(MOVILIZACION)} y una "
            f"asignación de colación de {pesos(COLACION)} mensuales, que no constituyen remuneración. La "
            "remuneración se pagará el último día hábil de cada mes, mediante transferencia electrónica a la "
            "cuenta bancaria que indique la Trabajadora. A petición de ella, el día 15 de cada mes se podrá "
            "otorgar un anticipo de hasta el 30% del sueldo base."
        )),
        ("QUINTO: Previsión y salud.", (
            f"La Trabajadora declara estar afiliada a {c['afp']} y a {c['salud']}, con un plan de salud "
            "pactado de 2,10 UF mensuales. El Empleador descontará de su "
            "remuneración y enterará en dichas instituciones las cotizaciones previsionales y de salud, así "
            "como la cotización del seguro de cesantía de la Ley N° 19.728. Cualquier cambio de AFP o de "
            "Isapre deberá ser informado por escrito al Empleador."
        )),
        ("SEXTO: Obligaciones de la Trabajadora.", (
            "La Trabajadora se obliga a cumplir con esmero sus labores; a tratar a los perros con cuidado y "
            "respeto, sin usar métodos de sujeción que les causen dolor; a seguir las indicaciones de las "
            "fichas sobre alergias y conducta de cada perro; a usar los elementos de protección que le "
            "entregue el Empleador; y a mantener las normas de higiene del local."
        )),
        ("SÉPTIMO: Confidencialidad y datos personales de los clientes.", (
            "En el desempeño de sus funciones, la Trabajadora conocerá datos personales de los clientes, como "
            "el nombre y el teléfono que figuran en la agenda diaria. Se obliga a usarlos solo para prestar "
            "el servicio; a no copiarlos, fotografiarlos ni comunicarlos a terceros; y a no usar su teléfono "
            "personal para fotografiar a los perros ni para comunicarse con los clientes, para lo cual "
            "utilizará únicamente el teléfono del local, de conformidad con la Ley N° 21.719. Esta obligación "
            "subsistirá después del término del contrato."
        )),
        ("OCTAVO: Datos personales de la Trabajadora.", (
            "El Empleador tratará los datos personales de la Trabajadora para ejecutar este contrato y "
            "cumplir sus obligaciones laborales, previsionales y tributarias. Para ello los comunicará a su "
            "contadora externa, que presta servicios por encargo del Empleador, y a las instituciones que "
            "corresponda, como Previred, la AFP, la Isapre, la mutualidad, la Dirección del Trabajo y el "
            "Servicio de Impuestos Internos. Los conservará mientras dure la relación laboral y por cinco años "
            "después de su término. La Trabajadora podrá ejercer sus derechos de acceso, rectificación, "
            "supresión, oposición, portabilidad y bloqueo dirigiéndose a la representante del Empleador."
        )),
        ("NOVENO: Feriado.", (
            "La Trabajadora tendrá derecho a un feriado anual de quince días hábiles con remuneración íntegra, "
            "que se otorgará de preferencia en los meses de enero y febrero, de común acuerdo."
        )),
        ("DÉCIMO: Duración.", (
            f"El presente contrato es de duración indefinida. La Trabajadora ingresó al servicio del Empleador "
            f"el {fecha_larga(ingreso)}."
        )),
        ("UNDÉCIMO: Ejemplares.", (
            "El presente contrato se firma en dos ejemplares de igual tenor y fecha, quedando uno en poder de "
            "cada parte. La Trabajadora declara haber recibido su ejemplar en este acto."
        )),
    ]
    for titulo, texto in clausulas:
        parrafo(d, texto, titulo)
    firmas(d, [
        [f"p.p. {RAZON_MAYUS}", VALENTINA["nombre"], "EMPLEADOR", f"RUT {EMPRESA['rut']}"],
        [c["nombre"].upper(), "TRABAJADORA", f"C.I. N° {c['rut']}"],
    ])
    d.save(path)


# ---------------------------------------------------------------- PDF: estilos comunes


def estilos():
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor(TINTA))
    return {
        "base": base,
        "just": ParagraphStyle("just", parent=base, alignment=TA_JUSTIFY, spaceAfter=6),
        "chico": ParagraphStyle("chico", parent=base, fontSize=8, leading=10.5, textColor=colors.HexColor(NIEBLA)),
        "chico_c": ParagraphStyle("chico_c", parent=base, fontSize=8, leading=10.5, alignment=TA_CENTER,
                                  textColor=colors.HexColor(NIEBLA)),
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=19,
                                 alignment=TA_CENTER, spaceAfter=4),
        "subtitulo": ParagraphStyle("subtitulo", parent=base, fontSize=10, alignment=TA_CENTER,
                                    textColor=colors.HexColor(NIEBLA), spaceAfter=14),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=10, leading=13,
                             textColor=colors.HexColor(MORADO), spaceBefore=10, spaceAfter=4),
        "der": ParagraphStyle("der", parent=base, alignment=TA_RIGHT),
        "negrita": ParagraphStyle("negrita", parent=base, fontName="Helvetica-Bold"),
        "centro": ParagraphStyle("centro", parent=base, alignment=TA_CENTER),
    }


E = estilos()


def logo(canvas, x, y, r=9):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(MORADO))
    canvas.circle(x + r, y + r, r, stroke=0, fill=1)
    canvas.setStrokeColor(colors.HexColor(PAPEL))
    canvas.setLineWidth(r * 0.19)
    canvas.setLineCap(2)
    p = canvas.beginPath()
    p.moveTo(x + r * 0.75, y + r * 1.47)
    p.lineTo(x + r * 0.75, y + r * 0.56)
    p.lineTo(x + r * 1.28, y + r * 0.56)
    canvas.drawPath(p, stroke=1, fill=0)
    canvas.restoreState()


def membrete(titulo_pie):
    def dibujar(canvas, doc):
        ancho, alto = LETTER
        canvas.saveState()
        logo(canvas, 2 * cm, alto - 2.05 * cm)
        canvas.setFillColor(colors.HexColor(TINTA))
        canvas.setFont("Times-Bold", 17)
        canvas.drawString(2 * cm + 24, alto - 1.9 * cm, "Lebrel")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(NIEBLA))
        canvas.drawString(2 * cm + 24, alto - 2.25 * cm, "PELUQUERÍA Y GUARDERÍA CANINA")
        canvas.drawRightString(ancho - 2 * cm, alto - 1.75 * cm, f"{EMPRESA['razon_social']} · RUT {EMPRESA['rut']}")
        canvas.drawRightString(ancho - 2 * cm, alto - 2.1 * cm,
                               f"{EMPRESA['direccion']}, {EMPRESA['comuna']}, {EMPRESA['ciudad']}")
        canvas.setStrokeColor(colors.HexColor(LAVANDA_2))
        canvas.setLineWidth(0.8)
        canvas.line(2 * cm, alto - 2.55 * cm, ancho - 2 * cm, alto - 2.55 * cm)
        canvas.line(2 * cm, 1.6 * cm, ancho - 2 * cm, 1.6 * cm)
        canvas.drawString(2 * cm, 1.15 * cm, titulo_pie)
        canvas.drawRightString(ancho - 2 * cm, 1.15 * cm, f"Página {doc.page}")
        canvas.restoreState()

    return dibujar


def pdf(path, titulo, autor, asunto, flowables, pie, top=3.2):
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=top * cm, bottomMargin=2.2 * cm, title=titulo, author=autor,
                            subject=asunto, creator="Lebrel")
    doc.build(flowables, onFirstPage=membrete(pie), onLaterPages=membrete(pie))


class Firma(Flowable):
    """Un garabato de firma sobre una línea, con el nombre debajo."""

    def __init__(self, semilla, lineas, ancho=6.5 * cm):
        super().__init__()
        self.semilla, self.lineas, self.ancho = semilla, lineas, ancho
        self.height = 1.75 * cm + 11 * len(lineas)

    def wrap(self, *args):
        return self.ancho, self.height

    def draw(self):
        c = self.canv
        rnd = random.Random(self.semilla)
        base = 11 * len(self.lineas) + 10
        c.setStrokeColor(colors.HexColor("#1f2a6b"))
        c.setLineWidth(1.1)
        x, y = self.ancho * rnd.uniform(0.15, 0.3), base + rnd.uniform(10, 16)
        p = c.beginPath()
        p.moveTo(x, y)
        # Una mayúscula alta y después una serie de bucles de tamaño variable.
        alto = rnd.uniform(18, 30)
        p.curveTo(x + 2, y + alto, x + 10, y + alto, x + 6, y - 2)
        x += 6
        for _ in range(rnd.randint(3, 6)):
            dx = rnd.uniform(8, 22)
            p.curveTo(x + dx * 0.3, y + rnd.uniform(6, 22), x + dx * 0.7, y - rnd.uniform(4, 14), x + dx,
                      y + rnd.uniform(-4, 6))
            x += dx
        p.curveTo(x + rnd.uniform(5, 15), y + rnd.uniform(10, 22), x - rnd.uniform(30, 60), y - 4,
                  x + rnd.uniform(10, 25), y - rnd.uniform(3, 9))
        c.drawPath(p, stroke=1, fill=0)
        c.setStrokeColor(colors.HexColor(TINTA))
        c.setLineWidth(0.6)
        c.line(0, base, self.ancho, base)
        c.setFillColor(colors.HexColor(TINTA))
        for i, linea in enumerate(self.lineas):
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 8.5)
            c.drawCentredString(self.ancho / 2, base - 11 * (i + 1), linea)


def tabla(filas, anchos, estilo_extra=(), cabecera=True, zebra=False):
    t = Table(filas, colWidths=anchos)
    estilo = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(TINTA)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(LAVANDA_2)),
    ]
    if cabecera:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MORADO)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ]
    if zebra:
        for i in range(1 if cabecera else 0, len(filas), 2):
            estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(LAVANDA)))
    t.setStyle(TableStyle(estilo + list(estilo_extra)))
    return t


# ---------------------------------------------------------------- 3. liquidación de sueldo


def calcular_liquidacion():
    tope_grat = round(4.75 * IMM / 12)
    gratificacion = min(round(0.25 * (SUELDO_BASE + COMISION)), tope_grat)
    imponible = SUELDO_BASE + COMISION + gratificacion
    no_imponible = MOVILIZACION + COLACION
    afp = round(imponible * TASA_AFP)
    salud_legal = round(imponible * 0.07)
    plan = round(CAMILA["plan_uf"] * UF_31_OCT)
    salud = max(plan, salud_legal)
    cesantia = round(imponible * CESANTIA_TRABAJADOR + 1e-9)
    tributable = imponible - afp - salud_legal - cesantia
    impuesto = 0 if tributable <= 13.5 * UTM_OCT else None
    assert impuesto == 0, "la liquidación de ejemplo debe quedar exenta del impuesto único"
    legales = afp + salud + cesantia
    haberes = imponible + no_imponible
    liquido = haberes - legales - ANTICIPO
    return locals()


def liquidacion(path):
    L = calcular_liquidacion()
    c = CAMILA
    cuerpo = [
        Paragraph("LIQUIDACIÓN DE SUELDO", E["titulo"]),
        Paragraph("Período: octubre de 2026 · Fecha de pago: 30 de octubre de 2026", E["subtitulo"]),
    ]
    datos_trab = [
        ["Trabajadora", c["nombre"], "RUT", c["rut"]],
        ["Cargo", c["cargo"], "Fecha de ingreso", c["ingreso"].strftime("%d-%m-%Y")],
        ["Tipo de contrato", "Indefinido", "Días trabajados", "30"],
        ["AFP", f"{c['afp']} (10,58%)", "Salud", f"{c['salud']} · plan 2,10 UF"],
        ["Forma de pago", "Transferencia a CuentaRUT", "Centro de costo", "Peluquería"],
    ]
    cuerpo.append(tabla(datos_trab, [3.1 * cm, 5.6 * cm, 3.1 * cm, 5.7 * cm], [
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8.5),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LAVANDA)),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(LAVANDA)),
    ], cabecera=False))
    cuerpo.append(Spacer(1, 12))

    haberes = [
        ["HABERES", ""],
        ["Sueldo base", miles(SUELDO_BASE)],
        ["Comisión por servicios (5%)", miles(COMISION)],
        ["Gratificación legal (art. 50)", miles(L["gratificacion"])],
        ["Total imponible", miles(L["imponible"])],
        ["Asignación de movilización", miles(MOVILIZACION)],
        ["Asignación de colación", miles(COLACION)],
        ["Total no imponible", miles(L["no_imponible"])],
        ["", ""],
        ["TOTAL HABERES", miles(L["haberes"])],
    ]
    descuentos = [
        ["DESCUENTOS", ""],
        ["AFP Modelo (10,58%)", miles(L["afp"])],
        ["Isapre Banmédica: 7% legal", miles(L["salud_legal"])],
        ["Isapre Banmédica: adicional plan", miles(L["salud"] - L["salud_legal"])],
        ["Seguro de cesantía (0,6%)", miles(L["cesantia"])],
        ["Impuesto único 2.ª categoría", "0"],
        ["Total descuentos legales", miles(L["legales"])],
        ["Anticipo de sueldo (15-10-2026)", miles(ANTICIPO)],
        ["", ""],
        ["TOTAL DESCUENTOS", miles(L["legales"] + ANTICIPO)],
    ]
    filas = [h + [""] + dsc for h, dsc in zip(haberes, descuentos)]
    destacar = []
    for i in (4, 7):
        destacar += [("FONT", (0, i), (1, i), "Helvetica-Bold", 9), ("LINEABOVE", (1, i), (1, i), 0.6, colors.HexColor(NIEBLA))]
    for i in (6,):
        destacar += [("FONT", (3, i), (4, i), "Helvetica-Bold", 9), ("LINEABOVE", (4, i), (4, i), 0.6, colors.HexColor(NIEBLA))]
    t = Table(filas, colWidths=[5.4 * cm, 2.9 * cm, 0.6 * cm, 5.7 * cm, 2.9 * cm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(TINTA)),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor(MORADO)),
        ("BACKGROUND", (3, 0), (4, 0), colors.HexColor(CIRUELA)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9.5),
        ("BACKGROUND", (0, -1), (1, -1), colors.HexColor(LAVANDA)),
        ("BACKGROUND", (3, -1), (4, -1), colors.HexColor(LAVANDA)),
        ("BOX", (0, 0), (1, -1), 0.6, colors.HexColor(LAVANDA_2)),
        ("BOX", (3, 0), (4, -1), 0.6, colors.HexColor(LAVANDA_2)),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ] + destacar))
    cuerpo += [t, Spacer(1, 12)]

    liquido = Table([
        ["LÍQUIDO A PAGAR", pesos(L["liquido"])],
        [Paragraph(f"Son: {en_palabras(L['liquido'])} pesos.", E["chico"]), ""],
    ], colWidths=[11.5 * cm, 6 * cm])
    liquido.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TINTA)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 12),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("SPAN", (0, 1), (1, 1)),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(TINTA)),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    cuerpo += [liquido, Spacer(1, 14)]

    info = [
        ["Base de cálculo", "", "Aportes del empleador (informativo)", ""],
        ["Base tributable", miles(L["tributable"]), "Seguro de cesantía (2,4%)", miles(L["imponible"] * 0.024)],
        ["Tramo impuesto único", "Exento (hasta 13,5 UTM)", "Seguro de invalidez y sobrevivencia (1,54%)",
         miles(L["imponible"] * 0.0154)],
        ["UF al 31-10-2026", f"$ {UF_31_OCT:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
         "Ley N° 16.744, mutualidad (0,93%)", miles(L["imponible"] * 0.0093)],
        ["UTM octubre 2026", pesos(UTM_OCT), "Ingreso mínimo mensual", pesos(IMM)],
    ]
    t = Table(info, colWidths=[3.6 * cm, 4.2 * cm, 6.6 * cm, 3.1 * cm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(NIEBLA)),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(MORADO)),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(LAVANDA_2)),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    cuerpo += [t, Spacer(1, 10)]
    cuerpo.append(Paragraph(
        f"Certifico que he recibido de {EMPRESA['razon_social']}, a mi entera satisfacción, el total líquido "
        "indicado en la presente liquidación, y que no tengo cargo ni cobro posterior alguno que hacer por "
        "los conceptos de esta liquidación.", E["just"]))
    cuerpo.append(Spacer(1, 10))
    firmas_t = Table([[
        Firma(11, [VALENTINA["nombre"], f"p.p. {EMPRESA['razon_social']}"]),
        Firma(29, [c["nombre"], f"RUT {c['rut']}"]),
    ]], colWidths=[8.75 * cm, 8.75 * cm])
    firmas_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    cuerpo.append(KeepTogether(firmas_t))
    pdf(path, "Liquidación de sueldo octubre 2026 · Camila Soto Muñoz", "Contabilidad Lebrel",
        "Liquidación de sueldo", cuerpo, "Liquidación de sueldo · octubre 2026 · documento confidencial")


# ---------------------------------------------------------------- 4. convenio con la veterinaria


def convenio(path):
    v = VETERINARIA
    vet = datos.persona("veterinario")
    firma_fecha = date(2026, 1, 15)
    cuerpo = [
        Paragraph("CONVENIO DE COMUNICACIÓN DE DATOS PERSONALES", E["titulo"]),
        Paragraph("Confirmación de vacunas para la guardería canina", E["subtitulo"]),
        Paragraph(
            f"En Santiago, a {fecha_larga(firma_fecha)}, comparecen: <b>{EMPRESA['razon_social']}</b>, RUT "
            f"{EMPRESA['rut']}, representada por doña {VALENTINA['nombre']}, ambas domiciliadas en "
            f"{EMPRESA['direccion']}, comuna de {EMPRESA['comuna']}, en adelante \"Lebrel\"; y <b>{v['razon_social']}</b>, "
            f"RUT {v['rut']}, representada por su {v['cargo_representante']}, don {vet['nombre']}, ambos domiciliados "
            f"en {v['direccion']}, comuna de {v['comuna']}, en adelante \"la Clínica\"; quienes acuerdan el "
            "siguiente convenio:", E["just"]),
    ]
    secciones = [
        ("PRIMERO: Antecedentes.", [
            "Lebrel presta servicios de peluquería y de guardería canina por el día en su local de Ñuñoa. Para "
            "proteger la salud de todos los perros del grupo, la guardería exige que cada perro tenga al día "
            "las vacunas antirrábica, óctuple y contra la traqueobronquitis infecciosa (tos de las perreras).",
            "La Clínica presta atención veterinaria en la misma comuna y mantiene el registro de vacunación de "
            "sus pacientes, o revisa el carnet de vacunas que le presente el dueño del perro.",
        ]),
        ("SEGUNDO: Objeto y finalidad.", [
            "Este convenio regula la comunicación de datos personales que Lebrel hace a la Clínica con la "
            "<b>única finalidad de confirmar que las vacunas del perro estén al día</b> antes de que asista a "
            "la guardería. La comunicación se funda en la ejecución del contrato de servicio que el cliente "
            "celebra con Lebrel al reservar la guardería (artículo 13, letra c, de la Ley N° 21.719).",
        ]),
        ("TERCERO: Datos que se comunican.", [
            "Lebrel solo comunica a la Clínica las reservas del servicio de guardería, y de cada una solo los "
            "datos que se indican a continuación:",
        ]),
    ]
    for titulo, ps in secciones:
        cuerpo.append(Paragraph(f"<b>{titulo}</b> " + ps[0], E["just"]))
        cuerpo += [Paragraph(p, E["just"]) for p in ps[1:]]
    filas = [
        ["Categoría", "Datos comunicados", "Datos que NO se comunican"],
        ["Cliente", "Nombre completo, RUT y teléfono", Paragraph("Correo electrónico y dirección", E["base"])],
        ["Perro", "Nombre y raza", "Cualquier otro dato del perro"],
        ["Reserva", Paragraph("Fecha de la reserva, declaración de vacunas al día e identificador interno "
                              "de la reserva (\"referencia\")", E["base"]),
         Paragraph("Servicio contratado, retiro a domicilio y fecha de envío", E["base"])],
        ["Otras reservas", Paragraph("Las reservas de baño y de baño y corte <b>no se comunican</b>", E["base"]), "—"],
    ]
    cuerpo += [tabla(filas, [2.8 * cm, 7.4 * cm, 7.3 * cm], [("VALIGN", (0, 0), (-1, -1), "TOP")], zebra=True),
               Spacer(1, 8)]
    resto = [
        ("CUARTO: Forma de la comunicación.", (
            "Lebrel envía cada reserva de guardería en forma automática, al momento de recibirla, mediante una "
            "conexión cifrada (HTTPS) a la interfaz de confirmación de vacunas de la Clínica, autenticada con "
            "una clave que cada parte guarda como secreto y que no se transmite por otros medios. La Clínica "
            "responde si la confirmación fue recibida. La dirección de la interfaz se indica en el Anexo N° 1."
        )),
        ("QUINTO: Uso permitido y prohibiciones.", (
            "La Clínica usará los datos recibidos solo para confirmar las vacunas. No podrá usarlos para enviar "
            "publicidad ni ofertas, para elaborar perfiles, ni para cruzarlos con otras bases de datos, salvo su "
            "propio registro de vacunación para el solo efecto de la confirmación. No podrá comunicarlos a "
            "terceros, salvo requerimiento de autoridad competente."
        )),
        ("SEXTO: Plazo de conservación.", (
            "La Clínica conservará cada confirmación por un máximo de <b>doce meses desde la fecha de la "
            "reserva</b> y, vencido ese plazo, la eliminará de sus sistemas. Lebrel conserva sus reservas por "
            "veinticuatro meses desde su envío."
        )),
        ("SÉPTIMO: Supresión.", (
            "Cuando un titular solicite a Lebrel la supresión de sus datos, Lebrel pedirá a la Clínica, a "
            "través de la misma interfaz y citando la referencia de la reserva, que elimine la confirmación "
            "recibida. La Clínica la eliminará dentro de dos días hábiles y confirmará la eliminación; si ya "
            "no la tiene, lo informará y esa respuesta valdrá como confirmación. Lebrel no eliminará su propia "
            "copia mientras la Clínica no confirme, para que la supresión sea completa."
        )),
        ("OCTAVO: Derechos de los titulares.", (
            "Si un titular se dirige a la Clínica para ejercer sus derechos sobre los datos recibidos en virtud "
            "de este convenio, la Clínica lo informará a Lebrel dentro de dos días hábiles, para que la "
            f"solicitud se gestione en el centro de privacidad de Lebrel ({EMPRESA['privacidad']})."
        )),
        ("NOVENO: Seguridad e incidentes.", (
            "Cada parte adoptará medidas de seguridad apropiadas al riesgo, entre ellas el cifrado en tránsito, "
            "el acceso restringido al personal que lo necesite y el registro de los accesos. La Clínica "
            "informará a Lebrel cualquier vulneración que afecte a estos datos dentro de las 24 horas siguientes "
            "a conocerla, para que Lebrel pueda reportarla a la Agencia de Protección de Datos Personales dentro "
            "del plazo legal."
        )),
        ("DÉCIMO: Calidad de las partes.", (
            "Lebrel es responsable del tratamiento de los datos de sus reservas. La Clínica es responsable del "
            "tratamiento que haga de los datos recibidos, el que queda limitado a la finalidad de este convenio."
        )),
        ("UNDÉCIMO: Vigencia y término.", (
            "Este convenio rige desde su firma por un año y se renueva automáticamente por períodos iguales. "
            "Cualquiera de las partes puede ponerle término avisando a la otra por escrito con treinta días de "
            "anticipación. Al término, la Clínica eliminará todas las confirmaciones recibidas dentro de diez "
            "días hábiles y lo certificará por escrito."
        )),
        ("DUODÉCIMO: Gratuidad y domicilio.", (
            "Este convenio no genera pagos entre las partes. Para todos sus efectos, las partes fijan domicilio "
            "en la comuna y ciudad de Santiago."
        )),
    ]
    for titulo, texto in resto:
        cuerpo.append(Paragraph(f"<b>{titulo}</b> {texto}", E["just"]))
    cuerpo.append(Spacer(1, 8))
    firmas_t = Table([[
        Firma(5, [VALENTINA["nombre"], f"p.p. {EMPRESA['razon_social']}", f"RUT {EMPRESA['rut']}"]),
        Firma(17, [vet["nombre"], f"p.p. {v['razon_social']}", f"RUT {v['rut']}"]),
    ]], colWidths=[8.75 * cm, 8.75 * cm])
    firmas_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    cuerpo.append(KeepTogether(firmas_t))
    cuerpo += [
        Spacer(1, 14),
        Paragraph("ANEXO N° 1: Interfaz de confirmación de vacunas", E["h2"]),
        tabla([
            ["Dirección", v["api"]],
            ["Envío de una reserva", "POST, con la referencia, los datos del cliente y del perro, la fecha y las vacunas"],
            ["Supresión", "DELETE a la dirección anterior seguida de la referencia de la reserva"],
            ["Autenticación", "Clave secreta en la cabecera Authorization (Bearer)"],
        ], [4 * cm, 13.5 * cm], [("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
                                 ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LAVANDA))], cabecera=False),
    ]
    pdf(path, "Convenio de comunicación de datos · Clínica Veterinaria Los Aromos", "Valentina Rojas Fuentes",
        "Convenio de comunicación de datos personales", cuerpo,
        f"Convenio Lebrel · {v['razon_social']} · {fecha_larga(firma_fecha)}")


# ---------------------------------------------------------------- 5. planilla de clientes


def planilla_clientes(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reservas 2026"
    cab = ["Fecha", "Servicio", "Cliente", "RUT", "Correo", "Teléfono", "Perro", "Raza", "Retiro",
           "Dirección de retiro", "Valor"]
    ws.append(cab)
    for c in datos.CLIENTES:
        ws.append([c["fecha"], datos.SERVICIOS[c["servicio"]], c["nombre"], c["rut"], c["correo"], c["telefono"],
                   c["perro"], c["raza"], "Sí" if c["retiro"] else "No", c["direccion"] or "",
                   datos.valor_reserva(c)])
    borde = Border(bottom=Side(style="thin", color="E6E0F2"))
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
        celda.fill = PatternFill("solid", fgColor=MORADO[1:])
        celda.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 22
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.font = Font(name="Calibri", size=11)
            celda.border = borde
        fila[0].number_format = "dd-mm-yyyy"
        fila[10].number_format = '"$"#,##0'
    anchos = [12, 20, 32, 14, 36, 17, 12, 22, 8, 34, 11]
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cab))}{ws.max_row}"
    wb.properties.creator = "Valentina Rojas Fuentes"
    wb.properties.lastModifiedBy = "Valentina Rojas Fuentes"
    wb.properties.title = "Clientes y reservas 2026"
    wb.properties.created = datetime(2026, 1, 12, 9, 30)
    wb.properties.modified = datetime(2026, 10, 31, 18, 45)
    wb.save(path)


# ---------------------------------------------------------------- 6. ficha de guardería


class Casilla(Flowable):
    """Casilla de formulario, marcada con una X a mano si corresponde."""

    def __init__(self, marcada):
        super().__init__()
        self.marcada = marcada
        self.width = self.height = 9

    def wrap(self, *args):
        return 9, 9

    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor(TINTA))
        c.setLineWidth(0.7)
        c.rect(0, 0, 9, 9)
        if self.marcada:
            c.setStrokeColor(colors.HexColor("#1f2a6b"))
            c.setLineWidth(1.4)
            c.line(1.2, 1.6, 7.8, 8.2)
            c.line(1.4, 7.9, 8.1, 1.2)


def opciones(*pares, anchos=None):
    """Una fila de casillas con su texto: opciones(("Sí", True), ("No", False))."""
    celdas, ws = [], []
    for (texto, marcada), ancho in zip(pares, anchos or [1.6 * cm] * len(pares)):
        celdas += [Casilla(marcada), Paragraph(texto, E["base"])]
        ws += [14, ancho]
    t = Table([celdas], colWidths=ws)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def ficha_bruno(path):
    mj = datos.persona("maria_jose")
    em = datos.persona("emergencia_bruno")
    rnd = random.Random(2026_06_15)
    chip = "".join(str(rnd.randint(0, 9)) for _ in range(9))
    P = lambda t, s="base": Paragraph(t, E[s])  # noqa: E731

    def bloque(titulo, filas, anchos=(4.2 * cm, 13.3 * cm)):
        t = Table([[P(f"<b>{a}</b>"), P(b) if isinstance(b, str) else b] for a, b in filas],
                  colWidths=list(anchos))
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(LAVANDA_2)),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LAVANDA)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return [KeepTogether([Paragraph(titulo, E["h2"]), t])]

    cuerpo = [
        Paragraph("FICHA DE INGRESO · GUARDERÍA POR EL DÍA", E["titulo"]),
        Paragraph("Fecha de ingreso: 15-06-2026 · Ficha N° G-2026-047", E["subtitulo"]),
    ]
    cuerpo += bloque("1. Datos del perro", [
        ("Nombre", "Bruno"),
        ("Raza / color", "Labrador retriever · chocolate"),
        ("Sexo / edad", "Macho · 4 años (nacido en abril de 2022)"),
        ("Peso", "29 kg"),
        ("Esterilizado", opciones(("Sí", True), ("No", False))),
        ("Microchip", f"985 112 {chip[:3]} {chip[3:6]} {chip[6:]}"),
    ])
    cuerpo += bloque("2. Datos de la dueña", [
        ("Nombre", mj["nombre"]),
        ("RUT", mj["rut"]),
        ("Teléfono", mj["telefono"]),
        ("Correo", mj["correo"]),
        ("Retiro a domicilio", opciones(("Sí", False), ("No (lo trae y lo retira ella)", True),
                                        anchos=[1.6 * cm, 9 * cm])),
    ])
    cuerpo += bloque("3. Contacto de emergencia", [
        ("Nombre", em["nombre"]),
        ("Relación", em["relacion"]),
        ("Teléfono", em["telefono"]),
        ("Uso", "Solo si no logramos ubicar a la dueña y es necesario tomar una decisión sobre Bruno."),
    ])
    vac = [
        ["Vacuna", "Fecha", "Vence", "Lugar"],
        ["Antirrábica", "18-03-2026", "18-03-2027", "Clínica Veterinaria Los Aromos"],
        ["Óctuple", "10-02-2026", "10-02-2027", "Clínica Veterinaria Los Aromos"],
        ["Tos de las perreras (KC)", "06-05-2026", "06-05-2027", "Clínica Veterinaria Los Aromos"],
        ["Desparasitación interna", "20-05-2026", "20-08-2026", "Clínica Veterinaria Los Aromos"],
        ["Antipulgas (pipeta)", "01-06-2026", "01-07-2026", "Aplicada por la dueña"],
    ]
    cuerpo += [Paragraph("4. Vacunas y desparasitación", E["h2"]),
               tabla(vac, [5 * cm, 2.6 * cm, 2.6 * cm, 7.3 * cm], zebra=True),
               Spacer(1, 3),
               Paragraph("Vacunas al día confirmadas por Clínica Veterinaria Los Aromos SpA el 12-06-2026.", E["chico"])]
    cuerpo += bloque("5. Salud y conducta", [
        ("Alergias", "<b>Alergia alimentaria al pollo</b>: no darle snacks ni premios con pollo. Piel sensible: "
                     "usar shampoo hipoalergénico."),
        ("Medicamentos", "Ninguno."),
        ("Alimentación", "Trae su comida. Una ración de 200 g a las 13:00 horas."),
        ("Conducta", "Sociable con perros y personas. Se pone nervioso con ruidos fuertes (truenos, fuegos "
                     "artificiales). Tira de la correa en los paseos."),
        ("Veterinaria de cabecera", "Clínica Veterinaria Los Aromos, Avenida Irarrázaval 0, Ñuñoa."),
    ])
    cuerpo += bloque("6. Autorizaciones", [
        ("Atención de urgencia", opciones((
            "Autorizo que, en caso de urgencia, Bruno sea llevado a la Clínica Veterinaria Los Aromos. Los costos "
            "de la atención serán de mi cargo.", True), anchos=[12.6 * cm])),
        ("Fotos en Instagram", opciones((
            "Autorizo publicar fotos de Bruno en el Instagram de Lebrel, sin mi nombre ni mi imagen. Puedo pedir "
            "que se retiren en cualquier momento.", True), anchos=[12.6 * cm])),
    ])
    cuerpo += [
        Spacer(1, 8),
        Paragraph(
            "Declaro que los datos de esta ficha son correctos y que informé a la persona indicada que la dejé como "
            "contacto de emergencia. Lebrel usa esta ficha para cuidar a Bruno en la guardería; la ve solo el "
            "personal de la guardería y la administración, y se destruye si Bruno no asiste durante dos años. "
            "En caso de no poder ubicar a la dueña, Lebrel llamará al contacto de emergencia. Más información en "
            f"{EMPRESA['privacidad']}.", E["chico"]),
        Spacer(1, 6),
    ]
    firmas_t = Table([[Firma(615, [mj["nombre"], f"RUT {mj['rut']}"]),
                       Firma(616, ["Recibido por Lebrel", "Asistente de guardería"])]],
                     colWidths=[8.75 * cm, 8.75 * cm])
    firmas_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    cuerpo.append(KeepTogether(firmas_t))
    pdf(path, "Ficha de ingreso guardería · Bruno", "Lebrel", "Ficha de ingreso a la guardería", cuerpo,
        "Ficha de ingreso guardería · Bruno · uso interno")


# ---------------------------------------------------------------- 7. presentación al banco

ATENCIONES_2026 = [512, 438, 561, 574, 589, 566, 603, 618, 597, 641]
CLIENTES_2026 = [318, 281, 344, 352, 361, 349, 368, 377, 365, 389]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct"]
INGRESOS = [("2023*", 64), ("2024", 112), ("2025", 131), ("2026**", 149)]
INVERSION = [
    ("Segunda sala de peluquería: mesa hidráulica, tina y secador de alto flujo", 4_800_000),
    ("Ampliación y techado del patio de la guardería (de 12 a 18 perros por día)", 9_200_000),
    ("Furgón utilitario usado, adaptado para el traslado seguro de perros", 14_500_000),
    ("Capital de trabajo: tres meses de sueldo de una tercera peluquera", 3_500_000),
]
CREDITO = 25_000_000
TASA_MENSUAL = 0.012
PLAZO = 48


def cuota_credito():
    return round(CREDITO * TASA_MENSUAL / (1 - (1 + TASA_MENSUAL) ** -PLAZO))


def rgb(h):
    return PptxRGB.from_string(h.lstrip("#"))


def texto_pptx(lamina, x, y, w, h, texto, tam=14, color=TINTA, negrita=False, fuente="Calibri",
               alinear=PP_ALIGN.LEFT, anclar=MSO_ANCHOR.TOP):
    caja = lamina.shapes.add_textbox(x, y, w, h)
    tf = caja.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anclar
    tf.margin_left = tf.margin_right = 0
    for i, linea in enumerate(texto.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinear
        r = p.add_run()
        r.text = linea
        r.font.size = PPt(tam)
        r.font.bold = negrita
        r.font.name = fuente
        r.font.color.rgb = rgb(color)
    return caja


def rect(lamina, x, y, w, h, color, forma=MSO_SHAPE.RECTANGLE):
    s = lamina.shapes.add_shape(forma, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(color)
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def presentacion(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    W, H = prs.slide_width, prs.slide_height
    vacia = prs.slide_layouts[6]
    total = 6

    def lamina(n, kicker, titulo):
        s = prs.slides.add_slide(vacia)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(PAPEL)
        rect(s, 0, 0, Inches(0.18), H, MORADO)
        texto_pptx(s, Inches(0.8), Inches(0.5), Inches(9), Inches(0.4), kicker.upper(), 12, MORADO, True)
        texto_pptx(s, Inches(0.8), Inches(0.85), Inches(11.5), Inches(0.9), titulo, 32, TINTA, False, "Georgia")
        texto_pptx(s, Inches(0.8), H - Inches(0.55), Inches(8), Inches(0.3),
                   "Lebrel · Solicitud de crédito pyme · Noviembre 2026", 10, NIEBLA)
        texto_pptx(s, W - Inches(1.8), H - Inches(0.55), Inches(1), Inches(0.3), f"{n} / {total}", 10, NIEBLA,
                   alinear=PP_ALIGN.RIGHT)
        return s

    def credito_foto(s, texto):
        texto_pptx(s, Inches(0.8), H - Inches(0.85), Inches(11.5), Inches(0.3), texto, 8, NIEBLA)

    # 1. El negocio
    s = lamina(1, "El negocio", "Lebrel, peluquería y guardería canina")
    s.shapes.add_picture(str(IMG / "hero-borzoi.jpg"), Inches(8.3), Inches(1.9), height=Inches(4.3))
    texto_pptx(s, Inches(0.8), Inches(1.9), Inches(7), Inches(1.6),
               "Desde marzo de 2023 bañamos, cortamos y cuidamos perros en Ñuñoa, con hora reservada y sin "
               "apuros. Si el dueño no alcanza a venir, lo buscamos y se lo devolvemos listo.", 16, TINTA)
    kpis = [("2023", "abrimos en Calle Los Aromos"), ("5", "personas en el equipo"),
            ("389", "clientes distintos en octubre"), ("12", "perros por día en la guardería")]
    for i, (num, desc) in enumerate(kpis):
        x = Inches(0.8) + i * Inches(1.82)
        rect(s, x, Inches(3.75), Inches(1.65), Inches(1.9), LAVANDA)
        texto_pptx(s, x + Inches(0.15), Inches(3.9), Inches(1.4), Inches(0.7), num, 30, MORADO, True, "Georgia")
        texto_pptx(s, x + Inches(0.15), Inches(4.65), Inches(1.4), Inches(0.9), desc, 11, NIEBLA)
    texto_pptx(s, Inches(0.8), Inches(5.95), Inches(7.2), Inches(0.5),
               f"{EMPRESA['razon_social']} · RUT {EMPRESA['rut']} · {EMPRESA['direccion']}, {EMPRESA['comuna']}",
               11, NIEBLA)
    credito_foto(s, "Foto: «Kobold», Deb West, CC BY 2.0, vía Wikimedia Commons.")

    # 2. Servicios
    s = lamina(2, "Servicios", "Cuatro servicios, el mismo cuidado")
    fotos = ["servicio-bano.jpg", "servicio-corte.jpg", "servicio-guarderia.jpg", "servicio-retiro.jpg"]
    for i, ((nombre, desc, precio), foto) in enumerate(zip(datos.PRECIOS, fotos)):
        x = Inches(0.8) + i * Inches(3.0)
        rect(s, x, Inches(1.9), Inches(2.8), Inches(4.5), "#FFFFFF")
        pic = s.shapes.add_picture(str(IMG / foto), x, Inches(1.9), width=Inches(2.8))
        alto_max = Inches(1.9)
        if pic.height > alto_max:  # recorta la foto a la franja superior de la tarjeta
            sobra = (pic.height - alto_max) / pic.height
            pic.crop_top = sobra / 2
            pic.crop_bottom = sobra / 2
            pic.height = alto_max
        texto_pptx(s, x + Inches(0.2), Inches(3.95), Inches(2.4), Inches(0.75), nombre, 15, TINTA, True,
                   anclar=MSO_ANCHOR.BOTTOM)
        texto_pptx(s, x + Inches(0.2), Inches(4.8), Inches(2.4), Inches(1.0), desc, 11, NIEBLA)
        texto_pptx(s, x + Inches(0.2), Inches(5.75), Inches(2.4), Inches(0.5), f"Desde {pesos(precio)}", 18,
                   MORADO, True, "Georgia")
    credito_foto(s, "Fotos vía Wikimedia Commons: Andrew Vargas (CC BY 2.0); Pedrobaba1 (CC BY-SA 4.0); "
                    "Sardaka (CC BY-SA 4.0); Slyronit (CC BY-SA 4.0). Precios de referencia para un perro mediano.")

    # 3. Clientes por mes
    s = lamina(3, "Clientes por mes", "Cada mes atendemos a más perros")
    cd = CategoryChartData()
    cd.categories = MESES
    cd.add_series("Atenciones", ATENCIONES_2026)
    cd.add_series("Clientes distintos", CLIENTES_2026)
    graf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.8), Inches(1.8), Inches(8.4),
                              Inches(4.6), cd).chart
    for serie, color in zip(graf.plots[0].series, (MORADO, CIRUELA)):
        serie.format.fill.solid()
        serie.format.fill.fore_color.rgb = rgb(color)
    graf.plots[0].gap_width = 60
    graf.has_legend = True
    graf.legend.position = XL_LEGEND_POSITION.BOTTOM
    graf.legend.include_in_layout = False
    graf.legend.font.size = PPt(11)
    graf.value_axis.has_major_gridlines = True
    graf.value_axis.major_gridlines.format.line.color.rgb = rgb(LAVANDA_2)
    graf.value_axis.format.line.fill.background()
    graf.value_axis.tick_labels.font.size = PPt(10)
    graf.category_axis.tick_labels.font.size = PPt(11)
    graf.font.color.rgb = rgb(NIEBLA)
    notas = [("+25%", "atenciones en octubre frente a enero"),
             ("95%", "de la capacidad usada en octubre"),
             ("1,6", "atenciones por cliente al mes")]
    for i, (num, desc) in enumerate(notas):
        y = Inches(1.9) + i * Inches(1.5)
        texto_pptx(s, Inches(9.7), y, Inches(3), Inches(0.6), num, 28, MORADO, True, "Georgia")
        texto_pptx(s, Inches(9.7), y + Inches(0.6), Inches(3), Inches(0.6), desc, 12, NIEBLA)
    credito_foto(s, "Enero a octubre de 2026. Atención: un servicio prestado (baño, corte o día de guardería). "
                    "Cifras agregadas del sistema de reservas.")

    # 4. Ingresos
    s = lamina(4, "Ingresos", "Ventas que crecen todos los años")
    cd = CategoryChartData()
    cd.categories = [a for a, _ in INGRESOS]
    cd.add_series("Ventas netas (millones de pesos)", [v for _, v in INGRESOS])
    graf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.8), Inches(1.8), Inches(6.6),
                              Inches(4.6), cd).chart
    graf.has_title = False
    serie = graf.plots[0].series[0]
    serie.format.fill.solid()
    serie.format.fill.fore_color.rgb = rgb(MORADO)
    graf.plots[0].gap_width = 70
    graf.plots[0].has_data_labels = True
    etiquetas = graf.plots[0].data_labels
    etiquetas.number_format = '"$"0" M"'
    etiquetas.number_format_is_linked = False
    etiquetas.position = XL_LABEL_POSITION.OUTSIDE_END
    etiquetas.font.size = PPt(14)
    etiquetas.font.bold = True
    graf.has_legend = False
    graf.value_axis.visible = False
    graf.value_axis.has_major_gridlines = False
    graf.category_axis.tick_labels.font.size = PPt(12)
    graf.font.color.rgb = rgb(NIEBLA)
    mezcla = [("Servicio", "% de ventas 2026"), ("Baño y corte", "41%"), ("Guardería por el día", "37%"),
              ("Baño", "17%"), ("Retiro y entrega", "5%")]
    tab = s.shapes.add_table(len(mezcla), 2, Inches(8.0), Inches(1.9), Inches(4.6), Inches(2.4)).table
    for i, (a, b) in enumerate(mezcla):
        for j, val in enumerate((a, b)):
            celda = tab.cell(i, j)
            celda.text = val
            celda.fill.solid()
            celda.fill.fore_color.rgb = rgb(MORADO if i == 0 else (LAVANDA if i % 2 else "#FFFFFF"))
            par = celda.text_frame.paragraphs[0]
            par.alignment = PP_ALIGN.RIGHT if j == 1 else PP_ALIGN.LEFT
            par.runs[0].font.size = PPt(13)
            par.runs[0].font.bold = i == 0
            par.runs[0].font.color.rgb = rgb("#FFFFFF" if i == 0 else TINTA)
    texto_pptx(s, Inches(8.0), Inches(4.6), Inches(4.6), Inches(1.6),
               "Resultado operacional 2025: $23,6 M (18% de las ventas).\nSin deudas financieras vigentes.\n"
               "Arriendo y sueldos al día.", 13, TINTA)
    credito_foto(s, "* Marzo a diciembre de 2023.  ** Enero a octubre real ($123 M) más proyección de noviembre "
                    "y diciembre. Ventas netas de IVA.")

    # 5. Inversión
    s = lamina(5, "Inversión", "Más espacio para atender a más perros")
    total_inv = sum(m for _, m in INVERSION)
    filas = [("Destino", "Monto")] + [(d, pesos(m)) for d, m in INVERSION] + [("Total del proyecto", pesos(total_inv))]
    tab = s.shapes.add_table(len(filas), 2, Inches(0.8), Inches(1.9), Inches(8.2), Inches(3.6)).table
    tab.columns[0].width = Inches(6.3)
    tab.columns[1].width = Inches(1.9)
    for i, (a, b) in enumerate(filas):
        for j, val in enumerate((a, b)):
            celda = tab.cell(i, j)
            celda.text = val
            celda.fill.solid()
            ultima = i == len(filas) - 1
            celda.fill.fore_color.rgb = rgb(MORADO if i == 0 else (LAVANDA_2 if ultima else "#FFFFFF"))
            par = celda.text_frame.paragraphs[0]
            par.alignment = PP_ALIGN.RIGHT if j == 1 else PP_ALIGN.LEFT
            par.runs[0].font.size = PPt(13)
            par.runs[0].font.bold = i == 0 or ultima
            par.runs[0].font.color.rgb = rgb("#FFFFFF" if i == 0 else TINTA)
    efectos = [("+45%", "capacidad de peluquería"), ("18", "perros por día en la guardería"),
               ("Mar 2027", "todo funcionando")]
    for i, (num, desc) in enumerate(efectos):
        y = Inches(1.9) + i * Inches(1.5)
        texto_pptx(s, Inches(9.7), y, Inches(3), Inches(0.6), num, 28, CIRUELA, True, "Georgia")
        texto_pptx(s, Inches(9.7), y + Inches(0.6), Inches(3), Inches(0.6), desc, 12, NIEBLA)
    credito_foto(s, "Montos con IVA incluido, según cotizaciones de octubre de 2026. El furgón reemplaza el vehículo "
                    "arrendado que hoy usamos para los retiros a domicilio.")

    # 6. Crédito
    s = lamina(6, "Crédito solicitado", "Lo que pedimos")
    aporte = total_inv - CREDITO
    cuota = cuota_credito()
    datos_credito = [("Monto del crédito", pesos(CREDITO)), ("Aporte propio", pesos(aporte)),
                     ("Plazo", f"{PLAZO} meses (3 de gracia)"),
                     ("Cuota estimada", f"{pesos(cuota)} al mes"),
                     ("Garantía", "FOGAPE y aval de la socia")]
    for i, (a, b) in enumerate(datos_credito):
        y = Inches(1.95) + i * Inches(0.78)
        rect(s, Inches(0.8), y, Inches(7.4), Inches(0.66), LAVANDA if i % 2 == 0 else "#FFFFFF")
        texto_pptx(s, Inches(1.0), y, Inches(3.2), Inches(0.66), a, 15, NIEBLA, anclar=MSO_ANCHOR.MIDDLE)
        texto_pptx(s, Inches(4.0), y, Inches(4.1), Inches(0.66), b, 17, TINTA, True, anclar=MSO_ANCHOR.MIDDLE)
    rect(s, Inches(8.8), Inches(1.95), Inches(3.8), Inches(3.78), MORADO)
    venta_mes = round(149_000_000 / 12)
    texto_pptx(s, Inches(9.1), Inches(2.2), Inches(3.3), Inches(0.8), f"{cuota / venta_mes:.1%}".replace(".", ","),
               40, "#FFFFFF", True, "Georgia")
    texto_pptx(s, Inches(9.1), Inches(3.1), Inches(3.3), Inches(2.4),
               "de las ventas mensuales promedio de 2026 se va a la cuota. Con la ampliación, esperamos sumar "
               "unas 200 atenciones al mes.", 14, "#FFFFFF")
    texto_pptx(s, Inches(0.8), Inches(6.0), Inches(11.5), Inches(0.5),
               f"Contacto: {VALENTINA['nombre']}, representante legal · {EMPRESA['correo']} · {EMPRESA['telefono']}",
               13, TINTA)
    credito_foto(s, f"Cuota referencial con tasa de {TASA_MENSUAL:.1%} mensual; la tasa final la fija el banco.".replace(".", ",", 1))

    prs.core_properties.title = "Lebrel · Solicitud de crédito pyme"
    prs.core_properties.author = "Valentina Rojas Fuentes"
    prs.core_properties.last_modified_by = "Valentina Rojas Fuentes"
    prs.core_properties.created = datetime(2026, 10, 28, 20, 15)
    prs.core_properties.modified = datetime(2026, 11, 3, 22, 40)
    prs.save(path)


# ---------------------------------------------------------------- 8. correo de reclamo


def correo_reclamo(path):
    cli = datos.CLIENTE_RECLAMO
    t1 = datetime(2026, 9, 12, 20, 47, 12, tzinfo=CHILE)
    t2 = datetime(2026, 9, 14, 9, 58, 30, tzinfo=CHILE)
    t3 = datetime(2026, 9, 14, 12, 16, 5, tzinfo=CHILE)
    id1 = "<CAK7v2m9Q1xR4pZt8sW3nE6yLh0dFj5uB2cM@mail.correo.example>"
    id2 = "<20260914125830.4f7a1c2e9b3d@lebrel.cl>"
    id3 = "<CAK7v2m9R8wT2kQx1vN5bH3zPe7aGc4yD6sJ@mail.correo.example>"
    original = (
        "Hola,\n\n"
        f"Hoy en la mañana llevé a {cli['perro']}, mi schnauzer, a baño y corte. Les pedí expresamente el corte "
        "clásico de schnauzer, dejándole la barba y las cejas, y me lo entregaron con la barba cortada casi al ras "
        "y una de las cejas dispareja. Además tiene la piel irritada debajo del cuello, se rasca a cada rato.\n\n"
        "Nadie me llamó para consultarme antes de cortarle la barba. Pagué $22.000 por un corte que no es el que "
        "pedí. Quiero saber qué pasó y qué solución me pueden dar.\n\n"
        f"{cli['nombre']}\n"
    )
    respuesta = (
        f"Hola, {cli['nombre'].split()[0]}:\n\n"
        f"Gracias por escribirnos y perdón por la demora; los domingos estamos cerrados. Lamentamos mucho cómo "
        f"le quedó el corte a {cli['perro']}.\n\n"
        "Revisamos lo que pasó con la peluquera que lo atendió: la barba tenía nudos muy apretados cerca de la "
        "piel y decidió cortarla para no tironearlo. Fue la decisión correcta para la piel de él, pero debimos "
        "llamarte antes, como hacemos siempre que hay que cambiar el corte acordado. Eso no ocurrió y es "
        "nuestra responsabilidad.\n\n"
        "Te proponemos lo siguiente:\n"
        "- Te devolvemos el valor del corte ($22.000) hoy mismo, por transferencia.\n"
        f"- Cuando la barba le crezca, en unas seis semanas, le hacemos el corte clásico sin costo.\n"
        "- La irritación probablemente se debe al deslanado de los nudos. Si sigue en dos o tres días, "
        "llévalo a la veterinaria y nosotros nos hacemos cargo del costo de la consulta.\n\n"
        f"Además, dejamos anotado en la reserva de {cli['perro']} que hay que llamarte antes de cambiar "
        "cualquier cosa del corte.\n\n"
        f"Un abrazo,\n{VALENTINA['nombre']}\nLebrel, peluquería y guardería canina\n"
        f"{EMPRESA['direccion']}, {EMPRESA['comuna']} · {EMPRESA['telefono']} · {EMPRESA['web']}\n"
    )
    seguimiento = (
        "Hola, Valentina:\n\n"
        "Gracias por la respuesta y por la devolución, ya me llegó la transferencia. Acepto el corte gratis "
        f"cuando le crezca la barba. {cli['perro']} está mejor, ya casi no se rasca.\n\n"
        "Una sola cosa más: la peluquera le sacó fotos antes y después. No quiero que las suban a Instagram, "
        "por favor bórrenlas.\n\n"
        "Saludos,\n"
        f"{cli['nombre']}\n"
    )

    def citar(texto):
        return "\n".join("> " + linea if linea else ">" for linea in texto.rstrip("\n").split("\n"))

    def dia(t):
        dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
        return f"{dias[t.weekday()]}, {t.day} sept 2026, {t:%H:%M}"

    cuerpo = (
        seguimiento + "\n"
        f"El {dia(t2)}, Lebrel <{EMPRESA['correo']}> escribió:\n"
        + citar(respuesta + "\n" + f"El {dia(t1)}, {cli['nombre']} <{cli['correo']}> escribió:\n" + citar(original))
        + "\n"
    )
    # Cabeceras escritas a mano, como las deja un cliente de correo: una por línea y el nombre en RFC 2047.
    cabeceras = [
        ("From", f"{Header(cli['nombre'], 'utf-8').encode()} <{cli['correo']}>"),
        ("To", f"Lebrel <{EMPRESA['correo']}>"),
        ("Subject", f"Re: Reclamo por el corte de {cli['perro']}"),
        ("Date", format_datetime(t3)),
        ("Message-ID", id3),
        ("In-Reply-To", id2),
        ("References", f"{id1}\n {id2}"),
        ("MIME-Version", "1.0"),
        ("Content-Type", 'text/plain; charset="UTF-8"'),
        ("Content-Transfer-Encoding", "8bit"),
    ]
    texto = "".join(f"{k}: {v}\n" for k, v in cabeceras) + "\n" + cuerpo
    path.write_text(texto, encoding="utf-8")


# ---------------------------------------------------------------- 9. log del sistema de reservas


def log_reservas(path):
    rnd = datos.rng()
    reservas = datos.reservas_octubre()
    t = datetime(2026, 11, 2, 9, 12, 5, 114_000, tzinfo=CHILE)

    def ts():
        nonlocal t
        while True:
            t += timedelta(milliseconds=rnd.randint(3, 180))
            s = t.isoformat(timespec="milliseconds")
            if not datos.PROHIBIDO.search(s):
                return s

    lineas = [
        f"{ts()} INFO  [export] inicio periodo=2026-10 tabla=reservas destino=export/reservas-2026-10.csv usuario=admin",
        f"{ts()} INFO  [db] consulta reservas fecha>=2026-10-01 fecha<=2026-10-31 filas={len(reservas)}",
    ]
    for r in reservas:
        lineas.append(
            f"{ts()} DEBUG [export] fila id={r['id']} fecha={r['fecha'].isoformat()} servicio={r['servicio']} "
            f"nombre=\"{r['nombre']}\" correo={r['correo']} telefono=\"{r['telefono']}\" perro=\"{r['perro']}\" "
            f"retiro={'si' if r['retiro'] else 'no'}" + (f" direccion=\"{r['direccion']}\"" if r["retiro"] else "")
        )
        if r["servicio"] == "guarderia" and len([x for x in lineas if "WARN" in x]) < 2:
            lineas.append(f"{ts()} WARN  [veterinaria] reserva id={r['id']} sin confirmacion_vacunas "
                          f"estado=omitido motivo=\"VETERINARIA_API_KEY no configurada\"")
    tam = sum(len(x) for x in lineas) * 0.62
    lineas.append(f"{ts()} INFO  [export] archivo escrito export/reservas-2026-10.csv filas={len(reservas)} bytes={round(tam)}")
    lineas.append(f"{ts()} INFO  [export] fin estado=ok duracion_ms={rnd.randint(2100, 2900)}")
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 10. lista de precios


def lista_precios(path):
    filas = [["Servicio", "Qué incluye", "Desde"]]
    for nombre, desc, precio in datos.PRECIOS:
        filas.append([Paragraph(f"<b>{nombre}</b>", E["base"]), Paragraph(desc, E["base"]), pesos(precio)])
    t = tabla(filas, [4.6 * cm, 9.6 * cm, 3.3 * cm], [
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("FONT", (2, 1), (2, -1), "Helvetica-Bold", 13),
        ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor(MORADO)),
        ("TOPPADDING", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0, colors.white),
        ("LINEBELOW", (0, 1), (-1, -1), 0.6, colors.HexColor(LAVANDA_2)),
    ])
    nota = ParagraphStyle("nota", parent=E["base"], fontSize=9.5, leading=14)
    titulo = ParagraphStyle("tp", parent=E["base"], fontName="Times-Bold", fontSize=30, leading=34,
                            spaceAfter=6, textColor=colors.HexColor(TINTA))
    cuerpo = [
        Paragraph("PELUQUERÍA Y GUARDERÍA CANINA · ÑUÑOA", ParagraphStyle("k", parent=E["h2"], spaceBefore=0)),
        Paragraph("Lista de precios 2026", titulo),
        Paragraph("Vigente desde el 2 de marzo de 2026. Valores en pesos chilenos, IVA incluido.", E["chico"]),
        Spacer(1, 18),
        t,
        Spacer(1, 18),
        Paragraph("Bueno saber", E["h2"]),
        Paragraph("• Son precios de referencia para un perro mediano. Te confirmamos el valor final según el "
                  "tamaño y el tipo de pelo antes de atender a tu perro.", nota),
        Paragraph("• Para la guardería pedimos las vacunas al día (antirrábica, óctuple y tos de las perreras): "
                  "así cuidamos a todo el grupo.", nota),
        Paragraph("• El retiro y la entrega a domicilio se suman a cualquier servicio. Recorridos por Ñuñoa, "
                  "Providencia y La Reina.", nota),
        Paragraph("• Si hay que cambiar el corte acordado, por ejemplo por nudos, te llamamos antes.", nota),
        Spacer(1, 22),
    ]
    contacto = Table([[
        Paragraph(f"<b>Reserva en {EMPRESA['web']}</b><br/>Te confirmamos la hora por teléfono o por correo.", E["base"]),
        Paragraph(f"<b>{EMPRESA['direccion']}, {EMPRESA['comuna']}</b><br/>{EMPRESA['horario']}<br/>"
                  f"{EMPRESA['telefono']}", E["base"]),
    ]], colWidths=[8.75 * cm, 8.75 * cm])
    contacto.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(LAVANDA)),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    cuerpo.append(contacto)
    pdf(path, "Lista de precios 2026 · Lebrel", "Lebrel", "Lista de precios", cuerpo,
        "Lista de precios 2026 · lebrel.cl")


# ---------------------------------------------------------------- 11. entrevista

HABLANTES = {"F": "Francisca Morales", "V": "Valentina Rojas"}
PALABRAS_POR_SEGUNDO = 2.6
PAUSA_SEGUNDOS = 1


def turnos_entrevista():
    texto = (Path(__file__).resolve().parent / "entrevista.txt").read_text(encoding="utf-8")
    turnos = []
    for bloque in texto.split("\n\n"):
        bloque = "\n".join(x for x in bloque.splitlines() if not x.startswith("#")).strip()
        if bloque:
            quien, dicho = bloque.split(": ", 1)
            turnos.append((HABLANTES[quien], dicho))
    segundos, marcados = 0, []
    for quien, dicho in turnos:
        marca = f"{segundos // 60:02d}:{segundos % 60:02d}"
        while datos.PROHIBIDO.search(marca):  # evita una marca que coincida con el barrido
            segundos += 1
            marca = f"{segundos // 60:02d}:{segundos % 60:02d}"
        marcados.append((marca, quien, dicho))
        segundos += round(len(dicho.split()) / PALABRAS_POR_SEGUNDO) + PAUSA_SEGUNDOS
    return marcados, segundos


def entrevista(path):
    turnos, duracion = turnos_entrevista()
    d = nuevo_docx("Transcripción entrevista de procesos · Lebrel", "Francisca Morales",
                   datetime(2026, 10, 23, 10, 5), "Privai · Levantamiento de procesos · Peluquería Canina Lebrel SpA")
    centrado(d, "Transcripción de entrevista", 18, True, 2, TINTA)
    centrado(d, "Levantamiento de procesos para el Registro de Actividades de Tratamiento (RAT)", 11, False, 14, NIEBLA)
    meta = [
        ("Empresa", f"{EMPRESA['razon_social']} (Lebrel, peluquería y guardería canina)"),
        ("Fecha", "Jueves 22 de octubre de 2026, 15:30 horas"),
        ("Lugar", f"Oficina del local, {EMPRESA['direccion']}, {EMPRESA['comuna']} (presencial)"),
        ("Duración", f"{duracion // 60} minutos {duracion % 60} segundos"),
        ("Entrevistada", "Valentina Rojas Fuentes, dueña y representante legal de Lebrel"),
        ("Entrevistadora", "Francisca Morales, consultora de privacidad de Privai"),
    ]
    t = d.add_table(rows=len(meta), cols=2)
    t.style = "Table Grid"
    t.autofit = False
    for col, ancho in zip(t.columns, (Cm(3.6), Cm(13))):
        col.width = ancho
    for fila, (a, b) in zip(t.rows, meta):
        fila.cells[0].width, fila.cells[1].width = Cm(3.6), Cm(13)
        fila.cells[0].text, fila.cells[1].text = a, b
        fila.cells[0].paragraphs[0].runs[0].bold = True
        sombrear(fila.cells[0], LAVANDA)
        for celda in fila.cells:
            celda.paragraphs[0].paragraph_format.space_after = Pt(2)
            celda.paragraphs[0].runs[0].font.size = Pt(10)
    nota = d.add_paragraph()
    nota.paragraph_format.space_before = Pt(10)
    r = nota.add_run(
        "Transcripción revisada a partir de la grabación de audio, con el consentimiento de ambas participantes. "
        "Se omitieron muletillas y repeticiones para facilitar la lectura. La conversación es general sobre los "
        "procesos de la empresa y no incluye datos de clientes ni de trabajadores. La grabación se eliminará una "
        "vez aprobado el registro.")
    r.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = RGBColor.from_string(NIEBLA[1:])
    d.add_heading("Transcripción", level=1)
    for marca, quien, dicho in turnos:
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run(f"[{marca}] ")
        r.font.name = "Consolas"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor.from_string(NIEBLA[1:])
        r = p.add_run(f"{quien}: ")
        r.bold = True
        r.font.color.rgb = RGBColor.from_string((MORADO if quien.startswith("Francisca") else CIRUELA)[1:])
        p.add_run(dicho)
    fin = d.add_paragraph()
    fin.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fin.paragraph_format.space_before = Pt(12)
    r = fin.add_run(f"[{duracion // 60:02d}:{duracion % 60:02d}] Fin de la grabación.")
    r.italic = True
    r.font.color.rgb = RGBColor.from_string(NIEBLA[1:])
    d.save(path)


# ----------------------------------------------------------------

DOCUMENTOS = [
    ("contrato-arriendo-local.docx", contrato_arriendo),
    ("contrato-trabajo-camila-soto.docx", contrato_trabajo),
    ("liquidacion-sueldo-camila-soto-2026-10.pdf", liquidacion),
    ("convenio-veterinaria-los-aromos.pdf", convenio),
    ("clientes-y-reservas-2026.xlsx", planilla_clientes),
    ("ficha-guarderia-bruno.pdf", ficha_bruno),
    ("presentacion-credito-banco.pptx", presentacion),
    ("reclamo-cliente-2026-09-14.eml", correo_reclamo),
    ("sistema-reservas-export-2026-10.log", log_reservas),
    ("lista-de-precios-2026.pdf", lista_precios),
    ("entrevista-procesos-lebrel.docx", entrevista),
]


def main():
    DRIVE.mkdir(exist_ok=True)
    for nombre, generar in DOCUMENTOS:
        generar(DRIVE / nombre)
        print(f"escrito drive/{nombre}")


if __name__ == "__main__":
    main()
