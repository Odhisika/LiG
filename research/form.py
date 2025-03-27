from django import forms
from froala_editor.widgets import FroalaEditor
from .models import *
from .models import ProjectBooking


class BlogForm(forms.ModelForm):
    class Meta:
        model = BlogModel
        fields = ['title', 'content']





class ProjectBookingForm(forms.ModelForm):
    class Meta:
        model = ProjectBooking
        fields = ['name', 'email', 'university', 'project_details']
