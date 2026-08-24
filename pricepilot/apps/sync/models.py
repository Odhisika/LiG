import uuid

from django.db import models


def _generate_sku() -> str:
    """Mirrors LiG's store.Product.generate_sku() so seeded rows get the
    same SKU shape the site's admin/order tooling already expects.
    """
    return f"SKU-{uuid.uuid4().hex[:8].upper()}"


class LiGCategory(models.Model):
    """Unmanaged mirror of LiG's `category_category` table.

    Only the fields the sync engine reads (category resolution for seeding)
    are declared. managed=False means Django never migrates or owns these
    tables — they belong to the merchant's site (LiG) and are written to
    through the `lig` database alias only.
    """

    id = models.BigAutoField(primary_key=True)
    category_name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True, default="")
    cat_image = models.FileField(upload_to="photos/categories", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        managed = False
        app_label = "sync"
        db_table = "category_category"

    def __str__(self) -> str:
        return self.category_name


class LiGProduct(models.Model):
    """Unmanaged mirror of LiG's base `store_product` table.

    LiG uses multi-table inheritance — every product type (ComputerProduct,
    UPSProduct, SecurityCameraProduct, ...) shares this base row, which holds
    all the fields the sync engine updates (price, cost_price, stock,
    description, is_available). Because those live on the base table, one
    model covers every product type; the sync engine never needs to know (or
    touch) which subclass a row belongs to.

    `images` is a FileField (not ImageField) so the sync engine can write a
    downloaded image without depending on Pillow — the merchant site's DB
    column is a varchar either way.
    """

    id = models.BigAutoField(primary_key=True)

    product_name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    description = models.TextField(blank=True, default="")
    short_description = models.CharField(max_length=500, blank=True, default="")

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    sku = models.CharField(max_length=50, unique=True, default=_generate_sku)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    stock = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    track_inventory = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)

    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_sold = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    is_digital = models.BooleanField(default=False)

    condition = models.CharField(max_length=20, choices=[("new", "Fresh in Box")], default="new")

    meta_title = models.CharField(max_length=60, blank=True, default="")
    meta_description = models.CharField(max_length=160, blank=True, default="")

    category = models.ForeignKey(LiGCategory, on_delete=models.CASCADE)
    tags = models.CharField(max_length=500, blank=True, default="")

    weight = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    dimensions_length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions_width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions_height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    images = models.FileField(upload_to="photos/products", blank=True, null=True)

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        app_label = "sync"
        db_table = "store_product"
        ordering = ["-created_date"]

    def __str__(self) -> str:
        return self.product_name


class LiGProductGallery(models.Model):
    """Unmanaged mirror of LiG's `store_productgallery` table.

    Used when seeding a product with more than one image — the first image
    goes into LiGProduct.images, the rest become gallery rows (the LiG
    storefront's `primary_image_url` falls back to gallery rows).
    """

    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(LiGProduct, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.FileField(upload_to="store/products", max_length=255)
    alt_text = models.CharField(max_length=255, blank=True, default="")
    image_type = models.CharField(max_length=20, default="gallery")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        app_label = "sync"
        db_table = "store_productgallery"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.product.product_name} - {self.image_type}"
