from django.urls import path

from . import views

urlpatterns = [
    path("loans/", views.loan_list, name="loan_list"),
    path("loans/overdue/", views.loan_overdue, name="loan_overdue"),
    path("loans/new/", views.loan_create, name="loan_create"),
    path("loans/<int:pk>/edit/", views.loan_update, name="loan_update"),
    path("loans/<int:pk>/return/", views.loan_return, name="loan_return"),
    path("loans/<int:pk>/delete/", views.loan_delete, name="loan_delete"),
    path("ratings/", views.rating_list, name="rating_list"),
    path("ratings/new/", views.rating_create, name="rating_create"),
    path("ratings/<int:pk>/edit/", views.rating_update, name="rating_update"),
    path("ratings/<int:pk>/delete/", views.rating_delete, name="rating_delete"),
]
