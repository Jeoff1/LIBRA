from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from apps.books import recommender
from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member

# The landing page's recommendation example: Pride and Prejudice.
DEMO_BOOK_ID = 1885


def _popular_covers(count):
    """The most popular books that have a real cover (dataset order = popularity)."""
    return list(
        Book.objects.filter(goodreads_book_id__isnull=False)
        .exclude(image_url="")
        .exclude(image_url__contains="nophoto")
        .order_by("pk")[:count]
    )


def landing(request):
    """Public front page. Everything else needs a librarian login."""
    covers = _popular_covers(9)
    demo_book = Book.objects.filter(goodreads_book_id=DEMO_BOOK_ID).first()
    return render(
        request,
        "core/landing.html",
        {
            "shelf": [covers[0:3], covers[3:6], covers[6:9]],
            "book_count": Book.objects.count(),
            "demo_book": demo_book,
            "demo_similar": recommender.similar_books(DEMO_BOOK_ID, n=4),
        },
    )


@login_required
def dashboard(request):
    stats = [
        ("Books", Book.objects.count(), "book_list", "bi-book", "brown"),
        ("Members", Member.objects.count(), "member_list", "bi-people", "sage"),
        (
            "Active loans",
            Loan.objects.active().count(),
            "loan_list",
            "bi-arrow-left-right",
            "brown",
        ),
        (
            "Overdue loans",
            Loan.objects.overdue().count(),
            "loan_overdue",
            "bi-alarm",
            "rust",
        ),
    ]
    most_borrowed = (
        Book.objects.annotate(times_borrowed=Count("loans"))
        .filter(times_borrowed__gt=0)
        .order_by("-times_borrowed", "title")[:5]
    )
    overdue = (
        Loan.objects.overdue().select_related("book", "member").order_by("due_date")
    )
    hour = timezone.localtime().hour
    greeting = (
        "Good morning"
        if hour < 12
        else "Good afternoon"
        if hour < 18
        else "Good evening"
    )
    return render(
        request,
        "core/dashboard.html",
        {
            "stats": stats,
            "most_borrowed": most_borrowed,
            "overdue": overdue[:5],
            "greeting": greeting,
            "today": timezone.localdate(),
        },
    )
