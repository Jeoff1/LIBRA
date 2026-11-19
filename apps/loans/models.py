from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Least
from django.utils import timezone

from apps.books.models import Book
from apps.members.models import Member

LOAN_DAYS = 14


class LoanQuerySet(models.QuerySet):
    def active(self):
        return self.filter(return_date__isnull=True)

    def overdue(self):
        return self.active().filter(due_date__lt=timezone.localdate())


class Loan(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    borrow_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(
        blank=True, help_text=f"Leave empty for {LOAN_DAYS} days after borrowing."
    )
    return_date = models.DateField(null=True, blank=True)

    objects = LoanQuerySet.as_manager()

    class Meta:
        ordering = ["-borrow_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(due_date__gte=F("borrow_date")),
                name="loan_due_on_or_after_borrow",
                violation_error_message="The due date cannot be before the borrow date.",
            ),
            models.CheckConstraint(
                condition=Q(return_date__isnull=True)
                | Q(return_date__gte=F("borrow_date")),
                name="loan_return_on_or_after_borrow",
                violation_error_message=(
                    "The return date cannot be before the borrow date."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.book} → {self.member}"

    def save(self, *args, **kwargs):
        if self.due_date is None:
            self.due_date = self.borrow_date + timedelta(days=LOAN_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.return_date is None

    @property
    def is_overdue(self):
        return self.is_active and self.due_date < timezone.localdate()

    @property
    def days_overdue(self):
        return (timezone.localdate() - self.due_date).days if self.is_overdue else 0

    @classmethod
    def borrow(cls, member, book, borrow_date=None, due_date=None):
        """Lend one copy of `book` to `member`, or raise ValidationError."""
        with transaction.atomic():
            # A single conditional UPDATE, so two librarians can't both take
            # the last copy.
            taken = Book.objects.filter(pk=book.pk, available_copies__gt=0).update(
                available_copies=F("available_copies") - 1
            )
            if not taken:
                raise ValidationError(f"No copies of “{book}” are available.")
            loan = cls.objects.create(
                member=member,
                book=book,
                borrow_date=borrow_date or timezone.localdate(),
                due_date=due_date,
            )
        book.refresh_from_db(fields=["available_copies"])
        return loan

    def mark_returned(self, return_date=None):
        """Record the return and put the copy back on the shelf."""
        return_date = return_date or timezone.localdate()
        if return_date < self.borrow_date:
            raise ValidationError("The return date cannot be before the borrow date.")
        with transaction.atomic():
            locked = Loan.objects.select_for_update().get(pk=self.pk)
            if locked.return_date is not None:
                raise ValidationError("This loan has already been returned.")
            self.return_date = return_date
            self.save(update_fields=["return_date"])
            _put_copy_back(self.book_id)

    def delete(self, *args, **kwargs):
        """Deleting a loan that is still out puts its copy back."""
        with transaction.atomic():
            if self.is_active:
                _put_copy_back(self.book_id)
            return super().delete(*args, **kwargs)


def _put_copy_back(book_id):
    # Least() keeps the count within total_copies even if a librarian lowered
    # the total while copies were out.
    Book.objects.filter(pk=book_id).update(
        available_copies=Least(F("available_copies") + 1, F("total_copies"))
    )


class Rating(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="ratings")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 (poor) to 5 (excellent).",
    )
    rated_on = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-rated_on", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "book"],
                name="unique_rating_per_member_book",
                violation_error_message="This member has already rated this book.",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=1, score__lte=5),
                name="rating_score_1_to_5",
                violation_error_message="The score must be between 1 and 5.",
            ),
        ]

    def __str__(self):
        return f"{self.member} rated {self.book} {self.score}/5"

    def clean(self):
        if self.member_id and self.book_id:
            borrowed = Loan.objects.filter(
                member_id=self.member_id, book_id=self.book_id
            ).exists()
            if not borrowed:
                raise ValidationError(
                    {"book": "This member can only rate books they have borrowed."}
                )
