from django.shortcuts import render, get_object_or_404
from store.models import Product, Category, ReviewRating, ComputerProduct, SoftwareProduct, PeripheralProduct, NetworkingProduct, UPSProduct, SecurityCameraProduct, HomeBanner
from research.models import BlogModel
from django.shortcuts import render, redirect
from django.http import HttpResponse
from research.form import ProjectBookingForm
from django.db.models import Q
from category.models import ResearchTypes, ComputerTypes, SoftwareTypes
from accounts.models import NewsletterSubscriber
from django.core.exceptions import ValidationError
from accounts.utils.validators import validate_email_domain
from django.contrib import messages


def home(request):
    products = Product.objects.filter(is_available=True).select_related('category').order_by('?')[:12]
    active_banners = {banner.slide_number: banner for banner in HomeBanner.objects.filter(is_active=True)}
    context = {'products': products, 'banners': active_banners}
    return render(request, 'home.html', context)


def allproducts(request):
    products = Product.objects.filter(is_available=True).exclude(softwareproduct__isnull=False).select_related('category').order_by('?')
    context = {'products': products}
    return render(request, 'hardware/allproducts.html', context)


def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            try:
                validate_email_domain(email)
            except ValidationError as e:
                messages.error(request, e.message)
                return redirect(request.META.get('HTTP_REFERER', 'home'))
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


