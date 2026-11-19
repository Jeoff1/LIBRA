from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.books.models import Book
from apps.members.models import Member

from .forms import BorrowForm, LoanUpdateForm, RatingForm, RatingUpdateForm
from .models import Loan, Rating

LOAN_STATUSES = {
    "active": "On loan",
    "overdue": "Overdue",
    "returned": "Returned",
    "all": "All",
}


def _safe_next(request, fallback):
    """Where to go after an action: ?next= if it points at this site."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return next_url
    return fallback


@login_required
def loan_list(request):
    status = request.GET.get("status", "active")
    if status not in LOAN_STATUSES:
        status = "active"
    loans = Loan.objects.select_related("member", "book")
    if status == "active":
        loans = loans.active()
    elif status == "overdue":
        loans = loans.overdue().order_by("due_date")
    elif status == "returned":
        loans = loans.filter(return_date__isnull=False)
    q = request.GET.get("q", "").strip()
    if q:
        loans = loans.filter(Q(member__name__icontains=q) | Q(book__title__icontains=q))
    page_obj = Paginator(loans, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "loans/loan_list.html",
        {"page_obj": page_obj, "status": status, "statuses": LOAN_STATUSES, "q": q},
    )


@login_required
def loan_overdue(request):
    loans = Loan.objects.overdue().select_related("member", "book").order_by("due_date")
    return render(request, "loans/loan_overdue.html", {"loans": loans})


@login_required
def loan_create(request):
    """Lend a book. Step 1: pick a book (unless ?book= is given). Step 2: the form."""
    member = None
    if request.GET.get("member"):
        member = Member.objects.filter(pk=request.GET["member"]).first()

    book = None
    if request.GET.get("book"):
        book = get_object_or_404(Book, pk=request.GET["book"])
    if book is None:
        q = request.GET.get("q", "").strip()
        books = Book.objects.filter(available_copies__gt=0)
        if q:
            books = books.filter(Q(title__icontains=q) | Q(authors__icontains=q))
        page_obj = Paginator(books, 10).get_page(request.GET.get("page"))
        return render(
            request,
            "loans/loan_pick_book.html",
            {"page_obj": page_obj, "q": q, "member": member},
        )

    form = BorrowForm(request.POST or None, book=book, initial={"member": member})
    if request.method == "POST" and form.is_valid():
        try:
            loan = Loan.borrow(
                form.cleaned_data["member"],
                book,
                borrow_date=form.cleaned_data["borrow_date"],
                due_date=form.cleaned_data["due_date"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(
                request,
                f"Lent “{book}” to {loan.member}. Due back on {loan.due_date}.",
            )
            return redirect(loan.member)
    if request.method == "GET" and not book.available_copies:
        messages.error(request, f"No copies of “{book}” are available right now.")
        return redirect(book)
    return render(
        request,
        "loans/loan_borrow.html",
        {"form": form, "book": book, "member": member},
    )


@login_required
@require_POST
def loan_return(request, pk):
    loan = get_object_or_404(Loan.objects.select_related("book", "member"), pk=pk)
    try:
        loan.mark_returned()
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, f"{loan.member} returned “{loan.book}”.")
    return redirect(_safe_next(request, "loan_list"))


@login_required
def loan_update(request, pk):
    loan = get_object_or_404(Loan.objects.select_related("book", "member"), pk=pk)
    next_url = _safe_next(request, reverse("loan_list"))
    form = LoanUpdateForm(request.POST or None, instance=loan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Due date changed to {loan.due_date}.")
        return redirect(next_url)
    return render(
        request,
        "loans/loan_form.html",
        {"form": form, "loan": loan, "next_url": next_url},
    )


@login_required
def loan_delete(request, pk):
    loan = get_object_or_404(Loan.objects.select_related("book", "member"), pk=pk)
    if request.method == "POST":
        loan.delete()
        messages.success(
            request, f"Deleted the loan of “{loan.book}” to {loan.member}."
        )
        return redirect("loan_list")
    return render(
        request,
        "confirm_delete.html",
        {
            "object": loan,
            "kind": "loan",
            "cancel_url": reverse("loan_list"),
            "warning": (
                "This loan is still open; its copy will go back on the shelf."
                if loan.is_active
                else ""
            ),
        },
    )


@login_required
def rating_list(request):
    ratings = Rating.objects.select_related("member", "book")
    q = request.GET.get("q", "").strip()
    if q:
        ratings = ratings.filter(
            Q(member__name__icontains=q) | Q(book__title__icontains=q)
        )
    page_obj = Paginator(ratings, 20).get_page(request.GET.get("page"))
    return render(request, "loans/rating_list.html", {"page_obj": page_obj, "q": q})


@login_required
def rating_create(request):
    member = None
    if request.GET.get("member"):
        member = get_object_or_404(Member, pk=request.GET["member"])
    initial = {"member": member, "book": request.GET.get("book")}
    form = RatingForm(request.POST or None, member=member, initial=initial)
    if request.method == "POST" and form.is_valid():
        rating = form.save()
        messages.success(
            request,
            f"Saved {rating.member}'s rating of “{rating.book}”: {rating.score}/5.",
        )
        return redirect(rating.member)
    return render(request, "loans/rating_form.html", {"form": form, "member": member})


@login_required
def rating_update(request, pk):
    rating = get_object_or_404(Rating.objects.select_related("member", "book"), pk=pk)
    form = RatingUpdateForm(request.POST or None, instance=rating)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated the rating to {rating.score}/5.")
        return redirect("rating_list")
    return render(request, "loans/rating_form.html", {"form": form, "rating": rating})


@login_required
def rating_delete(request, pk):
    rating = get_object_or_404(Rating.objects.select_related("member", "book"), pk=pk)
    if request.method == "POST":
        rating.delete()
        messages.success(request, "Deleted the rating.")
        return redirect("rating_list")
    return render(
        request,
        "confirm_delete.html",
        {"object": rating, "kind": "rating", "cancel_url": reverse("rating_list")},
    )
