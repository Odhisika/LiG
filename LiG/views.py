from django.shortcuts import render, get_object_or_404
from store.models import Product,Category,ReviewRating, ComputerProduct, SoftwareProduct, PeripheralProduct
from research.models import BlogModel
from django.shortcuts import render, redirect
from django.http import HttpResponse
from research.form import ProjectBookingForm
from category.models import ResearchTypes, ComputerTypes, SoftwareTypes
  # Import the form

def home(request):
    products = Product.objects.all().filter(is_available=True).order_by('created_date')

    # Get the reviews
    reviews = None
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, status=True)

    context = {
        'products': products,
        'reviews': reviews,
    }
    return render(request, 'home.html', context)


def allproducts(request):
    products = Product.objects.all().filter(is_available=True).order_by('created_date')

    # Get the reviews
    reviews = None
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, status=True)

    context = {
        'products': products,
        'reviews': reviews,
    }
    return render(request, 'hardware/allproducts.html', context)





### Hardware ###
def desktops(request):
    try:
        
        desktops_category = ComputerTypes.objects.get(slug="desktop")
        products = ComputerProduct.objects.filter(computer_type=desktops_category, is_available=True)

    except ComputerTypes.DoesNotExist:
        products = []  

    context = {
        'products': products
    }
    return render(request, 'hardware/desktop.html', context)

def laptops(request):
    try:
        
        desktops_category = ComputerTypes.objects.get(slug="laptop")
        products = ComputerProduct.objects.filter(computer_type=desktops_category, is_available=True)

    except ComputerTypes.DoesNotExist:
        products = []  

    context = {
        'products': products
    }
    return render(request, 'hardware/laptop.html',context) 




def peripherals(request):
    try:
        products = PeripheralProduct.objects.all().filter(is_available=True).order_by('created_date')
    except PeripheralProduct.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
    return render(request, 'hardware/peripherals.html', context) 

### Software ###
def operatingSystems(request):
    try:
        operatingSystems_category = SoftwareTypes.objects.get(slug="operating-systems")
        products = SoftwareProduct.objects.filter(software_type=operatingSystems_category, is_available=True)
    except SoftwareProduct.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
    return render(request, 'software/operatingSystems.html', context)

def applications(request):
    try:
        applications_category = SoftwareTypes.objects.get(slug="application")
        products = SoftwareProduct.objects.filter(software_type=applications_category, is_available=True)
    except SoftwareProduct.DoesNotExist:
        products = []
    return render(request, 'software/applications.html', {'products': products})

def developmentTools(request):
    try:
        developmentTools_category = SoftwareTypes.objects.get(slug="development-tools")
        products = SoftwareProduct.objects.filter(software_type=developmentTools_category, is_available=True)
    except SoftwareProduct.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
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


