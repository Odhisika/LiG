from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from .form import *
from .models import BlogModel
from django.db.models import Q
import bleach







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
    allowed_tags = ['p', 'br', 'strong', 'em', 'b', 'i', 'u', 'a', 'ul', 'ol', 'li',
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'code', 'blockquote',
                    'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'div',
                    'span', 'sup', 'sub', 'figure', 'figcaption', 'video', 'source',
                    'iframe']
    allowed_attrs = {
        'a': ['href', 'title', 'rel', 'target'],
        'img': ['src', 'alt', 'width', 'height', 'class'],
        'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen'],
        'video': ['src', 'controls', 'width', 'height'],
        'source': ['src', 'type'],
        '*': ['class', 'id', 'style'],
    }
    allowed_protocols = ['http', 'https', 'mailto']
    blog.sanitized_content = mark_safe(bleach.clean(
        blog.content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=allowed_protocols,
        strip=True
    ))
    return render(request, "research/research-detail.html", {"blog": blog})




def see_blog(request):
    context = {}

    try:
        blog_objs = BlogModel.objects.filter(user=request.user)
        context['blog_objs'] = blog_objs
    except Exception as e:
        pass

    return render(request, 'see_blog.html', context)


def add_blog(request):
    context = {'form': BlogForm}
    try:
        if request.method == 'POST':
            form = BlogForm(request.POST)
            image = request.FILES.get('image', '')
            title = request.POST.get('title')
            user = request.user

            if form.is_valid():
                content = form.cleaned_data['content']

            blog_obj = BlogModel.objects.create(
                user=user, title=title,
                content=content, image=image
            )
            return redirect('/add-blog/')
    except Exception as e:
        pass

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
        pass

    return render(request, 'update_blog.html', context)


def blog_delete(request, id):
    try:
        blog_obj = BlogModel.objects.get(id=id)

        if blog_obj.user == request.user:
            blog_obj.delete()

    except Exception as e:
        pass

    return redirect('/see-blog/')



