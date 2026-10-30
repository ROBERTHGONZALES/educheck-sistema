from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError

from core.models import School


class Command(BaseCommand):
    help = "Crea una cuenta de Director o Auxiliar para un colegio."

    def add_arguments(self, parser):
        parser.add_argument("--school", required=True, help="Nombre exacto del colegio.")
        parser.add_argument("--username", required=True)
        parser.add_argument(
            "--role",
            choices=["director", "assistant"],
            required=True,
        )
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    def handle(self, *args, **options):
        school_name = options["school"].strip()
        username = options["username"].strip()
        if not school_name or not username:
            raise CommandError("El nombre del colegio y el usuario son obligatorios.")

        school, _created = School.objects.get_or_create(name=school_name)
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            raise CommandError("Ese nombre de usuario ya está registrado.")

        password = getpass("Contraseña (mínimo 12 caracteres): ")
        confirmation = getpass("Repite la contraseña: ")
        if password != confirmation:
            raise CommandError("Las contraseñas no coinciden.")

        user = user_model(
            username=username,
            first_name=options["first_name"].strip(),
            last_name=options["last_name"].strip(),
            role=options["role"],
            colegio=school,
        )
        try:
            validate_password(password, user=user)
        except Exception as error:
            raise CommandError(str(error)) from error
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Cuenta {user.username} creada para {school.name} ({user.get_role_display()})."
            )
        )
