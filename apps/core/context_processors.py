from apps.loans.models import Loan


def libra(request):
    """The sidebar's active section and overdue badge, for logged-in pages."""
    if not request.user.is_authenticated:
        return {}
    match = request.resolver_match
    url_name = match.url_name if match else ""
    section = "overdue" if url_name == "loan_overdue" else url_name.split("_")[0]
    return {"nav_section": section, "overdue_count": Loan.objects.overdue().count()}
