import re

from django import forms
from django.utils import timezone

from apps.core.forms import BootstrapFormMixin, DateInput

from .models import Member


class MemberForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ["name", "email", "phone", "date_joined"]
        widgets = {"date_joined": DateInput()}

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if phone and not re.fullmatch(r"\+?[\d\s\-()]{7,20}", phone):
            raise forms.ValidationError(
                "Enter a valid phone number: digits, spaces, dashes, brackets "
                "and an optional leading +."
            )
        return phone

    def clean_date_joined(self):
        date_joined = self.cleaned_data["date_joined"]
        if date_joined > timezone.localdate():
            raise forms.ValidationError("The join date cannot be in the future.")
        return date_joined
