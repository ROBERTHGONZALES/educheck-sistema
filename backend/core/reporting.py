from collections import defaultdict

from .models import AttendanceRecord, Student


def report_data(*, start_date, end_date, grade_id=None, section_id=None):
    students = Student.objects.filter(active=True).select_related("grade", "section")
    records = AttendanceRecord.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
    ).select_related("student", "student__grade", "student__section", "attended_by")
    if grade_id is not None:
        students = students.filter(grade_id=grade_id)
        records = records.filter(student__grade_id=grade_id)
    if section_id is not None:
        students = students.filter(section_id=section_id)
        records = records.filter(student__section_id=section_id)

    recorded_days = records.values("date").distinct().count()
    present_count = records.values("student_id", "date").distinct().count()
    expected_count = students.count() * recorded_days
    absence_count = max(expected_count - present_count, 0)

    active_by_group = defaultdict(int)
    for student in students:
        active_by_group[(student.grade.name, student.section.name)] += 1

    present_by_group = defaultdict(int)
    grouped_records = records.values(
        "student__grade__name",
        "student__section__name",
        "student_id",
        "date",
    ).distinct()
    for row in grouped_records:
        group = (row["student__grade__name"], row["student__section__name"])
        present_by_group[group] += 1

    groups = []
    for grade_name, section_name in sorted(active_by_group):
        group = (grade_name, section_name)
        group_present = present_by_group[group]
        group_expected = active_by_group[group] * recorded_days
        group_absent = max(group_expected - group_present, 0)
        groups.append(
            {
                "gradeName": grade_name,
                "sectionName": section_name,
                "presentCount": group_present,
                "absenceCount": group_absent,
                "attendanceRate": round(group_present * 100 / group_expected, 1)
                if group_expected
                else 0,
                "absenceRate": round(group_absent * 100 / group_expected, 1)
                if group_expected
                else 0,
            }
        )

    return {
        "from": start_date,
        "to": end_date,
        "recordedDays": recorded_days,
        "presentCount": present_count,
        "absenceCount": absence_count,
        "attendanceRate": round(present_count * 100 / expected_count, 1)
        if expected_count
        else 0,
        "absenceRate": round(absence_count * 100 / expected_count, 1)
        if expected_count
        else 0,
        "groups": groups,
    }
