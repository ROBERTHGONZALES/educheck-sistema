import pytest
from django.test import Client

from core.models import Account, Grade, School, Section, Student
from core.tenant_context import current_school_id


@pytest.mark.django_db
def test_tenant_manager_filters_by_authenticated_school():
    school_one = School.objects.create(name="Colegio Norte")
    school_two = School.objects.create(name="Colegio Sur")
    Grade.all_objects.create(colegio=school_one, name="1.°")
    Grade.all_objects.create(colegio=school_two, name="1.°")

    token = current_school_id.set(school_one.id)
    try:
        assert list(Grade.objects.values_list("colegio_id", flat=True)) == [school_one.id]
    finally:
        current_school_id.reset(token)

    token = current_school_id.set(school_two.id)
    try:
        assert list(Grade.objects.values_list("colegio_id", flat=True)) == [school_two.id]
    finally:
        current_school_id.reset(token)


@pytest.mark.django_db
def test_director_api_never_returns_students_from_another_school():
    school_one = School.objects.create(name="Colegio Norte")
    school_two = School.objects.create(name="Colegio Sur")
    director = Account.objects.create_user(
        username="director-norte",
        password="Clave-Segura-2026!",
        role=Account.Role.DIRECTOR,
        colegio=school_one,
    )
    grade_one = Grade.all_objects.create(colegio=school_one, name="1.°")
    section_one = Section.all_objects.create(colegio=school_one, grade=grade_one, name="A")
    Student.all_objects.create(
        colegio=school_one,
        dni="10000001",
        first_name="Ana",
        last_name="Norte",
        grade=grade_one,
        section=section_one,
        guardian_phone="999111222",
    )

    grade_two = Grade.all_objects.create(colegio=school_two, name="1.°")
    section_two = Section.all_objects.create(colegio=school_two, grade=grade_two, name="A")
    Student.all_objects.create(
        colegio=school_two,
        dni="20000002",
        first_name="Luis",
        last_name="Sur",
        grade=grade_two,
        section=section_two,
        guardian_phone="999333444",
    )

    client = Client()
    client.force_login(director)
    response = client.get("/api/educheck/director/students")

    assert response.status_code == 200
    assert [student["dni"] for student in response.json()] == ["10000001"]


@pytest.mark.django_db
def test_assistant_cannot_access_director_student_management():
    school = School.objects.create(name="Colegio Auxiliar")
    assistant = Account.objects.create_user(
        username="auxiliar",
        password="Clave-Segura-2026!",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    client = Client()
    client.force_login(assistant)

    response = client.get("/api/educheck/director/students")

    assert response.status_code == 403
