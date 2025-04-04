from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages

from .models import Product, ReviewRating, ProductGallery, ComputerProduct, SoftwareProduct, PeripheralProduct
from category.models import Category
from cart.models import CartItem
from cart.views import _cart_id
from .forms import ReviewForm
from orders.models import OrderProduct





def store(request, category_slug=None):
    categories = None
    products = None

    if category_slug:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')
    
   
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        products = products.filter(price__gte=min_price, price__lte=max_price)
    
    # Pagination
    paginator = Paginator(products, 3 if not category_slug else 1)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()
    
    context = {
        'products': paged_products,
        'product_count': product_count,
        
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'store/store.html', context)





# views.py
from django.shortcuts import get_object_or_404, render
from .models import Product, ReviewRating, ProductGallery

def product_detail(request, category_slug, product_slug):
    # Get the product with all related sub-products in one query
    product = get_object_or_404(
        Product.objects.select_related(
            'computerproduct',
            'softwareproduct',
            'peripheralproduct'
        ).prefetch_related('productgallery_set'),
        category__slug=category_slug,
        slug=product_slug,
        is_available=True
    )
    
    # Get product gallery images
    product_gallery = ProductGallery.objects.filter(product=product)
    
    # Get reviews
    reviews = ReviewRating.objects.filter(product=product, status=True)
    
    context = {
        'single_product': product,
        'product_gallery': product_gallery,
        'reviews': reviews,
    }
    
    return render(request, 'store/product_detail.html', context)

def search(request):
    print("Search function triggered")  

    products = None
    product_count = 0

    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        print(f"Keyword searched: {keyword}")  

        if keyword:
            products = Product.objects.order_by('-created_date').filter(
                Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
            )
            product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)



def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated.')
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = form.save(commit=False)
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
        return redirect(url)
