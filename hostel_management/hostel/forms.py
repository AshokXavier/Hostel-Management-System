from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from . models import StudentProfile

class StudentRegistrationForm(UserCreationForm):

  email=forms.EmailField(required=True)
  phone=forms.CharField(max_length=15)
  department=forms.CharField(max_length=50)
  academic_year=forms.CharField(max_length=20)
  address=forms.CharField(
    widget=forms.Textarea(attrs={'row':3})
  )

  class Meta:

    model=User

    fields=[
      'username',
      'email',
    ]


  @transaction.atomic
  def save(self,commit=True):

    user=super().save(commit=False)
    user.email=self.cleaned_data['email']
    if commit:
      user.save()

      StudentProfile.objects.create(
        user=user,
        phone=self.cleaned_data['phone'],
        department=self.cleaned_data['department'],
        academic_year=self.cleaned_data['academic_year'],
        address=self.cleaned_data['address']
      )

    return user



class UserEmailForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['email']


class StudentProfileForm(forms.ModelForm):

    class Meta:
        model = StudentProfile
        fields = [
            'phone',
            'department',
            'academic_year',
            'address'
        ]

        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }