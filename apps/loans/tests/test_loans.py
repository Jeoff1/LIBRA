from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member


class LoanTestCase(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)
        self.book = Book.objects.create(
            title="Dune", authors="Frank Herbert", total_copies=2, available_copies=2
        )
        self.ann = Member.objects.create(name="Ann", email="ann@example.com")
        self.bob = Member.objects.create(name="Bob", email="bob@example.com")
        self.today = timezone.localdate()

    def borrow(self, member, **extra):
        data = {"member": member.pk, "borrow_date": self.today.isoformat()}
        data.update(extra)
        return self.client.post(
            f"{reverse('loan_create')}?book={self.book.pk}", data, follow=True
        )

    def copies(self):
        self.book.refresh_from_db()
        return self.book.available_copies


class BorrowReturnTests(LoanTestCase):
    def test_borrow_decreases_and_return_increases_copies(self):
        self.borrow(self.ann)
        self.assertEqual(self.copies(), 1)
        loan = Loan.objects.get()
        self.assertEqual(loan.due_date, self.today + timedelta(days=14))

        self.client.post(reverse("loan_return", args=[loan.pk]))
        self.assertEqual(self.copies(), 2)
        loan.refresh_from_db()
        self.assertEqual(loan.return_date, self.today)

    def test_borrow_blocked_when_no_copies_left(self):
        self.borrow(self.ann)
        self.borrow(self.bob)
        self.assertEqual(self.copies(), 0)

        carol = Member.objects.create(name="Carol", email="carol@example.com")
        response = self.borrow(carol)
        self.assertContains(response, "No copies of")
        self.assertEqual(Loan.objects.count(), 2)
        self.assertEqual(self.copies(), 0)

    def test_member_cannot_borrow_a_second_copy_of_the_same_book(self):
        self.borrow(self.ann)
        response = self.borrow(self.ann)
        self.assertContains(response, "already has a copy of this book on loan")
        self.assertEqual(self.copies(), 1)

    def test_due_date_before_borrow_date_is_rejected(self):
        response = self.borrow(
            self.ann, due_date=(self.today - timedelta(days=1)).isoformat()
        )
        self.assertContains(response, "The due date cannot be before the borrow date")
        self.assertFalse(Loan.objects.exists())

    def test_returning_twice_does_not_add_a_copy(self):
        loan = Loan.borrow(self.ann, self.book)
        self.client.post(reverse("loan_return", args=[loan.pk]))
        response = self.client.post(reverse("loan_return", args=[loan.pk]), follow=True)
        self.assertContains(response, "already been returned")
        self.assertEqual(self.copies(), 2)

    def test_deleting_an_open_loan_puts_the_copy_back(self):
        loan = Loan.borrow(self.ann, self.book)
        self.client.post(reverse("loan_delete", args=[loan.pk]))
        self.assertFalse(Loan.objects.exists())
        self.assertEqual(self.copies(), 2)

    def test_edit_due_date(self):
        loan = Loan.borrow(self.ann, self.book)
        new_due = self.today + timedelta(days=30)
        self.client.post(
            reverse("loan_update", args=[loan.pk]), {"due_date": new_due.isoformat()}
        )
        loan.refresh_from_db()
        self.assertEqual(loan.due_date, new_due)


class OverdueTests(LoanTestCase):
    def test_overdue_list_shows_only_late_open_loans(self):
        long_ago = self.today - timedelta(days=30)
        late = Loan.borrow(self.ann, self.book, borrow_date=long_ago)
        returned_late = Loan.borrow(self.bob, self.book, borrow_date=long_ago)
        returned_late.mark_returned()
        Loan.borrow(self.bob, self.book)  # on time

        response = self.client.get(reverse("loan_overdue"))
        self.assertEqual(list(response.context["loans"]), [late])
        self.assertContains(response, "16 days overdue")
