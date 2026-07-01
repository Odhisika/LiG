from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from accounts.models import Account, UserProfile
from accounts.utils.validators import validate_image, validate_email_domain, validate_ghana_phone_number

import re


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter Password',
        'class': 'form-control',
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password',
        'class': 'form-control',
    }))

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'password']

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            return password

        # Run Django's built-in validators (length, similarity, common, numeric)
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(list(e.messages))

        # Custom: require at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")

        # Custom: require at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;~`]', password):
            raise forms.ValidationError("Password must contain at least one special character (!@#$%^&* etc.).")

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password does not match!")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validate_email_domain(email)
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        return validate_ghana_phone_number(phone)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter Last Name'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Enter Phone Number'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('first_name', 'last_name', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        return validate_ghana_phone_number(phone)


class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        validators=[validate_image],
        error_messages={'invalid': "Image files only"},
        widget=forms.FileInput
    )

    class Meta:
        model = UserProfile
        fields = ('address_line_1', 'address_line_2', 'city', 'state', 'country', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
