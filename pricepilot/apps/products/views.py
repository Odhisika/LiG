from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.pricing.services import DefaultMarkupService
from apps.products.serializers import ProductSerializer
from apps.products.services import ProductService


class ProductListCreateView(APIView):
    """GET  /api/products/  — list the current user's products.
    POST /api/products/  — create a new product against one of their suppliers.

    Supports optional `?status=`, `?supplier=` and `?category=` query
    filters on GET.
    """

    serializer_class = ProductSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, required=False),
            OpenApiParameter("supplier", str, required=False),
            OpenApiParameter("category", str, required=False),
        ],
        responses=ProductSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        products = ProductService.list_for_owner(
            request.user,
            status=request.query_params.get("status"),
            supplier_id=request.query_params.get("supplier"),
            category=request.query_params.get("category"),
        )
        context = {"markup_percent": DefaultMarkupService.get_markup_percent(request.user)}
        return Response(envelope(data=ProductSerializer(products, many=True, context=context).data))

    @extend_schema(request=ProductSerializer, responses=ProductSerializer)
    def post(self, request: Request) -> Response:
        product = ProductService.create(request.user, request.data)
        context = {"markup_percent": DefaultMarkupService.get_markup_percent(request.user)}
        return Response(
            envelope(data=ProductSerializer(product, context=context).data),
            status=status.HTTP_201_CREATED,
        )


class ProductCategoriesView(APIView):
    """GET /api/products/categories/ — distinct categories in use by the
    current user's products (drives the category filter dropdowns).
    """

    @extend_schema(responses={200: str})
    def get(self, request: Request) -> Response:
        categories = ProductService.categories_for_owner(request.user)
        return Response(envelope(data=categories))


class ProductDetailView(APIView):
    """GET/PATCH/DELETE /api/products/{id}/ — scoped to the current user."""

    serializer_class = ProductSerializer

    @extend_schema(responses=ProductSerializer)
    def get(self, request: Request, product_id) -> Response:
        product = ProductService.get_for_owner(request.user, product_id)
        context = {"markup_percent": DefaultMarkupService.get_markup_percent(request.user)}
        return Response(envelope(data=ProductSerializer(product, context=context).data))

    @extend_schema(request=ProductSerializer, responses=ProductSerializer)
    def patch(self, request: Request, product_id) -> Response:
        product = ProductService.update(request.user, product_id, request.data, partial=True)
        context = {"markup_percent": DefaultMarkupService.get_markup_percent(request.user)}
        return Response(envelope(data=ProductSerializer(product, context=context).data))

    @extend_schema(responses=None)
    def delete(self, request: Request, product_id) -> Response:
        ProductService.delete(request.user, product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
