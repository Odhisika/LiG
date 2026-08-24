from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import RegisterSerializer, UserSerializer
from apps.accounts.services import AccountService
from apps.common.api import envelope


class RegisterView(APIView):
    """POST /api/auth/register/ — create a new merchant account."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(request=RegisterSerializer, responses=UserSerializer)
    def post(self, request: Request) -> Response:
        user = AccountService.register(request.data)
        return Response(
            envelope(data=UserSerializer(user).data),
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """GET /api/auth/me/ — current authenticated user."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(envelope(data=UserSerializer(request.user).data))
