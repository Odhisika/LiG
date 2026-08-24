from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.discovery.serializers import DiscoveredProductSerializer, ImportDiscoveryInputSerializer
from apps.discovery.services import DiscoveryService
from apps.products.serializers import ProductSerializer


class DiscoveredProductListView(APIView):
    """GET /api/discoveries/ — the current user's discovery review queue.

    Filter with ?status=pending|imported|dismissed (defaults to
    everything if omitted).
    """

    serializer_class = DiscoveredProductSerializer

    @extend_schema(
        parameters=[OpenApiParameter("status", str, required=False)],
        responses=DiscoveredProductSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        discoveries = DiscoveryService.list_for_owner(
            request.user, status=request.query_params.get("status")
        )
        return Response(envelope(data=DiscoveredProductSerializer(discoveries, many=True).data))


class DiscoveredProductImportView(APIView):
    """POST /api/discoveries/{id}/import/ — the one-click "yes, track
    this" action. Body is optional overrides (see
    ImportDiscoveryInputSerializer) for when the auto-captured preview
    isn't enough on its own (e.g. no price was found).
    """

    serializer_class = ImportDiscoveryInputSerializer

    @extend_schema(request=ImportDiscoveryInputSerializer, responses=ProductSerializer)
    def post(self, request: Request, discovery_id) -> Response:
        serializer = ImportDiscoveryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = DiscoveryService.import_discovery(
            request.user, discovery_id, overrides=serializer.validated_data
        )
        return Response(
            envelope(data=ProductSerializer(product).data), status=status.HTTP_201_CREATED
        )


class DiscoveredProductDismissView(APIView):
    """POST /api/discoveries/{id}/dismiss/ — "no thanks, don't ask again
    about this URL" (it stays recorded so a future scan won't re-surface it).
    """

    serializer_class = DiscoveredProductSerializer

    @extend_schema(responses=DiscoveredProductSerializer)
    def post(self, request: Request, discovery_id) -> Response:
        discovery = DiscoveryService.dismiss_discovery(request.user, discovery_id)
        return Response(envelope(data=DiscoveredProductSerializer(discovery).data))
