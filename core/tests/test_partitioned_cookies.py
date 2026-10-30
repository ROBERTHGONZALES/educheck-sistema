from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.middleware import PartitionedAuthCookiesMiddleware


class PartitionedAuthCookiesMiddlewareTests(SimpleTestCase):
    def test_partitions_secure_csrf_and_session_cookies(self):
        def response_with_auth_cookies(request):
            response = HttpResponse("ok")
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                "csrf-value",
                secure=True,
                samesite="None",
            )
            response.set_cookie(
                settings.SESSION_COOKIE_NAME,
                "session-value",
                secure=True,
                httponly=True,
                samesite="None",
            )
            response.set_cookie(
                "unrelated",
                "value",
                secure=True,
                samesite="None",
            )
            return response

        middleware = PartitionedAuthCookiesMiddleware(response_with_auth_cookies)
        response = middleware(RequestFactory().get("/"))

        for name in (settings.CSRF_COOKIE_NAME, settings.SESSION_COOKIE_NAME):
            cookie = response.cookies[name]
            self.assertIn("Partitioned", cookie.OutputString())
            self.assertIn("SameSite=None", cookie.OutputString())
            self.assertIn("Secure", cookie.OutputString())

        self.assertNotIn(
            "Partitioned",
            response.cookies["unrelated"].OutputString(),
        )

    def test_does_not_partition_insecure_cookies(self):
        def response_with_insecure_cookie(request):
            response = HttpResponse("ok")
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                "csrf-value",
                secure=False,
                samesite="Lax",
            )
            return response

        middleware = PartitionedAuthCookiesMiddleware(response_with_insecure_cookie)
        response = middleware(RequestFactory().get("/"))

        self.assertNotIn(
            "Partitioned",
            response.cookies[settings.CSRF_COOKIE_NAME].OutputString(),
        )
