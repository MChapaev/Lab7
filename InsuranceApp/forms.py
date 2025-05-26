from django import forms
from .models import Client, Policy, Claim
from django.core.exceptions import ValidationError
import re
from datetime import date

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['full_name', 'birth_date', 'passport_number', 'phone', 'email']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_passport_number(self):
        passport = self.cleaned_data['passport_number']
        if not re.match(r'^[A-Za-z0-9]{4,50}$', passport):
            raise ValidationError("Passport number must be 4-50 alphanumeric characters.")
        return passport

    def clean_birth_date(self):
        birth_date = self.cleaned_data['birth_date']
        if birth_date > date.today():
            raise ValidationError("Birth date cannot be in the future.")
        return birth_date

class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['policy_type', 'start_date', 'end_date', 'premium']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_premium(self):
        premium = self.cleaned_data['premium']
        if premium <= 0:
            raise ValidationError("Premium must be positive.")
        return premium

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise ValidationError("End date must be after start date.")
        return cleaned_data

class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['claim_date', 'description', 'amount']
        widgets = {
            'claim_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < 0:
            raise ValidationError("Amount must be non-negative.")
        return amount

class DeleteClientForm(forms.Form):
    client_id = forms.IntegerField(label="Client ID")

    def clean_client_id(self):
        client_id = self.cleaned_data['client_id']
        if not Client.objects.filter(id=client_id).exists():
            raise ValidationError("Client with this ID does not exist.")
        return client_id