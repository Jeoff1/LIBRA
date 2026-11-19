from django import forms
from django.utils import timezone

from apps.core.forms import BootstrapFormMixin, DateInput
from apps.members.models import Member

from .models import LOAN_DAYS, Loan


class BorrowForm(BootstrapFormMixin, forms.Form):
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(), empty_label="Choose a member…"
    )
    borrow_date = forms.DateField(initial=timezone.localdate, widget=DateInput())
    due_date = forms.DateField(
        required=False,
        widget=DateInput(),
        help_text=f"Leave empty for {LOAN_DAYS} days after the borrow date.",
    )

    def __init__(self, *args, book, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = book

    def clean_borrow_date(self):
        borrow_date = self.cleaned_data["borrow_date"]
        if borrow_date > timezone.localdate():
            raise forms.ValidationError("The borrow date cannot be in the future.")
        return borrow_date

    def clean(self):
        cleaned = super().clean()
        member = cleaned.get("member")
        borrow_date = cleaned.get("borrow_date")
        due_date = cleaned.get("due_date")
        if borrow_date and due_date and due_date < borrow_date:
            self.add_error("due_date", "The due date cannot be before the borrow date.")
        if (
            member
            and Loan.objects.active().filter(member=member, book=self.book).exists()
        ):
            self.add_error(
                "member", f"{member} already has a copy of this book on loan."
            )
        return cleaned


class LoanUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Loan
        fields = ["due_date"]
        widgets = {"due_date": DateInput()}
        help_texts = {"due_date": ""}

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date is None:
            raise forms.ValidationError("Enter a due date.")
        if due_date < self.instance.borrow_date:
            raise forms.ValidationError(
                f"The due date cannot be before the borrow date "
                f"({self.instance.borrow_date})."
            )
        return due_date
