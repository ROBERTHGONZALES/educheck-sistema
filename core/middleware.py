from http.cookies import Morsel

from django.conf import settings

from .tenant_context import current_school_id


class _PartitionedMorsel(Morsel):
    _reserved = {**Morsel._reserved, "partitioned": "Partitioned"}
    _flags = Morsel._flags | {"partitioned"}


class PartitionedAuthCookiesMiddleware:
    """Allow auth cookies in the Replit preview iframe using CHIPS."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.cookie_names = {
            settings.SESSION_COOKIE_NAME,
            settings.CSRF_COOKIE_NAME,
        }

    def __call__(self, request):
        response = self.get_response(request)
        for name in self.cookie_names:
            cookie = response.cookies.get(name)
            if (
                cookie is None
                or not cookie["secure"]
                or cookie["samesite"].lower() != "none"
            ):
                continue

            partitioned = _PartitionedMorsel()
            partitioned.set(cookie.key, cookie.value, cookie.coded_value)
            for key in cookie._reserved:
                if cookie[key]:
                    partitioned[key] = cookie[key]
            partitioned["partitioned"] = True
            response.cookies[name] = partitioned
        return response


class CurrentSchoolMiddleware:
    """Scopes tenant managers to the school of the authenticated session user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        school_id = (
            getattr(user, "colegio_id", None)
            if user is not None and user.is_authenticated
            else None
        )
        token = current_school_id.set(school_id)
        try:
            return self.get_response(request)
        finally:
            current_school_id.reset(token)
