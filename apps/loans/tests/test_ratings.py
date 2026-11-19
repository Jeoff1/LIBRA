from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.books.models import Book
from apps.loans.models import Loan, Rating
from apps.members.models import Member


class RatingTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)
        self.ann = Member.objects.create(name="Ann", email="ann@example.com")
        self.dune = Book.objects.create(title="Dune", authors="Frank Herbert")
        self.emma = Book.objects.create(title="Emma", authors="Jane Austen")
        Loan.borrow(self.ann, self.dune)

    def post(self, book, score=5):
        return self.client.post(
            reverse("rating_create"),
            {
                "member": self.ann.pk,
                "book": book.pk,
                "score": score,
                "rated_on": "2026-11-01",
            },
        )

    def test_rate_a_borrowed_book(self):
        response = self.post(self.dune)
        self.assertRedirects(response, self.ann.get_absolute_url())
        self.assertEqual(Rating.objects.get().score, 5)

    def test_cannot_rate_a_book_never_borrowed(self):
        # Emma was never lent out, so it isn't even offered as a choice.
        response = self.post(self.emma)
        self.assertContains(response, "Select a valid choice")
        Loan.borrow(Member.objects.create(name="Bob", email="b@example.com"), self.emma)
        # Now Emma is offered (Bob borrowed it), but Ann still never did.
        response = self.post(self.emma)
        self.assertContains(
            response, "This member can only rate books they have borrowed."
        )
        self.assertFalse(Rating.objects.exists())

    def test_one_rating_per_member_and_book(self):
        self.post(self.dune, score=5)
        response = self.post(self.dune, score=3)
        self.assertContains(response, "This member has already rated this book.")
        self.assertEqual(Rating.objects.get().score, 5)

    def test_score_must_be_1_to_5(self):
        response = self.post(self.dune, score=6)
        self.assertContains(response, "Ensure this value is less than or equal to 5.")

    def test_member_page_form_offers_only_their_unrated_books(self):
        url = f"{reverse('rating_create')}?member={self.ann.pk}"
        books = self.client.get(url).context["form"].fields["book"].queryset
        self.assertEqual(list(books), [self.dune])
        self.post(self.dune)
        books = self.client.get(url).context["form"].fields["book"].queryset
        self.assertEqual(list(books), [])

    def test_edit_and_delete(self):
        self.post(self.dune, score=5)
        rating = Rating.objects.get()
        self.client.post(
            reverse("rating_update", args=[rating.pk]),
            {"score": 2, "rated_on": "2026-11-02"},
        )
        rating.refresh_from_db()
        self.assertEqual(rating.score, 2)
        self.client.post(reverse("rating_delete", args=[rating.pk]))
        self.assertFalse(Rating.objects.exists())
