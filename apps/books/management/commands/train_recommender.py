import re

import joblib
import numpy as np
from django.core.management.base import BaseCommand
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from apps.books.dataset import read_books, top_tags
from apps.books.recommender import model_path

TOP_N = 10
# Compare 1,000 books at a time: the full 10k x 10k similarity matrix
# would need about 800 MB of memory.
CHUNK_SIZE = 1000
SANITY_CHECK = [2767052, 3, 1885]  # Hunger Games, Harry Potter 1, Pride and Prejudice


def as_token(name: str) -> str:
    """'Jane Austen' -> 'jane_austen', so a name or tag counts as one word."""
    return re.sub(r"\W+", "_", name.strip().lower()).strip("_")


def book_text(title, authors, tags) -> str:
    author_tokens = " ".join(as_token(a) for a in authors.split(","))
    tag_tokens = " ".join(as_token(t) for t in tags)
    return f"{title} {author_tokens} {tag_tokens}"


class Command(BaseCommand):
    help = (
        "Train the content-based recommender (TF-IDF on title + authors + "
        "top 10 tags) and save each book's 10 most similar books."
    )

    def handle(self, *args, **options):
        self.stdout.write("Reading CSVs...")
        books = read_books()[["goodreads_book_id", "title", "authors"]]
        tags = top_tags()
        texts = [
            book_text(row.title, row.authors, tags.get(row.goodreads_book_id, []))
            for row in books.itertuples(index=False)
        ]

        self.stdout.write(f"Fitting TF-IDF on {len(texts)} books...")
        vectors = TfidfVectorizer(stop_words="english").fit_transform(texts)

        # TF-IDF rows have length 1, so their dot product is the cosine similarity.
        ids = books["goodreads_book_id"].to_numpy()
        similar = {}
        for start in range(0, len(ids), CHUNK_SIZE):
            scores = linear_kernel(vectors[start : start + CHUNK_SIZE], vectors)
            rows = np.arange(scores.shape[0])
            scores[rows, start + rows] = -1  # a book isn't similar to itself
            top = np.argpartition(-scores, TOP_N, axis=1)[:, :TOP_N]
            order = np.argsort(-np.take_along_axis(scores, top, axis=1), axis=1)
            top = np.take_along_axis(top, order, axis=1)
            for offset, neighbours in enumerate(top):
                similar[int(ids[start + offset])] = [int(ids[j]) for j in neighbours]

        path = model_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(similar, path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Saved similar books for {len(similar)} books to {path}"
            )
        )

        titles = dict(zip(books["goodreads_book_id"], books["title"]))
        for book_id in SANITY_CHECK:
            if book_id not in similar:
                continue
            self.stdout.write(f"\nMost similar to “{titles[book_id]}”:")
            for rank, other in enumerate(similar[book_id][:5], start=1):
                self.stdout.write(f"  {rank}. {titles[other]}")
