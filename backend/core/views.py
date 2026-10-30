from datetime import date
from html import escape
from io import BytesIO

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from .models import (
    Account,
    AssistantSectionAssignment,
    AttendanceRecord,
    Grade,
    Section,
    Student,
)
from .alerts import DEFAULT_THRESHOLD, MAX_THRESHOLD, MIN_THRESHOLD, consecutive_absence_alerts
from .permissions import IsAssistant, IsDirector
from .reporting import report_data
from .serializers import (
    AssistantCreateInputSerializer,
    AssistantSectionsInputSerializer,
    AssistantSectionSerializer,
    AssistantSerializer,
    AttendanceRecordSerializer,
    AttendanceScanInputSerializer,
    GradeInputSerializer,
    GradeSerializer,
    LoginInputSerializer,
    SectionInputSerializer,
    SectionSerializer,
    SessionUserSerializer,
    StudentInputSerializer,
    StudentSerializer,
)
from .student_import import (
    StudentImportError,
    import_students_from_workbook,
    render_student_cards_pdf,
)


class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"status": "ready"})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active or user.colegio_id is None:
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        request.session.set_expiry(30 * 60)
        return Response(SessionUserSerializer(user).data)


class SessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.colegio_id is None:
            return Response({"detail": "La cuenta no pertenece a un colegio."}, status=403)
        return Response(SessionUserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DirectorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        today = timezone.localdate()
        active_students = Student.objects.filter(active=True)
        today_records = AttendanceRecord.objects.filter(date=today)
        active_count = active_students.count()
        present_count = today_records.values("student_id").distinct().count()
        shifts = [
            {
                "shift": shift,
                "present": today_records.filter(shift=shift)
                .values("student_id")
                .distinct()
                .count(),
            }
            for shift, _label in AttendanceRecord.Shift.choices
        ]
        return Response(
            {
                "activeStudents": active_count,
                "presentToday": present_count,
                "absentToday": max(active_count - present_count, 0),
                "attendanceRate": round(present_count * 100 / active_count, 1)
                if active_count
                else 0,
                "shifts": shifts,
            }
        )


class DirectorAssistantListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        assistants = Account.objects.filter(
            colegio_id=request.user.colegio_id,
            role=Account.Role.ASSISTANT,
        ).order_by("first_name", "last_name", "username")
        return Response(AssistantSerializer(assistants, many=True).data)

    def post(self, request):
        serializer = AssistantCreateInputSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        first_name, _, last_name = data["fullName"].strip().rpartition(" ")
        if not first_name:
            first_name, last_name = data["fullName"].strip(), ""
        try:
            with transaction.atomic():
                assistant = Account.objects.create_user(
                    username=data["username"],
                    password=data["password"],
                    first_name=first_name,
                    last_name=last_name,
                    role=Account.Role.ASSISTANT,
                    colegio=request.user.colegio,
                )
                AssistantSectionAssignment.all_objects.bulk_create(
                    [
                        AssistantSectionAssignment(
                            colegio=request.user.colegio,
                            assistant=assistant,
                            section=section,
                        )
                        for section in serializer.context["sections"]
                    ]
                )
        except IntegrityError:
            return Response(
                {"detail": "Ese nombre de usuario ya está registrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AssistantSerializer(assistant).data, status=status.HTTP_201_CREATED)


class DirectorAssistantSectionsView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def put(self, request, assistant_id):
        assistant = Account.objects.filter(
            pk=assistant_id,
            colegio_id=request.user.colegio_id,
            role=Account.Role.ASSISTANT,
        ).first()
        if assistant is None:
            return Response({"detail": "Auxiliar no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssistantSectionsInputSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            AssistantSectionAssignment.all_objects.filter(
                colegio_id=request.user.colegio_id,
                assistant=assistant,
            ).delete()
            AssistantSectionAssignment.all_objects.bulk_create(
                [
                    AssistantSectionAssignment(
                        colegio=request.user.colegio,
                        assistant=assistant,
                        section=section,
                    )
                    for section in serializer.context["sections"]
                ]
            )
        return Response(AssistantSerializer(assistant).data)


class StudentListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        students = Student.objects.select_related("grade", "section")
        search = request.query_params.get("search", "").strip()
        if search:
            students = students.filter(
                Q(dni__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        for parameter, field in (("gradeId", "grade_id"), ("sectionId", "section_id")):
            value = request.query_params.get(parameter)
            if value:
                try:
                    students = students.filter(**{field: int(value)})
                except ValueError:
                    raise ValidationError({parameter: "Debe ser un número entero."})
        active = request.query_params.get("active")
        if active is not None:
            if active.lower() not in {"true", "false"}:
                raise ValidationError({"active": "Usa true o false."})
            students = students.filter(active=active.lower() == "true")
        return Response(StudentSerializer(students, many=True).data)

    def post(self, request):
        serializer = StudentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            student = Student.objects.create(
                colegio=request.user.colegio,
                dni=data["dni"],
                first_name=data["firstName"],
                last_name=data["lastName"],
                grade=data["grade"],
                section=data["section"],
                guardian_phone=data["guardianPhone"],
            )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un estudiante con ese DNI en este colegio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)


class GradeListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        grades = Grade.objects.prefetch_related("sections")
        return Response(GradeSerializer(grades, many=True).data)

    def post(self, request):
        serializer = GradeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grade = Grade.objects.create(
                colegio=request.user.colegio,
                name=serializer.validated_data["name"],
            )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un grado con ese nombre en este colegio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(GradeSerializer(grade).data, status=status.HTTP_201_CREATED)


class SectionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        serializer = SectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            section = Section.objects.create(
                colegio=request.user.colegio,
                grade=data["grade"],
                name=data["name"],
            )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe esa sección para el grado indicado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SectionSerializer(section).data, status=status.HTTP_201_CREATED)


class SectionDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def delete(self, request, section_id):
        try:
            section = Section.objects.get(pk=section_id)
        except Section.DoesNotExist:
            return Response({"detail": "Sección no encontrada."}, status=404)
        if Student.objects.filter(section=section).exists():
            return Response(
                {"detail": "No se puede eliminar una sección con estudiantes asignados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_assigned_section(request, section_id):
    assignment = (
        AssistantSectionAssignment.objects.filter(
            assistant=request.user,
            section_id=section_id,
        )
        .select_related("section", "section__grade")
        .first()
    )
    if assignment is None:
        raise Http404("No tienes acceso a esta sección.")
    return assignment.section


class AssistantSectionListView(APIView):
    permission_classes = [IsAuthenticated, IsAssistant]

    def get(self, request):
        sections = (
            Section.objects.filter(assistant_assignments__assistant=request.user)
            .select_related("grade")
            .annotate(student_count=Count("students"))
            .order_by("grade__name", "name")
        )
        return Response(
            AssistantSectionSerializer(
                sections,
                many=True,
                context={"request": request},
            ).data
        )


class AssistantSectionStudentsView(APIView):
    permission_classes = [IsAuthenticated, IsAssistant]

    def get(self, request, section_id):
        section = _get_assigned_section(request, section_id)
        students = Student.objects.filter(section=section).select_related("grade", "section")
        return Response(StudentSerializer(students, many=True).data)


class AssistantStudentImportView(APIView):
    permission_classes = [IsAuthenticated, IsAssistant]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, section_id):
        section = _get_assigned_section(request, section_id)
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Adjunta un archivo Excel .xlsx en el campo «file»."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not upload.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "Solo se aceptan archivos .xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > 5 * 1024 * 1024:
            return Response(
                {"detail": "El archivo no puede superar 5 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = import_students_from_workbook(
                upload,
                request.user.colegio_id,
                section,
            )
        except StudentImportError as exc:
            return Response(
                {"detail": exc.detail, "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "Los datos cambiaron durante la importación. "
                        "No se guardó ningún registro; vuelve a importar el archivo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(result, status=status.HTTP_200_OK)


class AssistantStudentCardsPdfView(APIView):
    permission_classes = [IsAuthenticated, IsAssistant]

    def get(self, request, section_id):
        section = _get_assigned_section(request, section_id)
        students = list(
            Student.objects.filter(section=section)
            .select_related("grade", "section")
            .order_by("last_name", "first_name", "dni")
        )
        if not students:
            return Response(
                {"detail": "Esta sección todavía no tiene estudiantes para generar carnets."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pdf = render_student_cards_pdf(students, request.user.colegio.name)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="educheck-carnets-seccion-{section.id}.pdf"'
        )
        return response


class AttendanceScanView(APIView):
    permission_classes = [IsAuthenticated, IsAssistant]

    def post(self, request):
        serializer = AttendanceScanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        selected_shift = data["shift"]

        try:
            with transaction.atomic():
                students = Student.objects.select_for_update().select_related(
                    "grade", "section"
                )
                assigned_section_ids = AssistantSectionAssignment.objects.filter(
                    assistant=request.user
                ).values_list("section_id", flat=True)
                students = students.filter(section_id__in=assigned_section_ids)
                if "qrCode" in data:
                    student = students.filter(qr_token=data["qrCode"]).first()
                    source = AttendanceRecord.Source.QR
                else:
                    student = students.filter(dni=data["dni"]).first()
                    source = AttendanceRecord.Source.MANUAL_DNI

                if student is None:
                    return Response(
                        {"detail": "No se encontró un estudiante activo con ese código."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not student.active:
                    return Response(
                        {"detail": "El estudiante está inactivo."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                now = timezone.now()
                record = AttendanceRecord.objects.create(
                    colegio=request.user.colegio,
                    student=student,
                    attended_by=request.user,
                    date=timezone.localdate(now),
                    time=now,
                    shift=selected_shift,
                    source=source,
                )
        except IntegrityError:
            return Response(
                {"detail": "La asistencia ya fue registrada para este estudiante y turno."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            AttendanceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


def _parse_integer_parameter(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError({name: "Debe ser un número entero."})
    if value < 1:
        raise ValidationError({name: "Debe ser un número positivo."})
    return value


class DirectorAlertsView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        raw_threshold = request.query_params.get("threshold")
        threshold = DEFAULT_THRESHOLD
        if raw_threshold not in (None, ""):
            try:
                threshold = int(raw_threshold)
            except ValueError:
                raise ValidationError({"threshold": "Debe ser un número entero."})
            if not MIN_THRESHOLD <= threshold <= MAX_THRESHOLD:
                raise ValidationError(
                    {"threshold": f"Debe estar entre {MIN_THRESHOLD} y {MAX_THRESHOLD}."}
                )

        recorded_days, alerts = consecutive_absence_alerts(
            threshold=threshold,
            grade_id=_parse_integer_parameter(request.query_params, "gradeId"),
            section_id=_parse_integer_parameter(request.query_params, "sectionId"),
        )
        return Response(
            {"threshold": threshold, "recordedDays": recorded_days, "alerts": alerts}
        )


def _parse_report_dates(params):
    start_date = parse_date(params.get("from", ""))
    end_date = parse_date(params.get("to", ""))
    if start_date is None:
        raise ValidationError({"from": "Usa una fecha válida con formato AAAA-MM-DD."})
    if end_date is None:
        raise ValidationError({"to": "Usa una fecha válida con formato AAAA-MM-DD."})
    if start_date > end_date:
        raise ValidationError({"to": "La fecha final debe ser igual o posterior a la inicial."})
    return start_date, end_date


class AttendanceQueryView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        selected_date = parse_date(request.query_params.get("date", ""))
        if selected_date is None:
            raise ValidationError({"date": "Usa una fecha válida con formato AAAA-MM-DD."})
        shift = request.query_params.get("shift")
        if shift and shift not in AttendanceRecord.Shift.values:
            raise ValidationError({"shift": "El turno debe ser morning o afternoon."})
        grade_id = _parse_integer_parameter(request.query_params, "gradeId")
        section_id = _parse_integer_parameter(request.query_params, "sectionId")
        dni = request.query_params.get("dni")
        if dni and (len(dni) != 8 or not dni.isdigit()):
            raise ValidationError({"dni": "El DNI debe tener exactamente 8 dígitos."})

        students = Student.objects.filter(active=True).select_related("grade", "section")
        if grade_id:
            students = students.filter(grade_id=grade_id)
        if section_id:
            students = students.filter(section_id=section_id)
        if dni:
            students = students.filter(dni=dni)

        records = AttendanceRecord.objects.filter(date=selected_date).select_related(
            "student", "student__grade", "student__section", "attended_by"
        )
        if shift:
            records = records.filter(shift=shift)
        if grade_id:
            records = records.filter(student__grade_id=grade_id)
        if section_id:
            records = records.filter(student__section_id=section_id)
        if dni:
            records = records.filter(student__dni=dni)

        present_ids = records.values_list("student_id", flat=True).distinct()
        absent_students = students.exclude(id__in=present_ids)
        return Response(
            {
                "records": AttendanceRecordSerializer(records, many=True).data,
                "absentStudents": [
                    {
                        "studentId": student.id,
                        "studentName": f"{student.first_name} {student.last_name}".strip(),
                        "dni": student.dni,
                        "gradeName": student.grade.name,
                        "sectionName": student.section.name,
                    }
                    for student in absent_students
                ],
            }
        )


def _report_filters(request):
    start_date, end_date = _parse_report_dates(request.query_params)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "grade_id": _parse_integer_parameter(request.query_params, "gradeId"),
        "section_id": _parse_integer_parameter(request.query_params, "sectionId"),
    }


class AttendanceReportView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        return Response(report_data(**_report_filters(request)))


class AttendancePdfExportView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        data = report_data(**_report_filters(request))
        rows = "".join(
            "<tr>"
            f"<td>{escape(group['gradeName'])}</td>"
            f"<td>{escape(group['sectionName'])}</td>"
            f"<td>{group['presentCount']}</td>"
            f"<td>{group['absenceCount']}</td>"
            f"<td>{group['attendanceRate']:.1f}%</td>"
            f"<td>{group['absenceRate']:.1f}%</td>"
            "</tr>"
            for group in data["groups"]
        )
        document = f"""<!doctype html>
        <html lang="es"><meta charset="utf-8"><style>
        body {{ font-family: sans-serif; color: #241650; }}
        h1 {{ color: #34206A; }} .summary {{ background: #F7F4FF; padding: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
        th {{ background: #34206A; color: #fff; }} th, td {{ padding: 8px; border: 1px solid #C9B8E4; }}
        </style><body>
        <h1>EduCheck · Reporte de asistencia</h1>
        <p>Periodo: {data['from'].isoformat()} al {data['to'].isoformat()}</p>
        <div class="summary">Días con registros: {data['recordedDays']} ·
        Asistencia: {data['attendanceRate']:.1f}% · Inasistencia: {data['absenceRate']:.1f}%</div>
        <table><thead><tr><th>Grado</th><th>Sección</th><th>Asistencias</th>
        <th>Inasistencias</th><th>% Asistencia</th><th>% Inasistencia</th></tr></thead>
        <tbody>{rows}</tbody></table></body></html>"""
        from weasyprint import HTML

        response = HttpResponse(HTML(string=document).write_pdf(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="educheck-reporte.pdf"'
        return response


def _safe_spreadsheet_text(value):
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


class AttendanceXlsxExportView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        data = report_data(**_report_filters(request))
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Asistencia"
        sheet.append(["EduCheck · Reporte de asistencia"])
        sheet.append(["Desde", data["from"].isoformat(), "Hasta", data["to"].isoformat()])
        sheet.append(["Días con registros", data["recordedDays"]])
        sheet.append(["Asistencia", data["attendanceRate"] / 100])
        sheet.append(["Inasistencia", data["absenceRate"] / 100])
        sheet.append([])
        sheet.append(
            ["Grado", "Sección", "Asistencias", "Inasistencias", "% Asistencia", "% Inasistencia"]
        )
        for group in data["groups"]:
            sheet.append(
                [
                    _safe_spreadsheet_text(group["gradeName"]),
                    _safe_spreadsheet_text(group["sectionName"]),
                    group["presentCount"],
                    group["absenceCount"],
                    group["attendanceRate"] / 100,
                    group["absenceRate"] / 100,
                ]
            )
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF", size=14)
            cell.fill = PatternFill("solid", fgColor="34206A")
        for cell in sheet[7]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="6743A5")
            cell.alignment = Alignment(horizontal="center")
        for row in range(4, sheet.max_row + 1):
            for column in (2, 5, 6):
                sheet.cell(row=row, column=column).number_format = "0.0%"
        for column, width in zip("ABCDEF", [18, 18, 18, 18, 18, 20]):
            sheet.column_dimensions[column].width = width

        content = BytesIO()
        workbook.save(content)
        response = HttpResponse(
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="educheck-reporte.xlsx"'
        return response
