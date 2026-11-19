from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.books import recommender

from .forms import MemberForm
from .models import Member


@login_required
def member_list(request):
    members = Member.objects.annotate(
        active_loans=Count("loans", filter=Q(loans__return_date__isnull=True))
    ).order_by("name")
    q = request.GET.get("q", "").strip()
    if q:
        members = members.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )
    page_obj = Paginator(members, 20).get_page(request.GET.get("page"))
    return render(request, "members/member_list.html", {"page_obj": page_obj, "q": q})


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    loans = member.loans.select_related("book")
    ratings = member.ratings.select_related("book")
    return render(
        request,
        "members/member_detail.html",
        {
            "member": member,
            "active_loans": [loan for loan in loans if loan.is_active],
            "past_loans": [loan for loan in loans if not loan.is_active],
            "ratings": ratings,
            "recommender_ready": recommender.is_trained(),
            "recommendations": recommender.recommend_for_member(member),
        },
    )


@login_required
def member_create(request):
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        messages.success(request, f"Added member {member}.")
        return redirect(member)
    return render(request, "members/member_form.html", {"form": form})


@login_required
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Saved changes to {member}.")
        return redirect(member)
    return render(request, "members/member_form.html", {"form": form, "member": member})


@login_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        try:
            member.delete()
        except ProtectedError:
            messages.error(
                request,
                f"{member} has loan records, so they can't be deleted. "
                "Delete their loans first.",
            )
            return redirect(member)
        messages.success(request, f"Deleted member {member}.")
        return redirect("member_list")
    return render(
        request,
        "confirm_delete.html",
        {
            "object": member,
            "kind": "member",
            "cancel_url": member.get_absolute_url(),
            "warning": (
                "Their ratings will be deleted too." if member.ratings.exists() else ""
            ),
        },
    )
