import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import TenantManager


def generate_qr_token():
    return secrets.token_urlsafe(32)


class School(models.Model):
    name = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "educheck_schools"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Account(AbstractUser):
    class Role(models.TextChoices):
        DIRECTOR = "director", "Director"
        ASSISTANT = "assistant", "Auxiliar"

    colegio = models.ForeignKey(
        School,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="colegio_id",
        related_name="accounts",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.DIRECTOR)

    class Meta:
        db_table = "educheck_accounts"


class TenantModel(models.Model):
    colegio = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        db_column="colegio_id",
    )
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class Grade(TenantModel):
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "educheck_grades"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["colegio", "name"], name="uniq_grade_per_school")
        ]

    def __str__(self):
        return self.name


class Section(TenantModel):
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "educheck_sections"
        ordering = ["grade__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["colegio", "grade", "name"],
                name="uniq_section_per_grade_school",
            )
        ]

    def __str__(self):
        return f"{self.grade.name} {self.name}"


class Student(TenantModel):
    dni = models.CharField(max_length=8)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="students")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="students")
    guardian_phone = models.CharField(max_length=32)
    active = models.BooleanField(default=True)
    qr_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_qr_token,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "educheck_students"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["colegio", "dni"], name="uniq_student_dni_per_school")
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"


class AssistantSectionAssignment(TenantModel):
    assistant = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="section_assignments",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="assistant_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "educheck_assistant_assignments"
        ordering = ["section__grade__name", "section__name", "assistant__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["assistant", "section"],
                name="uniq_assistant_section_assignment",
            )
        ]

    def __str__(self):
        return f"{self.assistant.username} · {self.section}"


class AttendanceRecord(TenantModel):
    class Shift(models.TextChoices):
        MORNING = "morning", "Mañana"
        AFTERNOON = "afternoon", "Tarde"

    class Source(models.TextChoices):
        QR = "qr", "QR"
        MANUAL_DNI = "manual_dni", "DNI manual"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="attendance")
    attended_by = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="attendance_registered",
    )
    date = models.DateField()
    time = models.DateTimeField()
    shift = models.CharField(max_length=16, choices=Shift.choices)
    source = models.CharField(max_length=16, choices=Source.choices)

    class Meta:
        db_table = "educheck_attendance"
        ordering = ["-time"]
        constraints = [
            models.UniqueConstraint(
                fields=["colegio", "student", "date", "shift"],
                name="uniq_student_attendance_per_shift",
            )
        ]
