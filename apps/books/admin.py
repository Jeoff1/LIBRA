from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "authors",
        "publication_year",
        "average_rating",
        "available_copies",
        "total_copies",
    ]
    list_filter = ["language_code"]
    search_fields = ["title", "authors", "isbn", "goodreads_book_id"]
