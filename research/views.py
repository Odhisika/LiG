from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from .form import *
from .models import BlogModel
from django.db.models import Q







def research(request):
    context = {'blogs': BlogModel.objects.all()}
    return render(request, 'research/research.html', context)




def search1(request):
    query = request.GET.get('keyword', '')
    if query:
       
        results = BlogModel.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        ).distinct()
    else:
        results = BlogModel.objects.none()  

    context = {
        'query': query,
        'results': results,
    }
    return render(request, 'research/search_results.html', context)
 


def research_detail(request, slug):
    blog = get_object_or_404(BlogModel, slug=slug)
    return render(request, "research/research-detail.html", {"blog": blog})




def see_blog(request):
    context = {}

    try:
        blog_objs = BlogModel.objects.filter(user=request.user)
        context['blog_objs'] = blog_objs
    except Exception as e:
        print(e)

    print(context)
    return render(request, 'see_blog.html', context)


def add_blog(request):
    context = {'form': BlogForm}
    try:
        if request.method == 'POST':
            form = BlogForm(request.POST)
            print(request.FILES)
            image = request.FILES.get('image', '')
            title = request.POST.get('title')
            user = request.user

            if form.is_valid():
                print('Valid')
                content = form.cleaned_data['content']

            blog_obj = BlogModel.objects.create(
                user=user, title=title,
                content=content, image=image
            )
            print(blog_obj)
            return redirect('/add-blog/')
    except Exception as e:
        print(e)

    return render(request, 'add_blog.html', context)


def blog_update(request, slug):
    context = {}
    try:

        blog_obj = BlogModel.objects.get(slug=slug)

        if blog_obj.user != request.user:
            return redirect('/')

        initial_dict = {'content': blog_obj.content}
        form = BlogForm(initial=initial_dict)
        if request.method == 'POST':
            form = BlogForm(request.POST)
            print(request.FILES)
            image = request.FILES['image']
            title = request.POST.get('title')
            user = request.user

            if form.is_valid():
                content = form.cleaned_data['content']

            blog_obj = BlogModel.objects.create(
                user=user, title=title,
                content=content, image=image
            )

        context['blog_obj'] = blog_obj
        context['form'] = form
    except Exception as e:
        print(e)

    return render(request, 'update_blog.html', context)


def blog_delete(request, id):
    try:
        blog_obj = BlogModel.objects.get(id=id)

        if blog_obj.user == request.user:
            blog_obj.delete()

    except Exception as e:
        print(e)

    return redirect('/see-blog/')



