from django.shortcuts import render
from store.models import Product,Category,ReviewRating
from research.models import BlogModel
from django.shortcuts import render, redirect
from django.http import HttpResponse
from research.form import ProjectBookingForm
from category.models import ResearchTypes
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
        desktops_category = Category.objects.get(category_name="Desktop")
        products = Product.objects.filter(category=desktops_category, is_available=True)
    except Category.DoesNotExist:
        products = []

    context = {
        'products': products
    }
    return render(request, 'hardware/desktop.html',context)  


def laptops(request):
    try:
        laptops_category = Category.objects.get(category_name="Laptops")
        products = Product.objects.filter(category=laptops_category, is_available=True)
    except Category.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
    return render(request, 'hardware/laptop.html',context)  

def peripherals(request):
    try:
        laptops_category = Category.objects.get(category_name="Peripherals")
        products = Product.objects.filter(category=laptops_category, is_available=True)
    except Category.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
    return render(request, 'hardware/peripherals.html', context) 

### Software ###
def operatingSystems(request):
    try:
        operatingSystems_category = Category.objects.get(category_name="Operating Systems")
        products = Product.objects.filter(category=operatingSystems_category, is_available=True)
    except Category.DoesNotExist:
        products = []
    
    context = {
        'products': products
    }
    return render(request, 'software/operatingSystems.html', context)

def applications(request):
    try:
        applications_category = Category.objects.get(category_name="Applications")
        products = Product.objects.filter(category=applications_category, is_available=True)
    except Category.DoesNotExist:
        products = []
    return render(request, 'software/applications.html', {'products': products})

def developmentTools(request):
    try:
        developmentTools_category = Category.objects.get(category_name="Development Tools")
        products = Product.objects.filter(category=developmentTools_category, is_available=True)
    except Category.DoesNotExist:
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


