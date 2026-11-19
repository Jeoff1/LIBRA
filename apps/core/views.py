from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member


@login_required
def dashboard(request):
    stats = [
        ("Books", Book.objects.count(), "book_list", "primary"),
        ("Members", Member.objects.count(), "member_list", "info"),
        ("Active loans", Loan.objects.active().count(), "loan_list", "success"),
        ("Overdue loans", Loan.objects.overdue().count(), "loan_overdue", "danger"),
    ]
    most_borrowed = (
        Book.objects.annotate(times_borrowed=Count("loans"))
        .filter(times_borrowed__gt=0)
        .order_by("-times_borrowed", "title")[:5]
    )
    return render(
        request,
        "core/dashboard.html",
        {"stats": stats, "most_borrowed": most_borrowed},
    )
