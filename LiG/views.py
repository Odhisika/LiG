from django.shortcuts import render, get_object_or_404
from store.models import Product, Category, ReviewRating, ComputerProduct, SoftwareProduct, PeripheralProduct, NetworkingProduct, SecurityCameraProduct, HomeBanner
from research.models import BlogModel
from django.shortcuts import render, redirect
from django.http import HttpResponse
from research.form import ProjectBookingForm
from django.db.models import Q
from category.models import ResearchTypes, ComputerTypes, SoftwareTypes
from accounts.models import NewsletterSubscriber
from django.contrib import messages


def home(request):
    products = Product.objects.filter(is_available=True).select_related('category').order_by('?')[:12]
    active_banners = {banner.slide_number: banner for banner in HomeBanner.objects.filter(is_active=True)}
    context = {'products': products, 'banners': active_banners}
    return render(request, 'home.html', context)


def allproducts(request):
    products = Product.objects.filter(is_available=True).select_related('category').order_by('?')
    context = {'products': products}
    return render(request, 'hardware/allproducts.html', context)


def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            if NewsletterSubscriber.objects.filter(email=email).exists():
                messages.info(request, 'You are already subscribed to our newsletter.')
            else:
                NewsletterSubscriber.objects.create(email=email)
                messages.success(request, 'Thank you for subscribing to our newsletter!')
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    return redirect('home')


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTERS — filter by computer_type slug or its parent slug
# The computer_type hierarchy: Laptop > Fresh Laptop / Slightly Used Laptop etc.
# ─────────────────────────────────────────────────────────────────────────────

def laptops(request):
    """All laptops — any ComputerProduct where computer_type is 'Laptop' or its child."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='laptop') | Q(computer_type__parent__slug='laptop'),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/laptop.html', context)


def fresh_laptops(request):
    """Fresh/new laptops only."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='laptop') | Q(computer_type__parent__slug='laptop'),
        is_available=True
    ).filter(
        Q(condition='new') | Q(computer_type__slug='fresh-laptop')
    ).exclude(
        computer_type__slug='slightly-used-laptop'
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/fresh_laptops.html', context)


def used_laptops(request):
    """Slightly used laptops."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='laptop') | Q(computer_type__parent__slug='laptop'),
        is_available=True
    ).filter(
        Q(condition='slightly_used') | Q(computer_type__slug='slightly-used-laptop')
    ).exclude(
        computer_type__slug='fresh-laptop'
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/used_laptops.html', context)


def desktops(request):
    """All desktops — any ComputerProduct where computer_type is 'Desktop' or its child."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='desktop') | Q(computer_type__parent__slug='desktop'),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/desktop.html', context)


def fresh_desktops(request):
    """Fresh/new desktops only."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='desktop') | Q(computer_type__parent__slug='desktop'),
        is_available=True
    ).filter(
        Q(condition='new') | Q(computer_type__slug='fresh-desktop')
    ).exclude(
        computer_type__slug='slightly-used-desktop'
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/fresh_desktops.html', context)


def used_desktops(request):
    """Slightly used desktops."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='desktop') | Q(computer_type__parent__slug='desktop'),
        is_available=True
    ).filter(
        Q(condition='slightly_used') | Q(computer_type__slug='slightly-used-desktop')
    ).exclude(
        computer_type__slug='fresh-desktop'
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/used_desktops.html', context)


def peripherals(request):
    """All peripherals — from the PeripheralProduct model."""
    products = PeripheralProduct.objects.filter(
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/peripherals.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# NETWORKING — filter NetworkingProduct by device_type field
# ─────────────────────────────────────────────────────────────────────────────

def switches(request):
    """Switches — managed, unmanaged, and PoE."""
    products = NetworkingProduct.objects.filter(
        device_type__in=['switch_unmanaged', 'switch_managed', 'switch_poe'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/switches.html', context)


def routers_modems(request):
    """Routers, Modems, Modem-Router combos, and Access Points."""
    products = NetworkingProduct.objects.filter(
        device_type__in=['router', 'modem', 'modem_router', 'access_point'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/routers_modems.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY / CCTV — filter SecurityCameraProduct by camera_type
# ─────────────────────────────────────────────────────────────────────────────

def security_cameras(request):
    """All CCTV and security camera products."""
    products = SecurityCameraProduct.objects.filter(
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/security_cameras.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# SOFTWARE — filter SoftwareProduct by software_category FK
# ─────────────────────────────────────────────────────────────────────────────

def operatingSystems(request):
    """Operating System software products."""
    products = SoftwareProduct.objects.filter(
        software_category__slug='operating-system',
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'software/operatingSystems.html', context)


def applications(request):
    """Applications — Office Suite, Design, Accounting, etc."""
    products = SoftwareProduct.objects.filter(
        software_category__slug__in=[
            'office-suite', 'design-creative', 'accounting-finance',
            'video-editing', 'point-of-sale-pos'
        ],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'software/applications.html', context)


def developmentTools(request):
    """Development tools and database software."""
    products = SoftwareProduct.objects.filter(
        software_category__slug__in=['development-tools', 'database-software'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'software/developmentTools.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# IT SOLUTIONS (static info pages)
# ─────────────────────────────────────────────────────────────────────────────

def cctv(request):
    return render(request, 'itSolution/CCTVInstallation.html')

def cctvServices(request):
    return render(request, 'itSolution/cctvServices.html')

def hardwareRepairs(request):
    return render(request, 'itSolution/hardwareRepairs.html')

def hardwareServices(request):
    return render(request, 'itSolution/hardwareServices.html')

def networkingSolutions(request):
    return render(request, 'itSolution/networkingSolutions.html')

def networkingServices(request):
    return render(request, 'itSolution/networkingServices.html')


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH HUB
# ─────────────────────────────────────────────────────────────────────────────

def projects(request):
    if request.method == "POST":
        form = ProjectBookingForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("Your project booking has been received! We will contact you soon.")
    else:
        form = ProjectBookingForm()
    return render(request, "research/projects.html", {"form": form})


def seurity(request):
    try:
        research_type = ResearchTypes.objects.get(slug="security")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/security.html', context)


def cloud(request):
    try:
        research_type = ResearchTypes.objects.get(slug="cloud")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/cloud.html', context)


def ai(request):
    try:
        research_type = ResearchTypes.objects.get(slug="ai")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/ai.html', context)


def networking(request):
    try:
        research_type = ResearchTypes.objects.get(slug="networking")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/networking.html', context)


def hadware(request):
    try:
        research_type = ResearchTypes.objects.get(slug="hardware")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/hadware.html', context)
