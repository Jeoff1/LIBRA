from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member


class DashboardTests(TestCase):
    def test_counts_and_most_borrowed(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)
        dune = Book.objects.create(
            title="Dune", authors="F", total_copies=3, available_copies=3
        )
        emma = Book.objects.create(
            title="Emma", authors="J", total_copies=3, available_copies=3
        )
        Book.objects.create(title="Never lent", authors="X")
        ann = Member.objects.create(name="Ann", email="ann@example.com")
        bob = Member.objects.create(name="Bob", email="bob@example.com")
        month_ago = timezone.localdate() - timedelta(days=30)
        Loan.borrow(ann, dune, borrow_date=month_ago)  # overdue
        Loan.borrow(bob, dune).mark_returned()
        Loan.borrow(bob, emma)

        response = self.client.get(reverse("dashboard"))

        counts = {label: count for label, count, *_ in response.context["stats"]}
        self.assertEqual(
            counts,
            {"Books": 3, "Members": 2, "Active loans": 2, "Overdue loans": 1},
        )
        self.assertEqual(list(response.context["most_borrowed"]), [dune, emma])
