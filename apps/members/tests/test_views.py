from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.books.models import Book
from apps.loans.models import Loan
from apps.members.models import Member


class MemberCrudTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)

    def test_create_update_delete(self):
        response = self.client.post(
            reverse("member_create"),
            {
                "name": "Ann Lee",
                "email": "Ann@Example.com",
                "date_joined": "2026-01-05",
            },
        )
        member = Member.objects.get()
        self.assertRedirects(response, member.get_absolute_url())
        self.assertEqual(member.email, "ann@example.com")

        self.client.post(
            reverse("member_update", args=[member.pk]),
            {
                "name": "Ann Lee-Park",
                "email": "ann@example.com",
                "phone": "+1 (555) 010-2030",
                "date_joined": "2026-01-05",
            },
        )
        member.refresh_from_db()
        self.assertEqual(member.name, "Ann Lee-Park")
        self.assertEqual(member.phone, "+1 (555) 010-2030")

        response = self.client.post(reverse("member_delete", args=[member.pk]))
        self.assertRedirects(response, reverse("member_list"))
        self.assertFalse(Member.objects.exists())

    def test_duplicate_email_and_bad_phone_are_rejected(self):
        Member.objects.create(name="Ann", email="ann@example.com")
        response = self.client.post(
            reverse("member_create"),
            {
                "name": "Other Ann",
                "email": "ANN@example.com",
                "phone": "call me",
                "date_joined": "2026-01-05",
            },
        )
        self.assertContains(response, "A member with this email already exists.")
        self.assertContains(response, "Enter a valid phone number")

    def test_delete_blocked_when_member_has_loans(self):
        member = Member.objects.create(name="Ann", email="ann@example.com")
        Loan.borrow(member, Book.objects.create(title="Dune", authors="F. Herbert"))
        response = self.client.post(
            reverse("member_delete", args=[member.pk]), follow=True
        )
        self.assertContains(response, "has loan records")
        self.assertTrue(Member.objects.filter(pk=member.pk).exists())
