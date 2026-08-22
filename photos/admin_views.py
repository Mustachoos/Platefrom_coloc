"""Admin account management: the post-setup hub, and subadmin invites.

Access rule: the hub and invite generation/revocation require an
authenticated superuser — stricter than @staff_member_required (used by the
dashboard), since inviting/managing subadmins is the superuser's privilege
alone. Accepting an invite is the one open view here, since whoever holds
the one-time link doesn't have an account yet.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AdminAccountForm
from .models import AdminInvite

superuser_required = user_passes_test(lambda u: u.is_authenticated and u.is_superuser, login_url="dashboard")


@superuser_required
def admin_management_view(request):
    if request.method == "POST" and "generate_invite" in request.POST:
        invitee_name = request.POST.get("invitee_name", "").strip()
        if not invitee_name:
            messages.error(request, "Enter a name for the invite.")
        else:
            AdminInvite.objects.create(created_by=request.user, invitee_name=invitee_name)
        return redirect("admin-management")

    return render(request, "photos/admin_management.html", {
        "invites": AdminInvite.objects.all(),
    })


@superuser_required
def revoke_invite_view(request, token):
    if request.method == "POST":
        invite = get_object_or_404(AdminInvite, token=token)
        if invite.status != AdminInvite.STATUS_REVOKED:
            invite.revoked_at = timezone.now()
            invite.save(update_fields=["revoked_at"])
            if invite.used_by_id:
                invite.used_by.is_active = False
                invite.used_by.save(update_fields=["is_active"])
            messages.success(request, f"Access revoked for {invite.invitee_name}.")
    return redirect("admin-management")


def subadmin_invite_view(request, token):
    invite = get_object_or_404(AdminInvite, token=token)
    if invite.status != AdminInvite.STATUS_PENDING:
        messages.error(request, "This invite link is no longer valid.")
        return redirect("staff-login")

    if request.method == "POST":
        form = AdminAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(username=username).exists():
                form.add_error("username", "That username is already taken.")
            else:
                user = User.objects.create_user(
                    username, "", form.cleaned_data["password"], is_staff=True
                )
                invite.used_at = timezone.now()
                invite.used_by = user
                invite.save(update_fields=["used_at", "used_by"])
                login(request, user)
                return redirect("dashboard")
    else:
        form = AdminAccountForm()
    return render(request, "photos/subadmin_invite.html", {"form": form, "invite": invite})
