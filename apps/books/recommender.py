"""Book recommendations from ml_models/similar_books.joblib.

`python manage.py train_recommender` writes that file: a dict mapping each
dataset book_id (Book.goodreads_book_id) to its 10 most similar book_ids.
The file is loaded the first time it's needed, and again only if it changes.
If it is missing, every function returns an empty list.
"""

from pathlib import Path

import joblib
from django.conf import settings

from apps.books.models import Book
from apps.loans.models import Loan, Rating

MODEL_FILENAME = "similar_books.joblib"

_cache = {"path": None, "mtime": None, "similar": None}


def model_path() -> Path:
    return Path(settings.ML_MODELS_DIR) / MODEL_FILENAME


def _load():
    path = model_path()
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return None
    if _cache["path"] != path or _cache["mtime"] != mtime:
        _cache.update(path=path, mtime=mtime, similar=joblib.load(path))
    return _cache["similar"]


def is_trained() -> bool:
    return _load() is not None


def _books_in_order(book_ids, exclude_pks=(), n=5):
    """Fetch the Books for `book_ids`, keeping that order."""
    books = Book.objects.filter(goodreads_book_id__in=book_ids).exclude(
        pk__in=exclude_pks
    )
    by_id = {book.goodreads_book_id: book for book in books}
    return [by_id[book_id] for book_id in book_ids if book_id in by_id][:n]


def similar_books(book_id, n=5):
    """The n books most like the one with this dataset book_id."""
    similar = _load()
    if not similar or book_id is None:
        return []
    return _books_in_order(similar.get(book_id, []), n=n)


def recommend_for_member(member, n=5):
    """Books like the ones this member rated 4-5 (or, failing that, borrowed).

    Books the member has already borrowed or rated are never recommended.
    """
    similar = _load()
    if not similar:
        return []

    liked = Rating.objects.filter(member=member, score__gte=4).order_by(
        "-score", "-rated_on"
    )
    borrowed = Loan.objects.filter(member=member).order_by("-borrow_date")
    seeds = [
        book_id
        for book_id in liked.values_list("book__goodreads_book_id", flat=True)
        if book_id is not None
    ] or [
        book_id
        for book_id in borrowed.values_list("book__goodreads_book_id", flat=True)
        if book_id is not None
    ]

    # Each seed votes for its similar books; closer matches get bigger votes.
    scores = {}
    for seed in dict.fromkeys(seeds):
        for rank, book_id in enumerate(similar.get(seed, [])):
            scores[book_id] = scores.get(book_id, 0) + 1 / (rank + 1)
    ranked = sorted(scores, key=lambda book_id: (-scores[book_id], book_id))

    already_seen = set(borrowed.values_list("book_id", flat=True)) | set(
        Rating.objects.filter(member=member).values_list("book_id", flat=True)
    )
    return _books_in_order(ranked, exclude_pks=already_seen, n=n)
