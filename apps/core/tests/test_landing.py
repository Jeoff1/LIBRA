from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.books.models import Book
from apps.members.models import Member


class LandingPageTests(TestCase):
    def test_landing_is_public_and_links_to_login(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("login"))
        self.assertNotContains(response, "Open dashboard")

    def test_logged_in_librarian_gets_a_dashboard_link(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("landing")), "Open dashboard")

    def test_logout_returns_to_landing(self):
        user = get_user_model().objects.create_user("lib", password="pw", is_staff=True)
        self.client.force_login(user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("landing"))


class DisplayHelperTests(TestCase):
    def test_cover_url_hides_the_no_photo_placeholder(self):
        real = Book(image_url="https://images.gr-assets.com/books/1m/3.jpg")
        placeholder = Book(
            image_url="https://s.gr-assets.com/assets/nophoto/book/111x148.png"
        )
        self.assertEqual(real.cover_url, real.image_url)
        self.assertEqual(placeholder.cover_url, "")

    def test_member_initials(self):
        self.assertEqual(Member(name="ann lee-park").initials, "AL")
        self.assertEqual(Member(name="Cher").initials, "C")
        self.assertEqual(Member(name="Maria Clara de los Santos").initials, "MS")
