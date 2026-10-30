"""Alertas de inasistencia: estudiantes con N faltas seguidas.

Un día cuenta como registrado cuando el colegio tiene al menos un registro de
asistencia, igual que en los reportes. La falta se calcula sin distinguir turnos.
"""

from django.utils import timezone

from .models import AttendanceRecord, Student

DEFAULT_THRESHOLD = 3
MIN_THRESHOLD = 2
MAX_THRESHOLD = 10
LOOKBACK_DAYS = 60


def consecutive_absence_alerts(*, threshold=DEFAULT_THRESHOLD, grade_id=None, section_id=None):
    recorded_dates = list(
        AttendanceRecord.objects.order_by("-date")
        .values_list("date", flat=True)
        .distinct()[:LOOKBACK_DAYS]
    )
    if len(recorded_dates) < threshold:
        return len(recorded_dates), []

    students = Student.objects.filter(active=True).select_related("grade", "section")
    if grade_id is not None:
        students = students.filter(grade_id=grade_id)
    if section_id is not None:
        students = students.filter(section_id=section_id)

    present = set(
        AttendanceRecord.objects.filter(date__in=recorded_dates)
        .values_list("student_id", "date")
    )

    alerts = []
    for student in students:
        enrolled_on = timezone.localtime(student.created_at).date()
        streak = 0
        first_absence = None
        last_attendance = None
        for day in recorded_dates:
            if day < enrolled_on:
                break
            if (student.id, day) in present:
                last_attendance = day
                break
            streak += 1
            first_absence = day

        if streak >= threshold:
            alerts.append(
                {
                    "studentId": student.id,
                    "studentName": f"{student.first_name} {student.last_name}".strip(),
                    "dni": student.dni,
                    "gradeName": student.grade.name,
                    "sectionName": student.section.name,
                    "guardianPhone": student.guardian_phone,
                    "consecutiveAbsences": streak,
                    "absentSince": first_absence,
                    "lastAttendanceDate": last_attendance,
                }
            )

    alerts.sort(key=lambda item: (-item["consecutiveAbsences"], item["studentName"]))
    return len(recorded_dates), alerts
