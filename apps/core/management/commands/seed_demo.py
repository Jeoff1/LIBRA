import random
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.books.models import Book
from apps.loans.models import Loan, Rating
from apps.members.models import Member

FIRST_NAMES = [
    "Alex", "Bea", "Carlos", "Dana", "Eli", "Fatima", "Gabe", "Hana", "Ivan",
    "Jade", "Kofi", "Lena", "Marco", "Nadia", "Omar", "Priya", "Quinn", "Rosa",
    "Sam", "Tara",
]  # fmt: skip
LAST_NAMES = [
    "Reyes", "Santos", "Cruz", "Garcia", "Lim", "Tan", "Bautista", "Ramos",
    "Mendoza", "Torres", "Flores", "Rivera", "Navarro", "Aquino", "Castro",
    "Dizon", "Mercado", "Ocampo", "Pascual", "Villanueva",
]  # fmt: skip
# Each demo member mostly borrows one genre, so their recommendations make sense.
GENRES = [
    "fantasy", "mystery", "romance", "classics", "science-fiction",
    "historical-fiction", "young-adult", "non-fiction", "horror", "thriller",
]  # fmt: skip
POPULAR_BOOKS = 1500  # pick from the most popular books (the dataset's order)


class Command(BaseCommand):
    help = "Create 20 demo members with some loans and ratings."

    def handle(self, *args, **options):
        rng = random.Random(42)
        today = timezone.localdate()
        popular = list(
            Book.objects.filter(goodreads_book_id__isnull=False).order_by("pk")[
                :POPULAR_BOOKS
            ]
        )
        if not popular:
            raise CommandError(
                "No books yet. Run `python manage.py import_books` first."
            )

        members = []
        for i, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES)):
            member, _ = Member.objects.get_or_create(
                email=f"{first}.{last}@example.com".lower(),
                defaults={
                    "name": f"{first} {last}",
                    "phone": f"0917 555 {1000 + i:04d}",
                    "date_joined": today - timedelta(days=rng.randint(60, 400)),
                },
            )
            members.append(member)

        if Loan.objects.filter(member__in=members).exists():
            self.stdout.write("Demo loans already exist; only checked the members.")
            return

        loans = ratings = 0
        for i, member in enumerate(members):
            genre = GENRES[i % len(GENRES)]
            liked = [b for b in popular if genre in b.tag_list] or popular
            picks = rng.sample(liked, k=min(5, len(liked)))
            if rng.random() < 0.5:
                picks.append(rng.choice(popular))  # the odd book outside their genre

            for n, book in enumerate(picks):
                still_out = n >= len(picks) - rng.randint(1, 2)
                if still_out:
                    # 0-30 days ago, so loans older than 14 days are overdue.
                    borrowed = today - timedelta(days=rng.randint(0, 30))
                else:
                    borrowed = today - timedelta(days=rng.randint(30, 120))
                try:
                    loan = Loan.borrow(member, book, borrow_date=borrowed)
                except ValidationError:
                    continue  # no copies left
                loans += 1
                if still_out:
                    continue
                loan.mark_returned(borrowed + timedelta(days=rng.randint(3, 20)))
                if rng.random() < 0.8:
                    in_genre = genre in book.tag_list
                    score = rng.choice([4, 5, 5] if in_genre else [2, 3, 4])
                    Rating.objects.create(
                        member=member,
                        book=book,
                        score=score,
                        rated_on=loan.return_date,
                    )
                    ratings += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(members)} members, {loans} loans and {ratings} ratings."
            )
        )
