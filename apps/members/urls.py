from django.urls import path

from apps.core.views import coming_soon

urlpatterns = [
    path("", coming_soon, name="member_list"),
    path("<int:pk>/", coming_soon, name="member_detail"),
]
