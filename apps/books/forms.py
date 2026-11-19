from django import forms

from apps.core.forms import BootstrapFormMixin

from .models import Book


class BookForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            "title",
            "authors",
            "publication_year",
            "isbn",
            "language_code",
            "average_rating",
            "image_url",
            "tags",
            "total_copies",
            "available_copies",
        ]
        help_texts = {
            "authors": "Separate several authors with commas.",
            "publication_year": "Use a negative number for years before 1 AD.",
            "language_code": "For example: eng, en-US, spa.",
        }

    def clean_isbn(self):
        isbn = self.cleaned_data["isbn"].replace("-", "").replace(" ", "").upper()
        if isbn and not (
            len(isbn) in (10, 13) and isbn[:-1].isdigit() and isbn[-1] in "0123456789X"
        ):
            raise forms.ValidationError(
                "Enter a 10- or 13-digit ISBN (dashes and spaces are fine)."
            )
        return isbn

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("total_copies")
        available = cleaned.get("available_copies")
        if total is None or available is None:
            return cleaned
        if total < 1:
            self.add_error("total_copies", "A book needs at least one copy.")
        on_loan = self.instance.loans.active().count() if self.instance.pk else 0
        if available + on_loan > total:
            if on_loan:
                message = (
                    f"{on_loan} copies are on loan, so at most {max(total - on_loan, 0)} "
                    f"of the {total} copies can be available."
                )
            else:
                message = "Available copies cannot be more than total copies."
            self.add_error("available_copies", message)
        return cleaned
