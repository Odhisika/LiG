from django.shortcuts import render, get_object_or_404
from store.models import Product,Category,ReviewRating, ComputerProduct, SoftwareProduct, PeripheralProduct, HomeBanner
from research.models import BlogModel
from django.shortcuts import render, redirect
from django.http import HttpResponse
from research.form import ProjectBookingForm
from django.db.models import Q
from category.models import ResearchTypes, ComputerTypes, SoftwareTypes
  # Import the form

def home(request):
    products = Product.objects.filter(is_available=True).select_related('category').order_by('-created_date')[:12]
    active_banners = { banner.slide_number: banner for banner in HomeBanner.objects.filter(is_active=True) }
    context = {'products': products, 'banners': active_banners}
    return render(request, 'home.html', context)


def allproducts(request):
    products = Product.objects.filter(is_available=True).select_related('category').order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/allproducts.html', context)





### Hardware ###
def desktops(request):
    products = Product.objects.filter(
        Q(category__slug="desktops") | Q(computerproduct__computer_type__slug="desktop") | Q(computerproduct__computer_type__parent__slug="desktop"),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/desktop.html', context)

def fresh_desktops(request):
    products = Product.objects.filter(
        Q(category__slug="desktops") | Q(computerproduct__computer_type__slug="desktop") | Q(computerproduct__computer_type__parent__slug="desktop"),
        condition='new', is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/fresh_desktops.html', context)

def used_desktops(request):
    products = Product.objects.filter(
        Q(category__slug="desktops") | Q(computerproduct__computer_type__slug="desktop") | Q(computerproduct__computer_type__parent__slug="desktop"),
        condition='slightly_used', is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/used_desktops.html', context)

def fresh_laptops(request):
    products = Product.objects.filter(
        Q(category__slug="laptops") | Q(computerproduct__computer_type__slug="laptop") | Q(computerproduct__computer_type__parent__slug="laptop"),
        condition='new', is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/fresh_laptops.html', context)

def used_laptops(request):
    products = Product.objects.filter(
        Q(category__slug="laptops") | Q(computerproduct__computer_type__slug="laptop") | Q(computerproduct__computer_type__parent__slug="laptop"),
        condition='slightly_used', is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/used_laptops.html', context)

def laptops(request):
    products = Product.objects.filter(
        Q(category__slug="laptops") | Q(computerproduct__computer_type__slug="laptop") | Q(computerproduct__computer_type__parent__slug="laptop"),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/laptop.html', context)

def peripherals(request):
    products = Product.objects.filter(
        Q(category__slug="peripherals") | Q(peripheralproduct__isnull=False),
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'hardware/peripherals.html', context) 


### Software ###
def operatingSystems(request):
    products = Product.objects.filter(
        Q(category__slug="software") | Q(softwareproduct__isnull=False),
        softwareproduct__software_type__icontains="operating",
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'software/operatingSystems.html', context)

def applications(request):
    products = Product.objects.filter(
        Q(category__slug="software") | Q(softwareproduct__isnull=False),
        is_available=True
    ).filter(
        Q(softwareproduct__software_type__icontains="application") | Q(softwareproduct__software_type__icontains="productivity")
    ).distinct().order_by('-created_date')
    return render(request, 'software/applications.html', {'products': products})

def developmentTools(request):
    products = Product.objects.filter(
        Q(category__slug="software") | Q(softwareproduct__isnull=False),
        softwareproduct__software_type__icontains="development",
        is_available=True
    ).distinct().order_by('-created_date')
    context = {'products': products}
    return render(request, 'software/developmentTools.html', context)

### IT solutions ###

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

## Research Hub##





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


