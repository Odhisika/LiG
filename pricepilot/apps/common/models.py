import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model providing UUID PK and audit timestamps.

    Every domain model in PricePilot should inherit from this so that
    history/auditing is consistent across the codebase, per the
    "never delete important data / audit everything" project standard.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager only returns non-deleted rows."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(TimeStampedModel):
    """Abstract base for models that should never be hard-deleted.

    Use for Product, Supplier, PricingRule etc. — anything a merchant
    might "remove" but that we still want traceable in history/audit.
    """

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
