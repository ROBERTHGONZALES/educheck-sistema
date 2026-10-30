from django.db import models

from .tenant_context import current_school_id


class TenantQuerySet(models.QuerySet):
    def for_school(self, school_id: int):
        return self.filter(colegio_id=school_id)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    def get_queryset(self):
        queryset = super().get_queryset()
        school_id = current_school_id.get()
        if school_id is None:
            return queryset.none()
        return queryset.filter(colegio_id=school_id)
