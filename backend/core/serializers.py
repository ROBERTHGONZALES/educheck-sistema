import segno
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from rest_framework import serializers

from .models import (
    AssistantSectionAssignment,
    AttendanceRecord,
    Grade,
    Section,
    Student,
)

Account = get_user_model()


class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class SessionUserSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    schoolName = serializers.CharField(source="colegio.name", read_only=True)

    class Meta:
        model = Account
        fields = ["id", "username", "fullName", "role", "schoolName"]

    def get_fullName(self, user):
        return user.get_full_name().strip() or user.username


class StudentInputSerializer(serializers.Serializer):
    dni = serializers.RegexField(r"^[0-9]{8}$")
    firstName = serializers.CharField(max_length=120, trim_whitespace=True)
    lastName = serializers.CharField(max_length=120, trim_whitespace=True)
    gradeId = serializers.IntegerField(min_value=1)
    sectionId = serializers.IntegerField(min_value=1)
    guardianPhone = serializers.CharField(max_length=32, trim_whitespace=True)

    def validate(self, attrs):
        try:
            grade = Grade.objects.get(pk=attrs["gradeId"])
            section = Section.objects.get(pk=attrs["sectionId"])
        except (Grade.DoesNotExist, Section.DoesNotExist):
            raise serializers.ValidationError("El grado o la sección no pertenecen a este colegio.")
        if section.grade_id != grade.id:
            raise serializers.ValidationError("La sección seleccionada no pertenece al grado indicado.")
        attrs["grade"] = grade
        attrs["section"] = section
        return attrs


class StudentSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name", read_only=True)
    lastName = serializers.CharField(source="last_name", read_only=True)
    gradeId = serializers.IntegerField(source="grade_id", read_only=True)
    gradeName = serializers.CharField(source="grade.name", read_only=True)
    sectionId = serializers.IntegerField(source="section_id", read_only=True)
    sectionName = serializers.CharField(source="section.name", read_only=True)
    guardianPhone = serializers.CharField(source="guardian_phone", read_only=True)
    qrSvg = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "dni",
            "firstName",
            "lastName",
            "gradeId",
            "gradeName",
            "sectionId",
            "sectionName",
            "guardianPhone",
            "active",
            "qrSvg",
            "createdAt",
        ]

    def get_qrSvg(self, student):
        qr = segno.make(student.qr_token, error="M", micro=False)
        return qr.svg_data_uri(
            scale=5,
            dark="#34206A",
            light="#FFFFFF",
            border=2,
        )


class GradeInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, trim_whitespace=True)


class SectionInputSerializer(serializers.Serializer):
    gradeId = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=40, trim_whitespace=True)

    def validate(self, attrs):
        try:
            attrs["grade"] = Grade.objects.get(pk=attrs["gradeId"])
        except Grade.DoesNotExist:
            raise serializers.ValidationError("El grado no pertenece a este colegio.")
        return attrs


class SectionSerializer(serializers.ModelSerializer):
    gradeId = serializers.IntegerField(source="grade_id", read_only=True)

    class Meta:
        model = Section
        fields = ["id", "gradeId", "name"]


class GradeSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Grade
        fields = ["id", "name", "sections"]


class AssistantSectionSerializer(serializers.ModelSerializer):
    gradeId = serializers.IntegerField(source="grade_id", read_only=True)
    gradeName = serializers.CharField(source="grade.name", read_only=True)
    studentCount = serializers.IntegerField(source="student_count", read_only=True)

    class Meta:
        model = Section
        fields = ["id", "gradeId", "gradeName", "name", "studentCount"]


class AssistantSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ["id", "username", "fullName", "sections"]

    def get_fullName(self, user):
        return user.get_full_name().strip() or user.username

    def get_sections(self, user):
        assignments = (
            AssistantSectionAssignment.objects.filter(assistant=user)
            .select_related("section", "section__grade")
            .annotate(student_count=Count("section__students"))
        )
        sections = [assignment.section for assignment in assignments]
        counts = {assignment.section_id: assignment.student_count for assignment in assignments}
        for section in sections:
            section.student_count = counts[section.id]
        return AssistantSectionSerializer(sections, many=True).data


class AssistantCreateInputSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]{1,150}$")
    fullName = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(min_length=12, write_only=True, trim_whitespace=False)
    sectionIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_sectionIds(self, section_ids):
        if len(section_ids) != len(set(section_ids)):
            raise serializers.ValidationError("No repitas una sección.")
        school_id = self.context["request"].user.colegio_id
        sections = list(
            Section.objects.filter(colegio_id=school_id, id__in=section_ids).select_related("grade")
        )
        if len(sections) != len(section_ids):
            raise serializers.ValidationError(
                "Todas las secciones deben pertenecer al colegio de la sesión."
            )
        self.context["sections"] = sections
        return section_ids

    def validate_password(self, password):
        user = Account(username=self.initial_data.get("username", ""))
        try:
            from django.contrib.auth.password_validation import validate_password

            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return password


class AssistantSectionsInputSerializer(serializers.Serializer):
    sectionIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )

    def validate_sectionIds(self, section_ids):
        if len(section_ids) != len(set(section_ids)):
            raise serializers.ValidationError("No repitas una sección.")
        school_id = self.context["request"].user.colegio_id
        sections = list(Section.objects.filter(colegio_id=school_id, id__in=section_ids))
        if len(sections) != len(section_ids):
            raise serializers.ValidationError(
                "Todas las secciones deben pertenecer al colegio de la sesión."
            )
        self.context["sections"] = sections
        return section_ids


class AttendanceScanInputSerializer(serializers.Serializer):
    qrCode = serializers.CharField(required=False, allow_blank=False, min_length=16)
    dni = serializers.RegexField(r"^[0-9]{8}$", required=False)
    shift = serializers.ChoiceField(choices=AttendanceRecord.Shift.choices)

    def validate(self, attrs):
        if ("qrCode" in attrs) == ("dni" in attrs):
            raise serializers.ValidationError("Envía un código QR o un DNI, pero no ambos.")
        return attrs


class AttendanceRecordSerializer(serializers.ModelSerializer):
    studentId = serializers.IntegerField(source="student_id", read_only=True)
    studentName = serializers.SerializerMethodField()
    dni = serializers.CharField(source="student.dni", read_only=True)
    gradeName = serializers.CharField(source="student.grade.name", read_only=True)
    sectionName = serializers.CharField(source="student.section.name", read_only=True)
    attendedBy = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "studentId",
            "studentName",
            "dni",
            "gradeName",
            "sectionName",
            "date",
            "time",
            "shift",
            "source",
            "attendedBy",
        ]

    def get_studentName(self, record):
        return f"{record.student.first_name} {record.student.last_name}".strip()

    def get_attendedBy(self, record):
        return record.attended_by.get_full_name().strip() or record.attended_by.username
