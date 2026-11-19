from django.contrib import admin

from .models import Loan, Rating


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["book", "member", "borrow_date", "due_date", "return_date"]
    list_filter = ["borrow_date", "return_date"]
    search_fields = ["book__title", "member__name", "member__email"]
    autocomplete_fields = ["book", "member"]

    def delete_queryset(self, request, queryset):
        # Delete one by one so Loan.delete() puts copies back.
        for loan in queryset:
            loan.delete()


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["member", "book", "score", "rated_on"]
    list_filter = ["score"]
    search_fields = ["book__title", "member__name"]
    autocomplete_fields = ["book", "member"]
