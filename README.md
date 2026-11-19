# LIBRA – Library Management System

A small library system built with Django and MySQL/MariaDB. Librarians log in to manage books, members, loans and ratings, and the app recommends books using a content-based model trained on the goodbooks-10k dataset.

## Features

- **Landing page** at `/`: a public front page that introduces LIBRA and links to the librarian login.
- **Books**: list with search (title/author), year filter and pages; add, view, edit, delete.
- **Members**: list with search; add, view, edit, delete.
- **Loans**: lend a book (due in 14 days by default), return it, change the due date, delete. Borrowing takes a copy off the shelf and returning puts it back. Borrowing is blocked when no copies are left.
- **Overdue list**: loans still out after their due date.
- **Ratings**: a member's 1–5 rating for a book they borrowed, one per member and book.
- **Recommendations**: "Similar books" on each book page, and "Recommended for this member" on each member page.
- **Dashboard**: counts of books, members, active and overdue loans, plus the 5 most borrowed books.

Members don't log in. Librarians are Django staff users, and every page except the landing and login pages needs a logged-in user. After logging in, librarians land on the dashboard at `/dashboard/`.

## Requirements

- Python 3.12 or newer (developed on 3.14)
- MySQL 8.4+ or MariaDB 10.6+ (developed on MariaDB 12.3). XAMPP's bundled MariaDB 10.4 is too old for Django 6.1.
- A free Kaggle account, to download the dataset

## Setup

Commands below are for Windows (Command Prompt or PowerShell). On macOS or Linux, use `source .venv/bin/activate` instead of `.venv\Scripts\activate`.

### 1. Get the code and install packages

```bash
git clone https://github.com/Jeoff1/LIBRA.git
cd LIBRA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create the database

Open the MySQL/MariaDB client as `root` (for example **MySQL Client (MariaDB 12.3 (x64))** from the Start menu) and run, choosing your own password:

```sql
CREATE DATABASE library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'libra_user'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON library_db.* TO 'libra_user'@'localhost';
GRANT ALL PRIVILEGES ON test_library_db.* TO 'libra_user'@'localhost';
FLUSH PRIVILEGES;
```

The `test_library_db` grant lets `manage.py test` create its temporary test database.

### 3. Create the `.env` file

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Then fill it in:

- `DJANGO_SECRET_KEY`: generate one with
  `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`
- `DB_USER` / `DB_PASSWORD`: the user and password from step 2.

`.env` holds passwords, so it is ignored by git. Never commit it.

### 4. Download the dataset into `data/`

The dataset isn't in the repository (about 40 MB unzipped), so each computer downloads it once.

1. Log in to Kaggle and open <https://www.kaggle.com/datasets/zygmunt/goodbooks-10k>.
2. Click **Download** and save the zip file.
3. Create a folder named `data` in the project root (next to `manage.py`).
4. Extract the zip into `data/`. You should then have:

```
LIBRA/
├── data/
│   ├── books.csv
│   ├── book_tags.csv
│   ├── tags.csv
│   └── ratings.csv      (not used, but harmless to keep)
└── manage.py
```

The app reads `books.csv`, `book_tags.csv` and `tags.csv`. If the zip puts them in a subfolder, move them up into `data/` directly.

### 5. Build the database and the recommender

```bash
python manage.py migrate
python manage.py import_books        # loads the 10,000 books; safe to run again
python manage.py train_recommender   # takes a few seconds; prints a sanity check
python manage.py seed_demo           # optional: 20 demo members with loans and ratings
python manage.py createsuperuser     # your librarian login
python manage.py runserver
```

Open <http://127.0.0.1:8000/>, click **Librarian log in**, and use the superuser you created.

## Running the tests

```bash
python manage.py test
```

## How the recommender works

`train_recommender` builds one piece of text per book: its title, its authors and its 10 most-used tags from `book_tags.csv`. Each author name and tag is kept as one word (`jane_austen`, `science_fiction`). It turns these texts into TF-IDF vectors (scikit-learn's `TfidfVectorizer`, English stop words removed) and compares every pair of books by cosine similarity. For each book it saves the 10 most similar books to `ml_models/similar_books.joblib`.

- **Similar books** on a book page are that book's saved neighbours.
- **Member recommendations** combine the neighbours of the books the member rated 4–5 (or, if they have none, the books they borrowed). Closer matches count more. Books the member has already borrowed or rated are left out.

If `similar_books.joblib` is missing, the pages still work and show "Recommendations not trained yet." Run `train_recommender` again any time; the app picks up the new file automatically.

### Notes on the dataset

- In `books.csv`, the column `book_id` is the Goodreads ID; it matches `goodreads_book_id` in `book_tags.csv`. LIBRA stores it as `Book.goodreads_book_id`. (The `id` column is a separate 1–10000 numbering used only by `ratings.csv`.)
- Many tags are reading-list labels rather than topics (`to-read`, `favorites`, `owned`, `kindle`, `read-in-2015`, …). These are skipped when picking a book's top tags.
- ISBNs lost their leading zeros in the CSV; the import pads them back to 10 digits.
- Some books have no year, and a few have negative years (works from before 1 AD).

## Project layout

```
config/          settings (reads .env), main URLs
apps/
  core/          dashboard, seed_demo command, Bootstrap form helper
  books/         Book model and pages, import_books, train_recommender,
                 dataset.py (CSV reading), recommender.py
  members/       Member model and pages
  loans/         Loan and Rating models, borrow/return, overdue list, ratings
templates/       app layout (sidebar + top bar), login page, shared form/pagination/delete pages
static/css/      libra.css: the LIBRA theme on top of Bootstrap 5
static/images/   logos (originals plus light/dark and name-only variants)
data/            goodbooks-10k CSVs (not in git)
ml_models/       trained recommender (not in git)
```

## Design

- **Palette:** brown `#5c3a26`, sage `#a3b18a`, cream `#f1e7d3`, plus darker and lighter shades of each for hover states and readable text. All colours live as CSS variables at the top of `static/css/libra.css`.
- **Fonts:** Cormorant Garamond for headings (it matches the logo lettering) and DM Sans for text, from Google Fonts. Icons are Bootstrap Icons.
- **Logos:** `LIBRALogowithtext.svg` and `LIBRA_Logo.svg` are the originals. The `libra-*-light.svg` variants are for brown backgrounds and the `libra-*-dark.svg` variants for cream ones. The `libra-name-*` versions drop the tagline so they stay legible at small sizes.
- **Covers:** books without a cover in the dataset get a brown placeholder cover with a sage bookmark, borrowed from the logo.

The Django admin is at <http://127.0.0.1:8000/admin/> for staff users.