def computers_all(request):
    """All computer products across laptop, desktop, and related types."""
    products = ComputerProduct.objects.filter(
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/computers.html', context)


def all_in_one_computers(request):
    """All-in-one desktops."""
    products = ComputerProduct.objects.filter(
        Q(computer_type__slug='all-in-one') | Q(computer_type__slug='all-in-one-desktop'),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/all_in_one.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# NETWORKING — filter NetworkingProduct by device_type field
# ─────────────────────────────────────────────────────────────────────────────

def networking_all(request):
    """All networking products (Switches, Routers, Modems, Access Points)."""
    products = NetworkingProduct.objects.filter(
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/networking.html', context)

def switches(request):
    """Switches — managed, unmanaged, and PoE."""
    products = NetworkingProduct.objects.filter(
        device_type__in=['switch_unmanaged', 'switch_managed', 'switch_poe'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/switches.html', context)


def routers_modems(request):
    """Routers, modems, and modem-router combos."""
    products = NetworkingProduct.objects.filter(
        device_type__in=['router', 'modem', 'modem_router'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/routers_modems.html', context)


def access_points(request):
    """Wireless access points."""
    products = NetworkingProduct.objects.filter(
        device_type='access_point',
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/access_points.html', context)


def ups(request):
    """UPS units — standalone product type."""
    products = UPSProduct.objects.filter(
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/ups.html', context)


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


def ip_cameras(request):
    """Camera units excluding kits and recorders."""
    products = SecurityCameraProduct.objects.filter(
        is_available=True
    ).exclude(
        camera_type__in=['cctv_kit', 'nvr', 'dvr']
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/ip_cameras.html', context)


def cctv_kits(request):
    """Complete CCTV kits."""
    products = SecurityCameraProduct.objects.filter(
        camera_type='cctv_kit',
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/cctv_kits.html', context)


def nvr_dvr(request):
    """NVR and DVR products."""
    products = SecurityCameraProduct.objects.filter(
        camera_type__in=['nvr', 'dvr'],
        is_available=True
    ).order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/nvr_dvr.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# SOFTWARE — filter SoftwareProduct by software_category FK
# ─────────────────────────────────────────────────────────────────────────────

SOFTWARE_APPLICATION_SLUGS = [
    'office-suite',
    'design-creative',
    'accounting-finance',
    'video-editing',
    'point-of-sale-pos',
]

SOFTWARE_SECURITY_UTILITY_SLUGS = [
    'antivirus-security',
    'remote-desktop-vpn',
    'backup-recovery',
    'network-management',
]

SOFTWARE_DEVELOPMENT_SLUGS = [
    'development-tools',
    'database-software',
]


def _software_collection_products(*slugs):
    queryset = SoftwareProduct.objects.filter(is_available=True)
    if slugs:
        queryset = queryset.filter(software_category__slug__in=slugs)
    return queryset.order_by('-created_date')


def _render_software_collection(
    request,
    products,
    *,
    page_title,
    page_subtitle,
    hero_title,
    hero_subtitle,
    empty_message,
    empty_icon,
):
    for product in products:
        product.platforms_list = (
            [p.strip() for p in product.platforms.split(',') if p.strip()]
            if product.platforms else []
        )

    context = {
        'products': products,
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'hero_title': hero_title,
        'hero_subtitle': hero_subtitle,
        'empty_message': empty_message,
        'empty_icon': empty_icon,
    }
    return render(request, 'software/software_solutions.html', context)


def software_all(request):
    """All software products."""
    products = _software_collection_products()
    return _render_software_collection(
        request,
        products,
        page_title='All Software',
        page_subtitle='Operating systems, business apps, security tools, and development products',
        hero_title='Licensed Software for Work and Growth',
        hero_subtitle='Explore the full software catalogue from productivity tools to technical platforms',
        empty_message='No software products are available at the moment.',
        empty_icon='fa-layer-group',
    )

def operatingSystems(request):
    """Operating System software products."""
    products = _software_collection_products('operating-system')
    return _render_software_collection(
        request,
        products,
        page_title='Operating Systems',
        page_subtitle='Genuine OS licences for stability, security, and compatibility',
        hero_title='Modern Software Solutions',
        hero_subtitle='Empower your productivity with genuine digital tools',
        empty_message='No Operating Systems available at the moment.',
        empty_icon='fa-compact-disc',
    )


def applications(request):
    """Applications — Office Suite, Design, Accounting, etc."""
    products = _software_collection_products(*SOFTWARE_APPLICATION_SLUGS)
    return _render_software_collection(
        request,
        products,
        page_title='Applications',
        page_subtitle='Office, creative, finance, editing, and point-of-sale software',
        hero_title='Premium Applications',
        hero_subtitle='Boost your productivity with professional software',
        empty_message='No Applications available at the moment.',
        empty_icon='fa-app-store',
    )


def office_suite(request):
    products = _software_collection_products('office-suite')
    return _render_software_collection(
        request,
        products,
        page_title='Office Suite',
        page_subtitle='Document, spreadsheet, presentation, and collaboration tools',
        hero_title='Office Software for Daily Work',
        hero_subtitle='Equip teams with essential productivity apps for communication and reporting',
        empty_message='No Office Suite software is available at the moment.',
        empty_icon='fa-file-word',
    )


def design_creative(request):
    products = _software_collection_products('design-creative')
    return _render_software_collection(
        request,
        products,
        page_title='Design & Creative',
        page_subtitle='Graphics, layout, branding, and creative production software',
        hero_title='Creative Tools for Production Teams',
        hero_subtitle='Power design, content, and brand work with professional creative software',
        empty_message='No Design & Creative software is available at the moment.',
        empty_icon='fa-palette',
    )


def accounting_finance(request):
    products = _software_collection_products('accounting-finance')
    return _render_software_collection(
        request,
        products,
        page_title='Accounting & Finance',
        page_subtitle='Billing, bookkeeping, reporting, and finance operations tools',
        hero_title='Financial Software for Accurate Operations',
        hero_subtitle='Manage invoicing, records, payroll, and reporting with trusted platforms',
        empty_message='No Accounting & Finance software is available at the moment.',
        empty_icon='fa-calculator',
    )


def video_editing(request):
    products = _software_collection_products('video-editing')
    return _render_software_collection(
        request,
        products,
        page_title='Video Editing',
        page_subtitle='Editing, timeline, post-production, and export tools',
        hero_title='Video Software for Modern Content Teams',
        hero_subtitle='Edit and deliver polished media with capable production software',
        empty_message='No Video Editing software is available at the moment.',
        empty_icon='fa-film',
    )


def point_of_sale(request):
    products = _software_collection_products('point-of-sale-pos')
    return _render_software_collection(
        request,
        products,
        page_title='Point of Sale',
        page_subtitle='Retail, sales desk, and transaction software for front-office teams',
        hero_title='POS Systems for Faster Sales',
        hero_subtitle='Run counters, checkouts, and inventory-driven sales workflows efficiently',
        empty_message='No Point of Sale software is available at the moment.',
        empty_icon='fa-cash-register',
    )


def security_utilities(request):
    """Security and utility software products."""
    products = _software_collection_products(*SOFTWARE_SECURITY_UTILITY_SLUGS)
    return _render_software_collection(
        request,
        products,
        page_title='Security & Utilities',
        page_subtitle='Protection, access, backup, and systems management software',
        hero_title='Protect, Recover, and Manage Systems',
        hero_subtitle='Secure devices, recover data, and control infrastructure with dependable utilities',
        empty_message='No Security & Utility software is available at the moment.',
        empty_icon='fa-shield-alt',
    )


def antivirus_security(request):
    products = _software_collection_products('antivirus-security')
    return _render_software_collection(
        request,
        products,
        page_title='Antivirus & Security',
        page_subtitle='Endpoint protection, scanning, and security licensing',
        hero_title='Security Software for Safer Devices',
        hero_subtitle='Defend laptops, desktops, and servers with trusted protection tools',
        empty_message='No Antivirus & Security software is available at the moment.',
        empty_icon='fa-shield-virus',
    )


def remote_desktop_vpn(request):
    products = _software_collection_products('remote-desktop-vpn')
    return _render_software_collection(
        request,
        products,
        page_title='Remote Desktop & VPN',
        page_subtitle='Remote access, encrypted tunnelling, and distributed work tools',
        hero_title='Remote Access Tools for Hybrid Teams',
        hero_subtitle='Connect staff securely to systems, servers, and internal resources from anywhere',
        empty_message='No Remote Desktop & VPN software is available at the moment.',
        empty_icon='fa-network-wired',
    )


def backup_recovery(request):
    products = _software_collection_products('backup-recovery')
    return _render_software_collection(
        request,
        products,
        page_title='Backup & Recovery',
        page_subtitle='Data protection, restore workflows, and continuity software',
        hero_title='Backup Platforms for Business Continuity',
        hero_subtitle='Protect critical files and restore operations quickly when systems fail',
        empty_message='No Backup & Recovery software is available at the moment.',
        empty_icon='fa-database',
    )


def network_management(request):
    products = _software_collection_products('network-management')
    return _render_software_collection(
        request,
        products,
        page_title='Network Management',
        page_subtitle='Monitoring, configuration, visibility, and control software',
        hero_title='Software for Managing Network Operations',
        hero_subtitle='Monitor devices, diagnose issues, and keep infrastructure under control',
        empty_message='No Network Management software is available at the moment.',
        empty_icon='fa-sitemap',
    )


def developmentTools(request):
    """Development tools and database software."""
    products = _software_collection_products(*SOFTWARE_DEVELOPMENT_SLUGS)
    return _render_software_collection(
        request,
        products,
        page_title='Development',
        page_subtitle='Developer platforms, IDEs, SDKs, and database software',
        hero_title='Build the Future',
        hero_subtitle='Professional tools for developers, engineers, and technical teams',
        empty_message='No Development software is available at the moment.',
        empty_icon='fa-code',
    )


def development_tools_only(request):
    products = _software_collection_products('development-tools')
    return _render_software_collection(
        request,
        products,
        page_title='Development Tools',
        page_subtitle='Coding environments, compilers, toolchains, and technical utilities',
        hero_title='Tools for Productive Engineering Teams',
        hero_subtitle='Support software engineering workflows with capable build and coding tools',
        empty_message='No Development Tools are available at the moment.',
        empty_icon='fa-code',
    )


def database_software(request):
    products = _software_collection_products('database-software')
    return _render_software_collection(
        request,
        products,
        page_title='Database Software',
        page_subtitle='Database engines, management tools, and data platform software',
        hero_title='Data Platforms for Structured Workloads',
        hero_subtitle='Deploy and manage business data with reliable database software',
        empty_message='No Database Software is available at the moment.',
        empty_icon='fa-server',
    )


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


def security(request):
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


def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

def hardware(request):
    try:
        research_type = ResearchTypes.objects.get(slug="hardware")
        blogs = BlogModel.objects.filter(research_type=research_type)
    except ResearchTypes.DoesNotExist:
        blogs = []
    context = {'blogs': blogs}
    return render(request, 'research/hardware.html', context)
