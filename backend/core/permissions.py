from rest_framework.permissions import BasePermission


class IsDirector(BasePermission):
    message = "Esta función solo está disponible para el Director."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "director"
            and request.user.colegio_id
        )


class IsAssistant(BasePermission):
    message = "Esta función solo está disponible para el Auxiliar."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "assistant"
            and request.user.colegio_id
        )
