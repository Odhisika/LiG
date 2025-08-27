from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta


from accounts.forms import RegistrationForm, UserForm, UserProfileForm
from accounts.models import Account, UserProfile
from orders.models import Order, OrderProduct
from cart.views import _cart_id
from cart.models import Cart, CartItem
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator


def transfer_guest_cart_to_user(request, user):
    """
    Transfer items from guest cart (session-based) to user cart after login
    """
    try:
        # Get the guest cart
        guest_cart = Cart.objects.get(cart_id=_cart_id(request))
        guest_cart_items = CartItem.objects.filter(cart=guest_cart)
        
        for guest_item in guest_cart_items:
            try:
                # Check if user already has this product in their cart
                user_cart_item = CartItem.objects.get(
                    product=guest_item.product, 
                    user=user
                )
                # If exists, add the quantities together
                user_cart_item.quantity += guest_item.quantity
                user_cart_item.save()
                # Delete the guest cart item since it's been merged
                guest_item.delete()
            except CartItem.DoesNotExist:
                # If doesn't exist, transfer the cart item to the user
                guest_item.user = user
                guest_item.cart = None  # Remove cart association
                guest_item.save()
        
        # Delete the guest cart after all items are transferred
        if not CartItem.objects.filter(cart=guest_cart).exists():
            guest_cart.delete()
            
    except Cart.DoesNotExist:
        # No guest cart exists, nothing to transfer
        pass


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]

            # Create user
            user = Account.objects.create_user(
                first_name=first_name, 
                last_name=last_name, 
                email=email, 
                username=username, 
                password=password
            )
            user.phone_number = phone_number
            user.save()

            # Create a user profile
            profile = UserProfile.objects.create(
                user=user,
                profile_picture='default/default-user.png'
            )

            # USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),  # Fixed syntax issue
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            
            try:
                send_email = EmailMessage(mail_subject, message, to=[to_email])
                send_email.send()
            except Exception as e:
                print(f"Email sending failed: {e}")  # Log the error for debugging

            # Redirect to login with verification message
            redirect_url = reverse('login') + f"?command=verification&email={email}"
            return redirect(redirect_url)

    else:
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'accounts/register.html', context)


def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Authenticate using email
        user = auth.authenticate(username=email, password=password)  # Use 'username' instead of 'email'

        if user:
            # Transfer guest cart items to user BEFORE logging in
            transfer_guest_cart_to_user(request, user)
            
            # Now log in the user
            auth.login(request, user)
            messages.success(request, 'You are now logged in.')
            
            # Handle redirect - prioritize checkout if that's where they came from
            next_url = request.GET.get('next')
            if next_url:
                # If they were trying to access checkout, redirect there
                if 'checkout' in next_url:
                    return redirect('checkout')
                else:
                    return redirect(next_url)
            else:
                # Default redirect to cart to show merged items, then to home
                return redirect('cart')
        else:
            messages.error(request, 'Invalid login credentials')
    
    return render(request, 'accounts/login.html')



@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')


@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    print(f"Orders count for {request.user}: {orders.count()}")
    
    context = {
        'orders_count': orders.count(),
        'userprofile': user_profile,
    
    }
    return render(request, 'accounts/dashboard.html', context)


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        try:
            user = Account.objects.get(email=email)
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            EmailMessage(mail_subject, message, to=[email]).send()
            messages.success(request, 'Password reset email sent.')
        except Account.DoesNotExist:
            messages.error(request, 'Account does not exist!')
    
    return render(request, 'accounts/forgotPassword.html')


def reset_password_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request, 'Invalid or expired reset link')
        return redirect('login')


def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match!')
    
    return render(request, 'accounts/resetPassword.html')

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('change_password')
    return render(request, 'accounts/change_password.html')





@login_required
def my_orders(request):
    """
    Display user's order history with pagination and statistics
    """
    # Get all orders for the current user
    all_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate statistics on ALL orders (before filtering)
    total_spent = all_orders.aggregate(total=Sum('order_total'))['total'] or 0
    
    # Get orders from this year
    current_year = timezone.now().year
    orders_this_year = all_orders.filter(created_at__year=current_year).count()
    
    # Start with all orders for filtering
    orders = all_orders
    
    # Handle search and filtering
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=filter_date)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,  # This will be used in the template for the table
        'all_orders': all_orders,  # This is for the statistics
        'total_spent': total_spent,
        'orders_this_year': orders_this_year,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/my_orders.html', context)


@login_required(login_url='login')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
    
    return render(request, 'accounts/edit_profile.html', {
        'user_form': UserForm(instance=request.user),
        'profile_form': UserProfileForm(instance=userprofile),
        'userprofile': userprofile,
    })


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_number=order_id)
    order_detail = OrderProduct.objects.filter(order=order)
    subtotal = sum(item.product_price * item.quantity for item in order_detail)
    
    return render(request, 'accounts/order_detail.html', {'order_detail': order_detail, 'order': order, 'subtotal': subtotal})