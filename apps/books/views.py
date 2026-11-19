from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BookForm
from .models import Book


@login_required
def book_list(request):
    books = Book.objects.all()
    q = request.GET.get("q", "").strip()
    year = request.GET.get("year", "").strip()
    year_error = ""
    if q:
        books = books.filter(Q(title__icontains=q) | Q(authors__icontains=q))
    if year:
        try:
            books = books.filter(publication_year=int(year))
        except ValueError:
            year_error = "The year must be a whole number, like 1997."
    page_obj = Paginator(books, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "books/book_list.html",
        {"page_obj": page_obj, "q": q, "year": year, "year_error": year_error},
    )


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    active_loans = book.loans.active().select_related("member")
    ratings = book.ratings.select_related("member")
    return render(
        request,
        "books/book_detail.html",
        {"book": book, "active_loans": active_loans, "ratings": ratings},
    )


@login_required
def book_create(request):
    form = BookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        messages.success(request, f"Added “{book}”.")
        return redirect(book)
    return render(request, "books/book_form.html", {"form": form})


@login_required
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = BookForm(request.POST or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Saved changes to “{book}”.")
        return redirect(book)
    return render(request, "books/book_form.html", {"form": form, "book": book})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        try:
            book.delete()
        except ProtectedError:
            messages.error(
                request,
                f"“{book}” has loan records, so it can't be deleted. "
                "Delete its loans first.",
            )
            return redirect(book)
        messages.success(request, f"Deleted “{book}”.")
        return redirect("book_list")
    return render(
        request,
        "confirm_delete.html",
        {
            "object": book,
            "kind": "book",
            "cancel_url": book.get_absolute_url(),
            "warning": "Its ratings will be deleted too."
            if book.ratings.exists()
            else "",
        },
    )
