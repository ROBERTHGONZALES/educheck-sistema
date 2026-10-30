from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/educheck/schema/", SpectacularAPIView.as_view(), name="educheck-schema"),
    path(
        "api/educheck/docs/",
        SpectacularSwaggerView.as_view(url_name="educheck-schema"),
        name="educheck-docs",
    ),
    path("api/educheck/", include("core.urls")),
]
