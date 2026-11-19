from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member


def make_book(**kwargs):
    defaults = {"title": "Dune", "authors": "Frank Herbert", "publication_year": 1965}
    defaults.update(kwargs)
    return Book.objects.create(**defaults)


class LibrarianTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "librarian", password="pw", is_staff=True
        )
        self.client.force_login(self.user)


class LoginRequiredTests(TestCase):
    def test_pages_redirect_to_login(self):
        book = make_book()
        for url in (
            reverse("dashboard"),
            reverse("book_list"),
            reverse("book_detail", args=[book.pk]),
            reverse("book_create"),
        ):
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")


class BookListTests(LibrarianTestCase):
    def test_search_matches_title_or_author_and_filters_year(self):
        make_book(title="Dune", authors="Frank Herbert", publication_year=1965)
        make_book(title="Emma", authors="Jane Austen", publication_year=1815)

        response = self.client.get(reverse("book_list"), {"q": "austen"})
        self.assertEqual([b.title for b in response.context["page_obj"]], ["Emma"])

        response = self.client.get(reverse("book_list"), {"year": "1965"})
        self.assertEqual([b.title for b in response.context["page_obj"]], ["Dune"])

    def test_bad_year_shows_error_instead_of_crashing(self):
        response = self.client.get(reverse("book_list"), {"year": "abc"})
        self.assertContains(response, "The year must be a whole number")


class BookCrudTests(LibrarianTestCase):
    def form_data(self, **overrides):
        data = {
            "title": "Dune",
            "authors": "Frank Herbert",
            "publication_year": 1965,
            "isbn": "0-441-17271-7",
            "total_copies": 3,
            "available_copies": 3,
        }
        data.update(overrides)
        return data

    def test_create(self):
        response = self.client.post(reverse("book_create"), self.form_data())
        book = Book.objects.get()
        self.assertRedirects(response, book.get_absolute_url())
        self.assertEqual(book.isbn, "0441172717")
        self.assertEqual(book.goodreads_book_id, None)

    def test_create_rejects_more_available_than_total(self):
        response = self.client.post(
            reverse("book_create"), self.form_data(available_copies=4)
        )
        self.assertContains(response, "cannot be more than total copies")
        self.assertFalse(Book.objects.exists())

    def test_create_rejects_bad_isbn(self):
        response = self.client.post(reverse("book_create"), self.form_data(isbn="12"))
        self.assertContains(response, "Enter a 10- or 13-digit ISBN")

    def test_update(self):
        book = make_book()
        response = self.client.post(
            reverse("book_update", args=[book.pk]), self.form_data(title="Dune Messiah")
        )
        self.assertRedirects(response, book.get_absolute_url())
        book.refresh_from_db()
        self.assertEqual(book.title, "Dune Messiah")

    def test_update_counts_copies_on_loan(self):
        book = make_book(total_copies=2, available_copies=2)
        member = Member.objects.create(name="Ann", email="ann@example.com")
        Loan.borrow(member, book)
        # 1 copy is out, so 2 available of 2 total is impossible.
        response = self.client.post(
            reverse("book_update", args=[book.pk]),
            self.form_data(total_copies=2, available_copies=2),
        )
        self.assertContains(response, "1 copies are on loan")

    def test_delete(self):
        book = make_book()
        response = self.client.post(reverse("book_delete", args=[book.pk]))
        self.assertRedirects(response, reverse("book_list"))
        self.assertFalse(Book.objects.exists())

    def test_delete_blocked_when_book_has_loans(self):
        book = make_book()
        member = Member.objects.create(name="Ann", email="ann@example.com")
        Loan.borrow(member, book)
        response = self.client.post(reverse("book_delete", args=[book.pk]), follow=True)
        self.assertContains(response, "has loan records")
        self.assertTrue(Book.objects.filter(pk=book.pk).exists())
