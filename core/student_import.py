import contextlib
import math
import os
import unicodedata
from collections import defaultdict
from html import escape
from io import BytesIO

import segno
from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import Grade, Section, Student

MAX_STUDENT_IMPORT_ROWS = 2000

HEADER_ALIASES = {
    "dni": {"dni"},
    "first_name": {"nombres", "nombre"},
    "last_name": {"apellidos", "apellido"},
    "grade": {"grado"},
    "section": {"seccion"},
    "guardian_phone": {
        "telefono del apoderado",
        "telefono apoderado",
        "celular del apoderado",
        "celular apoderado",
        "telefono del tutor",
        "telefono tutor",
    },
}


class StudentImportError(Exception):
    def __init__(self, errors, detail="Corrige los datos del archivo y vuelve a importarlo."):
        self.errors = errors
        self.detail = detail
        super().__init__(detail)


def _normalized_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in text).split())


def _cell_text(value):
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _get_headers(sheet):
    header_cells = next(sheet.iter_rows(min_row=1, max_row=1), ())
    normalized_headers = [_normalized_text(cell.value) for cell in header_cells]
    indexes = {}
    errors = []
    for field, aliases in HEADER_ALIASES.items():
        matching = [index for index, header in enumerate(normalized_headers) if header in aliases]
        if not matching:
            errors.append(
                {
                    "row": 1,
                    "field": field,
                    "message": f"Falta la columna obligatoria: {field.replace('_', ' ')}.",
                }
            )
        elif len(matching) > 1:
            errors.append(
                {
                    "row": 1,
                    "field": field,
                    "message": "La columna aparece más de una vez.",
                }
            )
        else:
            indexes[field] = matching[0]
    return indexes, errors


