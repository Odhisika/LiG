from django.contrib.auth import get_user_model

from apps.accounts.serializers import RegisterSerializer
from apps.common.exceptions import ValidationError

User = get_user_model()


class AccountService:
    """Business logic for account creation, kept out of the view layer
    per the project's service-layer coding standard.
    """

    @staticmethod
    def register(data: dict) -> User:
        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))
        return serializer.save()
