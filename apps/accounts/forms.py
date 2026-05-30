"""
Nova Capital Group - Accounts Forms
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 234 567 8900'})
    )
    country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'País'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'country', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrónico ya está registrado.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].split('@')[0] + str(User.objects.count())
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.country = self.cleaned_data.get('country', '')
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'country', 'city', 'address', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Las contraseñas no coinciden.')
        return cleaned_data
