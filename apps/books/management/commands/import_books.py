import random
from decimal import Decimal

import pandas as pd
from django.core.management.base import BaseCommand

from apps.books.dataset import clean_isbn, read_books, top_tags
from apps.books.models import Book


def _or_none(value):
    return None if pd.isna(value) else value


class Command(BaseCommand):
    help = (
        "Import the goodbooks-10k books and their top tags from data/. "
        "Safe to run again: books already imported are skipped."
    )

    def handle(self, *args, **options):
        self.stdout.write("Reading CSVs...")
        books = read_books()
        tags = top_tags()

        existing = set(
            Book.objects.filter(goodreads_book_id__isnull=False).values_list(
                "goodreads_book_id", flat=True
            )
        )

        new_books = []
        for row in books.itertuples(index=False):
            goodreads_id = int(row.goodreads_book_id)
            if goodreads_id in existing:
                continue
            year = _or_none(row.publication_year)
            rating = _or_none(row.average_rating)
            copies = random.randint(1, 5)
            new_books.append(
                Book(
                    goodreads_book_id=goodreads_id,
                    title=row.title.strip(),
                    authors=row.authors.strip(),
                    publication_year=int(year) if year is not None else None,
                    isbn=clean_isbn(row.isbn),
                    language_code=_or_none(row.language_code) or "",
                    average_rating=(
                        Decimal(str(round(rating, 2))) if rating is not None else None
                    ),
                    image_url=_or_none(row.image_url) or "",
                    tags=", ".join(tags.get(goodreads_id, [])),
                    total_copies=copies,
                    available_copies=copies,
                )
            )

        Book.objects.bulk_create(new_books, batch_size=1000)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(new_books)} books; "
                f"skipped {len(books) - len(new_books)} already in the database."
            )
        )
