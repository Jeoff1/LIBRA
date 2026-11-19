from django.db import models
from django.urls import reverse
from django.utils import timezone


class Member(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(
        unique=True,
        error_messages={"unique": "A member with this email already exists."},
    )
    phone = models.CharField(max_length=30, blank=True)
    date_joined = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("member_detail", args=[self.pk])

    @property
    def initials(self):
        """'Ann Lee-Park' -> 'AL'."""
        parts = self.name.split()
        return "".join(part[0] for part in parts[:1] + parts[1:][-1:]).upper()