def _dni_text(value):
    text = _cell_text(value).replace(" ", "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if text.isdigit() and len(text) < 8:
            text = text.zfill(8)
    return text


def parse_and_validate_student_workbook(upload, school_id, target_section):
    try:
        workbook = load_workbook(upload, read_only=True, data_only=True)
    except (InvalidFileException, OSError, ValueError, TypeError):
        raise StudentImportError(
            [{"row": 0, "field": "file", "message": "El archivo no es un Excel .xlsx válido."}],
            "No se pudo leer el archivo.",
        )

    try:
        sheet = workbook.active
        indexes, errors = _get_headers(sheet)
        if errors:
            raise StudentImportError(errors)

        grades = list(Grade.all_objects.filter(colegio_id=school_id))
        sections = list(
            Section.all_objects.filter(colegio_id=school_id).select_related("grade")
        )
        grade_by_name = {_normalized_text(grade.name): grade for grade in grades}
        section_by_names = {
            (_normalized_text(section.grade.name), _normalized_text(section.name)): section
            for section in sections
        }

        parsed_rows = []
        seen_dnis = {}
        nonempty_rows = 0
        for row_number, cells in enumerate(sheet.iter_rows(min_row=2), start=2):
            values = {
                field: _cell_text(cells[index].value if index < len(cells) else None)
                for field, index in indexes.items()
            }
            if not any(values.values()):
                continue
            nonempty_rows += 1
            if nonempty_rows > MAX_STUDENT_IMPORT_ROWS:
                errors.append(
                    {
                        "row": row_number,
                        "field": "file",
                        "message": f"El archivo supera el límite de {MAX_STUDENT_IMPORT_ROWS} estudiantes.",
                    }
                )
                break

            dni = _dni_text(cells[indexes["dni"]].value if indexes["dni"] < len(cells) else None)
            values["dni"] = dni
            row_has_error = False
            for field, value in values.items():
                if not value:
                    errors.append(
                        {
                            "row": row_number,
                            "field": field,
                            "message": "Este dato es obligatorio.",
                        }
                    )
                    row_has_error = True
            if dni and (len(dni) != 8 or not dni.isdigit()):
                errors.append(
                    {
                        "row": row_number,
                        "field": "dni",
                        "message": "El DNI debe tener exactamente 8 dígitos.",
                    }
                )
                row_has_error = True
            elif dni in seen_dnis:
                errors.append(
                    {
                        "row": row_number,
                        "field": "dni",
                        "message": f"El DNI está repetido en la fila {seen_dnis[dni]} del archivo.",
                    }
                )
                row_has_error = True
            else:
                seen_dnis[dni] = row_number

            grade = grade_by_name.get(_normalized_text(values["grade"]))
            section = section_by_names.get(
                (_normalized_text(values["grade"]), _normalized_text(values["section"]))
            )
            if grade is None:
                errors.append(
                    {
                        "row": row_number,
                        "field": "grade",
                        "message": f"No existe el grado «{values['grade']}» en este colegio.",
                    }
                )
                row_has_error = True
            elif section is None:
                errors.append(
                    {
                        "row": row_number,
                        "field": "section",
                        "message": (
                            f"No existe la sección «{values['section']}» "
                            f"para el grado «{values['grade']}»."
                        ),
                    }
                )
                row_has_error = True
            elif section.id != target_section.id:
                errors.append(
                    {
                        "row": row_number,
                        "field": "section",
                        "message": (
                            "Esta fila no pertenece a la sección abierta. "
                            "Importa cada sección desde su propia pantalla."
                        ),
                    }
                )
                row_has_error = True
            elif grade.id != section.grade_id:
                errors.append(
                    {
                        "row": row_number,
                        "field": "grade",
                        "message": "El grado no corresponde a la sección indicada.",
                    }
                )
                row_has_error = True

            if not row_has_error:
                parsed_rows.append(
                    {
                        "row": row_number,
                        "dni": dni,
                        "first_name": values["first_name"],
                        "last_name": values["last_name"],
                        "grade": grade,
                        "section": section,
                        "guardian_phone": values["guardian_phone"],
                    }
                )

        if nonempty_rows == 0:
            errors.append(
                {
                    "row": 2,
                    "field": "file",
                    "message": "El archivo no contiene estudiantes.",
                }
            )
        if errors:
            raise StudentImportError(errors[:100])
        return parsed_rows
    finally:
        workbook.close()


@transaction.atomic
def import_students_from_workbook(upload, school_id, target_section):
    rows = parse_and_validate_student_workbook(upload, school_id, target_section)
    existing_students = {
        student.dni: student
        for student in Student.all_objects.select_for_update().filter(
            colegio_id=school_id,
            dni__in=[row["dni"] for row in rows],
        )
    }

    errors = []
    for row in rows:
        existing = existing_students.get(row["dni"])
        if existing and existing.section_id != target_section.id:
            errors.append(
                {
                    "row": row["row"],
                    "field": "dni",
                    "message": (
                        "Este DNI ya está registrado en otra sección. "
                        "Solicita a dirección que realice el cambio."
                    ),
                }
            )
    if errors:
        raise StudentImportError(errors)

    created = 0
    updated = 0
    existing_count = 0
    qr_preserved = 0
    for row in rows:
        student = existing_students.get(row["dni"])
        if student is None:
            student = Student.all_objects.create(
                colegio_id=school_id,
                dni=row["dni"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                grade=row["grade"],
                section=row["section"],
                guardian_phone=row["guardian_phone"],
            )
            created += 1
            continue

        existing_count += 1
        qr_preserved += 1
        changed_fields = []
        for field in ("first_name", "last_name", "guardian_phone"):
            if getattr(student, field) != row[field]:
                setattr(student, field, row[field])
                changed_fields.append(field)
        if changed_fields:
            student.save(update_fields=changed_fields)
            updated += 1

    return {
        "total": len(rows),
        "created": created,
        "updated": updated,
        "existing": existing_count,
        "qrPreserved": qr_preserved,
    }


def _chunks(values, size):
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def render_student_cards_pdf(students, school_name):
    card_pages = []
    for page_students in _chunks(students, 8):
        cards = []
        for student in page_students:
            qr_svg = segno.make(student.qr_token, error="M", micro=False).svg_inline(
                scale=4,
                dark="#34206A",
                light="#FFFFFF",
                border=2,
            )
            cards.append(
                f"""
                <article class="card">
                  <span class="crop crop-tl"></span><span class="crop crop-tr"></span>
                  <span class="crop crop-bl"></span><span class="crop crop-br"></span>
                  <div class="card-head"><span class="brand-mark">E</span>
                    <span><strong>EduCheck</strong><small>{escape(school_name)}</small></span>
                  </div>
                  <div class="card-body">
                    <div class="student-data">
                      <small>CARNET DE ESTUDIANTE</small>
                      <strong class="name">{escape(student.first_name)} {escape(student.last_name)}</strong>
                      <span><b>DNI:</b> {escape(student.dni)}</span>
                      <span><b>Grado:</b> {escape(student.grade.name)}</span>
                      <span><b>Sección:</b> {escape(student.section.name)}</span>
                      <span><b>Apoderado:</b> {escape(student.guardian_phone)}</span>
                    </div>
                    <div class="qr">{qr_svg}</div>
                  </div>
                  <footer>Presenta este carnet para registrar tu asistencia</footer>
                </article>
                """
            )
        card_pages.append(f'<section class="sheet">{"".join(cards)}</section>')

    document = f"""<!doctype html>
    <html lang="es"><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 0; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; color: #241650; font-family: sans-serif; }}
      .sheet {{ width: 210mm; height: 297mm; display: grid;
        grid-template-columns: repeat(2, 85.6mm); grid-template-rows: repeat(4, 54mm);
        gap: 3mm 4mm; place-content: center; page-break-after: always; }}
      .sheet:last-child {{ page-break-after: auto; }}
      .card {{ position: relative; width: 85.6mm; height: 54mm; padding: 3.5mm;
        border: .2mm dashed #8d7cae; border-radius: 2mm; overflow: visible;
        display: flex; flex-direction: column; background: #fff; }}
      .card-head {{ display: flex; align-items: center; gap: 2mm; border-bottom: .2mm solid #e3dbf3; padding-bottom: 2mm; }}
      .brand-mark {{ width: 7mm; height: 7mm; display: grid; place-items: center;
        border-radius: 1.5mm; color: #fff; background: #34206a; font-weight: 700; }}
      .card-head strong, .card-head small {{ display: block; }}
      .card-head strong {{ font-size: 9pt; }}
      .card-head small {{ max-width: 58mm; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
        margin-top: .4mm; color: #6e6590; font-size: 6.5pt; }}
      .card-body {{ min-height: 0; flex: 1; display: flex; align-items: center; justify-content: space-between; gap: 2mm; }}
      .student-data {{ min-width: 0; display: flex; flex-direction: column; gap: 1.1mm; font-size: 7pt; }}
      .student-data > small {{ color: #6743a5; font-size: 5.5pt; font-weight: 700; letter-spacing: .5pt; }}
      .student-data .name {{ max-width: 52mm; overflow: hidden; font-size: 9pt; line-height: 1.15; }}
      .student-data span {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
      .qr {{ width: 25mm; height: 25mm; flex: 0 0 25mm; }}
      .qr svg {{ display: block; width: 25mm; height: 25mm; }}
      footer {{ border-top: .2mm solid #e3dbf3; padding-top: 1.2mm; color: #6e6590; font-size: 5.4pt; }}
      .crop {{ position: absolute; z-index: 2; width: 2mm; height: 2mm; }}
      .crop-tl {{ top: -1mm; left: -1mm; border-top: .25mm solid #34206a; border-left: .25mm solid #34206a; }}
      .crop-tr {{ top: -1mm; right: -1mm; border-top: .25mm solid #34206a; border-right: .25mm solid #34206a; }}
      .crop-bl {{ bottom: -1mm; left: -1mm; border-bottom: .25mm solid #34206a; border-left: .25mm solid #34206a; }}
      .crop-br {{ bottom: -1mm; right: -1mm; border-bottom: .25mm solid #34206a; border-right: .25mm solid #34206a; }}
    </style><body>{"".join(card_pages)}</body></html>"""
    dll_directory = os.environ.get("WEASYPRINT_DLL_DIRECTORY")
    dll_directory_context = (
        os.add_dll_directory(dll_directory)
        if os.name == "nt" and dll_directory
        else contextlib.nullcontext()
    )
    with dll_directory_context:
        from weasyprint import HTML

        return HTML(string=document).write_pdf()
