"""Datos de demostración para la instancia local de EduCheck."""
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "educheck_project.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Account, AttendanceRecord, Grade, School, Section, Student
from core.tenant_context import current_school_id

random.seed(7)

school, _ = School.objects.get_or_create(name="Colegio Demo EduCheck")
current_school_id.set(school.pk)

Account_obj = get_user_model()

if not Account_obj.objects.filter(username="auxiliar").exists():
    auxiliar = Account_obj(
        username="auxiliar",
        first_name="Auxiliar",
        last_name="Demo",
        role=Account.Role.ASSISTANT,
        colegio=school,
    )
    auxiliar.set_password("EduCheck2026!")
    auxiliar.save()
    print("auxiliar creado")
else:
    auxiliar = Account_obj.objects.get(username="auxiliar")

director = Account_obj.objects.get(username="director")

grados = {
    "1° Primaria": ["A", "B"],
    "2° Primaria": ["A", "B"],
    "3° Primaria": ["A"],
}

nombres = [
    ("Ana", "Quispe Ramos"), ("Luis", "Huamán Torres"), ("María", "Flores Díaz"),
    ("Jorge", "Salazar Vega"), ("Rosa", "Ccahuana Lima"), ("Diego", "Mendoza Ríos"),
    ("Camila", "Paredes Soto"), ("Mateo", "Chávez Núñez"), ("Valeria", "Rojas Pinto"),
    ("Sebastián", "Vargas León"), ("Lucía", "Torres Aquino"), ("Adrián", "Ramos Córdova"),
]

secciones = []
for grado_nombre, seccion_nombres in grados.items():
    grado, _ = Grade.objects.get_or_create(colegio=school, name=grado_nombre)
    for seccion_nombre in seccion_nombres:
        seccion, _ = Section.objects.get_or_create(
            colegio=school, grade=grado, name=seccion_nombre
        )
        secciones.append(seccion)

dni_base = 70000000
indice = 0
for seccion in secciones:
    for _ in range(6):
        nombre, apellido = nombres[indice % len(nombres)]
        dni = str(dni_base + indice)
        Student.objects.get_or_create(
            colegio=school,
            dni=dni,
            defaults={
                "first_name": nombre,
                "last_name": apellido,
                "grade": seccion.grade,
                "section": seccion,
                "guardian_phone": f"9{random.randint(10000000, 99999999)}",
            },
        )
        indice += 1

estudiantes = list(Student.objects.filter(colegio=school))

# Asistencia de los últimos días hábiles para alimentar reportes y alertas.
hoy = date.today()
dias = []
cursor = hoy
while len(dias) < 6:
    if cursor.weekday() < 5:
        dias.append(cursor)
    cursor -= timedelta(days=1)

for dia in dias:
    for estudiante in estudiantes:
        if random.random() < 0.12:
            continue
        turno = AttendanceRecord.Shift.MORNING
        hora = timezone.make_aware(datetime.combine(dia, datetime.min.time()) + timedelta(hours=7, minutes=45))
        AttendanceRecord.objects.get_or_create(
            colegio=school,
            student=estudiante,
            date=dia,
            shift=turno,
            defaults={
                "attended_by": auxiliar,
                "time": hora,
                "source": AttendanceRecord.Source.QR,
            },
        )

print(
    f"Listo: {Grade.objects.filter(colegio=school).count()} grados, "
    f"{Section.objects.filter(colegio=school).count()} secciones, "
    f"{Student.objects.filter(colegio=school).count()} estudiantes, "
    f"{AttendanceRecord.objects.filter(colegio=school).count()} asistencias."
)
