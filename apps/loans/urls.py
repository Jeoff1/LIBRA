from django.urls import path

from apps.core.views import coming_soon

urlpatterns = [
    path("loans/", coming_soon, name="loan_list"),
    path("loans/overdue/", coming_soon, name="loan_overdue"),
    path("loans/new/", coming_soon, name="loan_create"),
    path("ratings/", coming_soon, name="rating_list"),
    path("ratings/new/", coming_soon, name="rating_create"),
]
