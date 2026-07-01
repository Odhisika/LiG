from django import forms
from django.core.exceptions import ValidationError
from froala_editor.widgets import FroalaEditor
from .models import *
from .models import ProjectBooking
from accounts.utils.validators import validate_email_domain


class BlogForm(forms.ModelForm):
    class Meta:
        model = BlogModel
        fields = ['title', 'content']


class ProjectBookingForm(forms.ModelForm):
    class Meta:
        model = ProjectBooking
        fields = ['name', 'email', 'university', 'project_details']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validate_email_domain(email)
        return email
