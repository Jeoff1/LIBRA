from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse


class Book(models.Model):
    # The dataset's book_id (a Goodreads ID). The recommender's output is keyed
    # by it. Empty for books a librarian adds by hand.
    goodreads_book_id = models.PositiveIntegerField(
        "Goodreads book ID", unique=True, null=True, blank=True
    )
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=1000)
    # Negative years are works from before 1 AD.
    publication_year = models.IntegerField(
        null=True, blank=True, validators=[MaxValueValidator(2100)]
    )
    isbn = models.CharField("ISBN", max_length=13, blank=True)
    language_code = models.CharField(max_length=10, blank=True)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    image_url = models.URLField("Cover image URL", max_length=500, blank=True)
    tags = models.CharField(
        max_length=500, blank=True, help_text="Top tags, separated by commas."
    )
    total_copies = models.PositiveSmallIntegerField(default=1)
    available_copies = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(available_copies__lte=F("total_copies")),
                name="book_available_lte_total",
                violation_error_message=(
                    "Available copies cannot be more than total copies."
                ),
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("book_detail", args=[self.pk])

    @property
    def cover_url(self):
        """The cover image, or "" when the dataset only has a "no photo" image."""
        if not self.image_url or "nophoto" in self.image_url:
            return ""
        return self.image_url

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
