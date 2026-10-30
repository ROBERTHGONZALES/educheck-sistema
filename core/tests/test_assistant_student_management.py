from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from openpyxl import Workbook

from core.models import (
    Account,
    AssistantSectionAssignment,
    Grade,
    School,
    Section,
    Student,
)


def setup_school():
    school = School.objects.create(name="Colegio Prueba")
    director = Account.objects.create_user(
        username="directora-prueba",
        password="Clave-Segura-2026!",
        first_name="Directora",
        role=Account.Role.DIRECTOR,
        colegio=school,
    )
    grade = Grade.all_objects.create(colegio=school, name="1.° primaria")
    section_a = Section.all_objects.create(colegio=school, grade=grade, name="A")
    section_b = Section.all_objects.create(colegio=school, grade=grade, name="B")
    return school, director, grade, section_a, section_b


def workbook_upload(rows, filename="estudiantes.xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "DNI",
            "Nombres",
            "Apellidos",
            "Grado",
            "Sección",
            "Teléfono del apoderado",
        ]
    )
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return SimpleUploadedFile(
        filename,
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
def test_director_creates_assistant_with_sections_and_can_change_assignments():
    school, director, _grade, section_a, section_b = setup_school()
    client = Client()
    client.force_login(director)

    response = client.post(
        "/api/educheck/director/assistants",
        data={
            "username": "auxiliar-nuevo",
            "fullName": "Ana Rivera",
            "password": "Apoyo!Seguro2026-Lima",
            "sectionIds": [section_a.id],
        },
        content_type="application/json",
    )

    assert response.status_code == 201, response.content
    assistant_id = response.json()["id"]
    assistant = Account.objects.get(pk=assistant_id, colegio=school)
    assert assistant.role == Account.Role.ASSISTANT
    assert response.json()["sections"][0]["id"] == section_a.id
    assert AssistantSectionAssignment.all_objects.filter(
        assistant=assistant,
        section=section_a,
    ).exists()

    update = client.put(
        f"/api/educheck/director/assistants/{assistant_id}/sections",
        data={"sectionIds": [section_b.id]},
        content_type="application/json",
    )
    assert update.status_code == 200, update.content
    assert [section["id"] for section in update.json()["sections"]] == [section_b.id]

    listing = client.get("/api/educheck/director/assistants")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [assistant_id]


@pytest.mark.django_db
def test_assistant_only_sees_and_imports_into_assigned_section():
    school, _director, grade, section_a, section_b = setup_school()
    assistant = Account.objects.create_user(
        username="auxiliar-a",
        password="Clave-Segura-2026!",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    AssistantSectionAssignment.all_objects.create(
        colegio=school,
        assistant=assistant,
        section=section_a,
    )
    Student.all_objects.create(
        colegio=school,
        dni="10000001",
        first_name="Luis",
        last_name="Aula A",
        grade=grade,
        section=section_a,
        guardian_phone="999111222",
    )
    Student.all_objects.create(
        colegio=school,
        dni="10000002",
        first_name="Eva",
        last_name="Aula B",
        grade=grade,
        section=section_b,
        guardian_phone="999111333",
    )

    client = Client()
    client.force_login(assistant)
    assigned = client.get("/api/educheck/assistant/sections")
    assert assigned.status_code == 200
    assert [section["id"] for section in assigned.json()] == [section_a.id]
    assert assigned.json()[0]["studentCount"] == 1

    students = client.get(f"/api/educheck/assistant/sections/{section_a.id}/students")
    assert students.status_code == 200
    assert [student["dni"] for student in students.json()] == ["10000001"]
    assert client.get(
        f"/api/educheck/assistant/sections/{section_b.id}/students"
    ).status_code == 404


@pytest.mark.django_db
def test_reimport_updates_existing_student_without_changing_qr():
    school, _director, _grade, section, _other = setup_school()
    assistant = Account.objects.create_user(
        username="auxiliar-importa",
        password="Clave-Segura-2026!",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    AssistantSectionAssignment.all_objects.create(
        colegio=school,
        assistant=assistant,
        section=section,
    )
    client = Client()
    client.force_login(assistant)
    url = f"/api/educheck/assistant/sections/{section.id}/students/import"

    first = client.post(
        url,
        {"file": workbook_upload([["00123456", "Ana", "Pérez", "1.° primaria", "A", "999111222"]])},
    )
    assert first.status_code == 200, first.content
    assert first.json() == {
        "total": 1,
        "created": 1,
        "updated": 0,
        "existing": 0,
        "qrPreserved": 0,
    }
    student = Student.all_objects.get(colegio=school, dni="00123456")
    original_qr = student.qr_token

    second = client.post(
        url,
        {"file": workbook_upload([["00123456", "Ana María", "Pérez", "1.° primaria", "A", "999000111"]])},
    )
    assert second.status_code == 200, second.content
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 1
    assert second.json()["existing"] == 1
    assert second.json()["qrPreserved"] == 1
    student.refresh_from_db()
    assert student.first_name == "Ana María"
    assert student.guardian_phone == "999000111"
    assert student.qr_token == original_qr
    assert Student.all_objects.filter(colegio=school, dni="00123456").count() == 1


@pytest.mark.django_db
def test_invalid_duplicate_or_out_of_section_rows_save_nothing():
    school, _director, _grade, section_a, _section_b = setup_school()
    assistant = Account.objects.create_user(
        username="auxiliar-valida",
        password="Clave-Segura-2026!",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    AssistantSectionAssignment.all_objects.create(
        colegio=school,
        assistant=assistant,
        section=section_a,
    )
    client = Client()
    client.force_login(assistant)
    url = f"/api/educheck/assistant/sections/{section_a.id}/students/import"

    duplicate_file = workbook_upload(
        [
            ["20000001", "Ana", "Uno", "1.° primaria", "A", "999111222"],
            ["20000001", "Eva", "Dos", "1.° primaria", "A", "999111333"],
        ]
    )
    duplicate_response = client.post(url, {"file": duplicate_file})
    assert duplicate_response.status_code == 400
    assert any(error["field"] == "dni" for error in duplicate_response.json()["errors"])
    assert not Student.all_objects.filter(colegio=school).exists()

    wrong_section = workbook_upload(
        [["20000002", "Luis", "Fuera", "1.° primaria", "B", "999111444"]]
    )
    section_response = client.post(url, {"file": wrong_section})
    assert section_response.status_code == 400
    assert "sección abierta" in section_response.json()["errors"][0]["message"]
    assert not Student.all_objects.filter(colegio=school).exists()


@pytest.mark.django_db
def test_assistant_can_download_pdf_with_cards_and_unassigned_section_is_denied():
    school, _director, grade, section_a, section_b = setup_school()
    assistant = Account.objects.create_user(
        username="auxiliar-pdf",
        password="Clave-Segura-2026!",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    AssistantSectionAssignment.all_objects.create(
        colegio=school,
        assistant=assistant,
        section=section_a,
    )
    Student.all_objects.create(
        colegio=school,
        dni="30000001",
        first_name="María",
        last_name="López",
        grade=grade,
        section=section_a,
        guardian_phone="999111555",
    )
    client = Client()
    client.force_login(assistant)

    pdf_response = client.get(f"/api/educheck/assistant/sections/{section_a.id}/cards.pdf")
    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert client.get(
        f"/api/educheck/assistant/sections/{section_b.id}/cards.pdf"
    ).status_code == 404
