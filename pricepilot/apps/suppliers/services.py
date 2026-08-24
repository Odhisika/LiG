from django.db import IntegrityError

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ValidationError
from apps.suppliers.models import Supplier
from apps.suppliers.serializers import SupplierSerializer


class SupplierService:
    """Business logic for supplier CRUD, kept out of the view layer.

    Every method is scoped by `owner` — there is no "list all suppliers"
    path here, by design, so ownership isolation can't be forgotten by
    a future call site.
    """

    @staticmethod
    def list_for_owner(owner: User):
        return Supplier.objects.filter(owner=owner)

    @staticmethod
    def get_for_owner(owner: User, supplier_id) -> Supplier:
        supplier = Supplier.objects.filter(owner=owner, id=supplier_id).first()
        if supplier is None:
            raise NotFoundError("Supplier not found.")
        return supplier

    @staticmethod
    def create(owner: User, data: dict) -> Supplier:
        serializer = SupplierSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))
        try:
            return Supplier.objects.create(owner=owner, **serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(f"A supplier named '{data.get('name')}' already exists.") from exc

    @staticmethod
    def update(owner: User, supplier_id, data: dict, partial: bool = True) -> Supplier:
        supplier = SupplierService.get_for_owner(owner, supplier_id)
        serializer = SupplierSerializer(supplier, data=data, partial=partial)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))
        try:
            return serializer.save()
        except IntegrityError as exc:
            raise ValidationError(f"A supplier named '{data.get('name')}' already exists.") from exc

    @staticmethod
    def delete(owner: User, supplier_id) -> None:
        supplier = SupplierService.get_for_owner(owner, supplier_id)
        supplier.soft_delete()
