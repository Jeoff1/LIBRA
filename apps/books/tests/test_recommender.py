import tempfile
from pathlib import Path

import joblib
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.books import recommender
from apps.books.models import Book
from apps.loans.models import Loan, Rating
from apps.members.models import Member

# Dataset book_id -> its most similar book_ids, as train_recommender saves it.
SIMILAR = {
    1: [2, 3, 4, 5],
    2: [1, 3, 6, 4],
    3: [1, 2, 4, 6],
    4: [5, 6, 1, 2],
    5: [4, 6, 1, 3],
    6: [4, 5, 2, 3],
}


class RecommenderTestCase(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        joblib.dump(SIMILAR, Path(tmp.name) / recommender.MODEL_FILENAME)
        settings_override = override_settings(ML_MODELS_DIR=tmp.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.books = {
            i: Book.objects.create(
                goodreads_book_id=i,
                title=f"Book {i}",
                authors="Someone",
                total_copies=3,
                available_copies=3,
            )
            for i in SIMILAR
        }
        self.member = Member.objects.create(name="Ann", email="ann@example.com")


class SimilarBooksTests(RecommenderTestCase):
    def test_returns_books_in_similarity_order(self):
        self.assertEqual(
            recommender.similar_books(1, n=3),
            [self.books[2], self.books[3], self.books[4]],
        )

    def test_unknown_or_missing_book_id_gives_nothing(self):
        self.assertEqual(recommender.similar_books(999), [])
        self.assertEqual(recommender.similar_books(None), [])


class RecommendForMemberTests(RecommenderTestCase):
    def test_excludes_books_already_borrowed_or_rated(self):
        Loan.borrow(self.member, self.books[1])
        Loan.borrow(self.member, self.books[2])
        Rating.objects.create(member=self.member, book=self.books[1], score=5)

        recs = recommender.recommend_for_member(self.member, n=10)

        self.assertTrue(recs)
        self.assertNotIn(self.books[1], recs)
        self.assertNotIn(self.books[2], recs)
        # Book 1 was rated 5, so its neighbours lead: 3, then 4, then 5.
        self.assertEqual(recs[:3], [self.books[3], self.books[4], self.books[5]])

    def test_falls_back_to_borrowed_books_without_high_ratings(self):
        Loan.borrow(self.member, self.books[4])
        Rating.objects.create(member=self.member, book=self.books[4], score=2)

        recs = recommender.recommend_for_member(self.member, n=10)

        self.assertNotIn(self.books[4], recs)
        self.assertEqual(recs[:2], [self.books[5], self.books[6]])

    def test_new_member_gets_nothing(self):
        self.assertEqual(recommender.recommend_for_member(self.member), [])


class RecommendationPagesTests(RecommenderTestCase):
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)

    def test_pages_show_recommendations(self):
        Loan.borrow(self.member, self.books[1])
        book_page = self.client.get(reverse("book_detail", args=[self.books[1].pk]))
        self.assertEqual(book_page.context["similar"][0], self.books[2])
        member_page = self.client.get(reverse("member_detail", args=[self.member.pk]))
        self.assertIn(self.books[2], member_page.context["recommendations"])

    def test_pages_still_work_without_a_trained_model(self):
        with override_settings(ML_MODELS_DIR=Path(tempfile.gettempdir()) / "none"):
            for url in (
                reverse("book_detail", args=[self.books[1].pk]),
                reverse("member_detail", args=[self.member.pk]),
            ):
                self.assertContains(
                    self.client.get(url), "Recommendations not trained yet."
                )
