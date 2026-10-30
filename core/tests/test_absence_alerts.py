from datetime import date, datetime, timedelta, timezone as dt_timezone

import pytest
from django.test import Client

from core.models import Account, AttendanceRecord, Grade, School, Section, Student


def make_school(name="Colegio Alertas"):
    school = School.objects.create(name=name)
    director = Account.objects.create_user(
        username=f"dir-{school.id}",
        password="Alertas-Test-Password-2026",
        role=Account.Role.DIRECTOR,
        colegio=school,
    )
    grade = Grade.all_objects.create(colegio=school, name="3.° secundaria")
    section = Section.all_objects.create(colegio=school, grade=grade, name="A")
    return school, director, grade, section


def make_student(school, grade, section, dni, name="Ana"):
    student = Student.all_objects.create(
        colegio=school,
        dni=dni,
        first_name=name,
        last_name="Quispe",
        grade=grade,
        section=section,
        guardian_phone="900000000",
    )
    Student.all_objects.filter(pk=student.pk).update(
        created_at=datetime(2020, 1, 1, tzinfo=dt_timezone.utc)
    )
    student.refresh_from_db()
    return student


def mark(student, director, day):
    AttendanceRecord.all_objects.create(
        colegio=student.colegio,
        student=student,
        attended_by=director,
        date=day,
        time=datetime.combine(day, datetime.min.time(), tzinfo=dt_timezone.utc),
        shift=AttendanceRecord.Shift.MORNING,
        source=AttendanceRecord.Source.QR,
    )


DAYS = [date(2026, 10, 5) + timedelta(days=index) for index in range(4)]


@pytest.mark.django_db
def test_director_sees_students_with_consecutive_absences_and_filters():
    school, director, grade, section = make_school()
    absent = make_student(school, grade, section, "11111111", "Ausente")
    regular = make_student(school, grade, section, "22222222", "Regular")
    intermittent = make_student(school, grade, section, "33333333", "Intermitente")
    for day in DAYS:
        mark(regular, director, day)
    mark(absent, director, DAYS[0])
    mark(intermittent, director, DAYS[-1])

    client = Client()
    client.force_login(director)
    response = client.get("/api/educheck/director/alerts")

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["threshold"] == 3 and body["recordedDays"] == 4
    assert [item["dni"] for item in body["alerts"]] == ["11111111"]
    alert = body["alerts"][0]
    assert alert["consecutiveAbsences"] == 3
    assert alert["absentSince"] == DAYS[1].isoformat()
    assert alert["lastAttendanceDate"] == DAYS[0].isoformat()
    assert client.get(f"/api/educheck/director/alerts?gradeId={grade.id}").json()["alerts"] == body["alerts"]
    assert client.get(f"/api/educheck/director/alerts?sectionId={section.id}").json()["alerts"] == body["alerts"]


@pytest.mark.django_db
def test_threshold_can_be_changed_and_is_validated():
    school, director, grade, section = make_school()
    student = make_student(school, grade, section, "11111111")
    other = make_student(school, grade, section, "22222222", "Otra")
    for day in DAYS:
        mark(other, director, day)
    mark(student, director, DAYS[0])
    mark(student, director, DAYS[1])

    client = Client()
    client.force_login(director)
    assert client.get("/api/educheck/director/alerts?threshold=3").json()["alerts"] == []
    assert len(client.get("/api/educheck/director/alerts?threshold=2").json()["alerts"]) == 1
    assert client.get("/api/educheck/director/alerts?threshold=1").status_code == 400
    assert client.get("/api/educheck/director/alerts?threshold=abc").status_code == 400


@pytest.mark.django_db
def test_absences_before_enrollment_do_not_count():
    school, director, grade, section = make_school()
    present = make_student(school, grade, section, "22222222", "Presente")
    for day in DAYS:
        mark(present, director, day)
    newcomer = Student.all_objects.create(
        colegio=school,
        dni="11111111",
        first_name="Nuevo",
        last_name="Quispe",
        grade=grade,
        section=section,
        guardian_phone="900000000",
    )
    Student.all_objects.filter(pk=newcomer.pk).update(
        created_at=datetime.combine(DAYS[-1], datetime.min.time(), tzinfo=dt_timezone.utc)
        + timedelta(hours=14)
    )

    client = Client()
    client.force_login(director)
    assert client.get("/api/educheck/director/alerts").json()["alerts"] == []


@pytest.mark.django_db
def test_alerts_are_isolated_by_school_and_forbidden_for_assistants():
    school, director, grade, section = make_school()
    student = make_student(school, grade, section, "11111111")
    for index, day in enumerate(DAYS):
        other = make_student(school, grade, section, f"9999999{index}", "Otro")
        mark(other, director, day)

    client = Client()
    client.force_login(director)
    assert "11111111" in [
        item["dni"] for item in client.get("/api/educheck/director/alerts").json()["alerts"]
    ]

    _other_school, other_director, *_ = make_school("Otro colegio")
    other_client = Client()
    other_client.force_login(other_director)
    assert other_client.get("/api/educheck/director/alerts").json()["alerts"] == []

    assistant = Account.objects.create_user(
        username="auxiliar-alertas",
        password="Alertas-Test-Password-2026",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    assistant_client = Client()
    assistant_client.force_login(assistant)
    assert assistant_client.get("/api/educheck/director/alerts").status_code == 403
