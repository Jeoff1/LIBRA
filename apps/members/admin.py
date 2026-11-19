from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "date_joined"]
    search_fields = ["name", "email", "phone"]
