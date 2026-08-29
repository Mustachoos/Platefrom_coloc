"""Admin account management: first-run admin creation, the post-setup hub,
subadmin invites, Google Drive connection, and network address verification.

Access rule: creating the admin account is open to anyone while no
superuser exists yet (that's the "fresh install" state); once one exists,
only that authenticated superuser can reach it again (e.g. to check the
username). Everything else here — the hub, Drive connection, invite
generation/revocation — requires an authenticated superuser outright, since
by the time any of it is reachable an admin account already exists and the
person who created it is logged in. Accepting a subadmin invite and loading
the verify-IP page are the two exceptions, both reached by someone who
isn't logged in as anyone (a new subadmin, or a phone scanning a QR code).

Verify-IP flow: the admin types an address; the server itself (not the
admin's browser) fires a background request at that address to prove it's
actually reachable — a real round trip out onto the LAN and back in,
because request.get_host() on the receiving end is the only honest proof,
not whatever the admin typed. Pending/result/failure state lives in the
cache (short-lived, no need to persist it).
"""

import logging
import os
import threading
import urllib.error
import urllib.request
import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from google_auth_oauthlib.flow import Flow

from . import drive_service, email_service
from .forms import AdminAccountForm, DriveClientSecretForm, StyledPasswordResetForm
from .models import AdminInvite, SiteSettings

logger = logging.getLogger(__name__)

# oauthlib refuses any OAuth exchange over plain http by default. Google
# itself allows http://localhost specifically (see _localhost_redirect_uri
# below) — this only lifts oauthlib's own client-side check to match, and
# only ever applies to the localhost-only redirect this flow is locked to.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

superuser_required = user_passes_test(lambda u: u.is_authenticated and u.is_superuser, login_url="dashboard")

_VERIFY_TTL_SECONDS = 600
_VERIFY_CHECK_TIMEOUT_SECONDS = 5
_SUPPORT_EMAIL_VERIFY_TTL_SECONDS = 1800


def _support_email_verify_pending_key(token):
    return f"verify-support-email-pending:{token}"


def _send_support_email_verification(request):
    """Sends a fresh verification link for the currently-saved support_email
    to the admin's own account email — click-through proof it's usable,
    same honesty principle as the network-address round trip below."""
    site_settings = SiteSettings.get_solo()
    token = uuid.uuid4()
    cache.set(
        _support_email_verify_pending_key(token), site_settings.support_email,
        timeout=_SUPPORT_EMAIL_VERIFY_TTL_SECONDS,
    )
    verify_url = request.build_absolute_uri(reverse("verify-support-email", args=[token]))
    email_service.send_verification_email(request.user.email, verify_url)


def _verify_pending_key(token):
    return f"verify-ip-pending:{token}"


def _verify_result_key(token):
    return f"verify-ip-result:{token}"


def _verify_failed_key(token):
    return f"verify-ip-failed:{token}"


def _run_ip_check(token, ip_address, port):
    """Runs in a background thread. Success is recorded by verify_ip_page_view
    itself, as the target of this very request — this function only ever
    needs to record failure, when the address couldn't be reached at all."""
    url = f"http://{ip_address}:{port}{reverse('verify-ip-page', args=[token])}"
    try:
        with urllib.request.urlopen(url, timeout=_VERIFY_CHECK_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                cache.set(_verify_failed_key(token), True, timeout=_VERIFY_TTL_SECONDS)
    except (urllib.error.URLError, TimeoutError, OSError):
        cache.set(_verify_failed_key(token), True, timeout=_VERIFY_TTL_SECONDS)


def _admin_creation_open(request):
    if not User.objects.filter(is_superuser=True).exists():
        return True
    return request.user.is_authenticated and request.user.is_superuser


def create_admin_view(request):
    if not _admin_creation_open(request):
        return redirect("dashboard")

    existing_admin = User.objects.filter(is_superuser=True).first()
    if existing_admin:
        # Already done — a fresh admin account can't be created twice, but
        # revisiting this page (e.g. a stale bookmark) shouldn't dead-end.
        return render(request, "photos/create_admin.html", {"existing_admin": existing_admin})

    if request.method == "POST":
        form = AdminAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(username=username).exists():
                form.add_error("username", "That username is already taken.")
            else:
                user = User.objects.create_superuser(
                    username, form.cleaned_data["email"].strip(), form.cleaned_data["password"]
                )
                login(request, user)
                return redirect("admin-management")
    else:
        form = AdminAccountForm()
    return render(request, "photos/create_admin.html", {"form": form})


class SupportEmailPasswordResetView(auth_views.PasswordResetView):
    """Same as Django's PasswordResetView, except the SMTP credentials come
    from SiteSettings (set via the admin UI) instead of the global
    EMAIL_HOST_* settings — this app also ships as a standalone .exe where
    end users can't set environment variables."""

    template_name = "photos/password_reset_form.html"
    email_template_name = "photos/password_reset_email.txt"
    subject_template_name = "photos/password_reset_subject.txt"
    success_url = reverse_lazy("password-reset-done")
    form_class = StyledPasswordResetForm

    def form_valid(self, form):
        # Never let an SMTP failure surface differently from "no matching
        # account" — either way the response must look identical, so this
        # always redirects to the same success page; a misconfigured
        # support email only shows up in the server log, not to whoever
        # submitted the form.
        try:
            form.save(
                use_https=self.request.is_secure(),
                token_generator=self.token_generator,
                from_email=SiteSettings.get_solo().support_email,
                email_template_name=self.email_template_name,
                subject_template_name=self.subject_template_name,
                request=self.request,
                email_backend=email_service.build_backend(),
            )
        except Exception:
            logger.exception("Failed to send password-reset email")
        return HttpResponseRedirect(self.get_success_url())


def _client_secret_path():
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()


def _token_path():
    return os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", "").strip()


def _is_localhost(request):
    return request.get_host().split(":", 1)[0] in ("localhost", "127.0.0.1")


def _localhost_redirect_uri(request):
    """Google's OAuth policy requires HTTPS for any redirect URI host except
    localhost/127.0.0.1 (a LAN IP like 192.168.1.13 over plain http is
    rejected outright, even if registered) — so this step always targets
    localhost specifically, regardless of what host the current request
    actually came in on. That only resolves correctly if the browser
    completing this step is on the server machine itself; see _is_localhost."""
    host = request.get_host()
    port = host.split(":", 1)[1] if ":" in host else "8000"
    return f"http://localhost:{port}{reverse('drive-google-callback')}"


def _google_flow(request):
    return Flow.from_client_secrets_file(
        _client_secret_path(), scopes=drive_service.SCOPES,
        redirect_uri=_localhost_redirect_uri(request),
    )


@superuser_required
def drive_google_connect_view(request):
    if not _is_localhost(request):
        # Google would reject this redirect_uri outright (see
        # _localhost_redirect_uri) — fail here with a clear message instead
        # of sending the user into a doomed consent flow.
        return redirect("admin-management")
    flow = _google_flow(request)
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["google_oauth_state"] = state
    # google-auth-oauthlib auto-generates a PKCE code_verifier per Flow
    # instance (authorization_url() creates it, sends its hash to Google as
    # code_challenge). The callback below builds a brand new Flow object, so
    # without carrying this over the exchange fails with "Missing code
    # verifier" — same reason state has to round-trip through the session.
    request.session["google_oauth_code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@superuser_required
def drive_google_callback_view(request):
    flow = _google_flow(request)
    flow.state = request.session.get("google_oauth_state")
    flow.code_verifier = request.session.get("google_oauth_code_verifier")
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    token_path = _token_path()
    os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
    with open(token_path, "w") as f:
        f.write(flow.credentials.to_json())
    return redirect("admin-management")


@superuser_required
def admin_management_view(request):
    if request.method == "POST" and "generate_invite" in request.POST:
        invitee_name = request.POST.get("invitee_name", "").strip()
        if not invitee_name:
            messages.error(request, "Enter a name for the invite.", extra_tags="staff")
        else:
            AdminInvite.objects.create(created_by=request.user, invitee_name=invitee_name)
        return redirect("admin-management")

    if request.method == "POST" and "start_verify_ip" in request.POST:
        # Strip a trailing ":port" if present — Recheck resubmits the
        # already-verified value, which is stored as host:port.
        ip_address = request.POST.get("ip_address", "").strip().split(":", 1)[0]
        if not ip_address:
            messages.error(request, "Enter an IP address to verify.", extra_tags="network")
            return redirect("admin-management")
        token = uuid.uuid4()
        cache.set(_verify_pending_key(token), ip_address, timeout=_VERIFY_TTL_SECONDS)
        host = request.get_host()
        port = host.split(":", 1)[1] if ":" in host else "8000"
        threading.Thread(target=_run_ip_check, args=(token, ip_address, port), daemon=True).start()
        return redirect(f"{reverse('admin-management')}?verify_token={token}&verify_ip={ip_address}")

    client_secret_path = _client_secret_path()
    token_path = _token_path()
    site_settings = SiteSettings.get_solo()
    drive_error = None

    if request.method == "POST" and "save_support_email" in request.POST:
        new_email = request.POST.get("support_email", "").strip()
        try:
            if new_email:
                validate_email(new_email)
        except ValidationError:
            messages.error(request, "That doesn't look like a valid email address.", extra_tags="support-email")
            return redirect("admin-management")

        email_changed = new_email != site_settings.support_email
        site_settings.support_email = new_email
        site_settings.support_email_app_password = request.POST.get("support_email_app_password", "").strip()
        if email_changed:
            site_settings.support_email_verified = False
        site_settings.save(update_fields=["support_email", "support_email_app_password", "support_email_verified"])

        if new_email and email_changed:
            if not request.user.email:
                messages.error(
                    request, "Set your own email on your profile page first — that's where the verification link goes.",
                    extra_tags="support-email",
                )
            else:
                try:
                    _send_support_email_verification(request)
                except Exception:
                    logger.exception("Failed to send support-email verification email")
                    messages.error(
                        request, "Support email saved, but the verification email couldn't be sent — check "
                        "the address and app password, then use \"Resend verification email\" below.",
                        extra_tags="support-email",
                    )
                else:
                    messages.success(
                        request, f"Support email saved — check {request.user.email} for a verification link.",
                        extra_tags="support-email",
                    )
        else:
            messages.success(request, "Support email saved.", extra_tags="support-email")
        return redirect("admin-management")

    if request.method == "POST" and "resend_support_email_verification" in request.POST:
        try:
            _send_support_email_verification(request)
        except Exception as exc:
            messages.error(request, f"Could not send verification email: {exc}", extra_tags="support-email")
        else:
            messages.success(request, f"Verification email sent to {request.user.email}.", extra_tags="support-email")
        return redirect("admin-management")

    if request.method == "POST" and "send_test_email" in request.POST:
        try:
            email_service.send_test_email(request.user.email)
        except Exception as exc:
            messages.error(request, f"Could not send test email: {exc}", extra_tags="account")
        else:
            messages.success(request, f"Test email sent to {request.user.email}.", extra_tags="account")
        return redirect("admin-management")

    if request.method == "POST" and "upload_client_secret" in request.POST:
        client_secret_form = DriveClientSecretForm(request.POST, request.FILES)
        if client_secret_form.is_valid():
            os.makedirs(os.path.dirname(client_secret_path) or ".", exist_ok=True)
            with open(client_secret_path, "wb") as f:
                for chunk in client_secret_form.cleaned_data["client_secret_file"].chunks():
                    f.write(chunk)
        return redirect("admin-management")

    if request.method == "POST" and "disconnect_drive" in request.POST:
        for path in (client_secret_path, token_path):
            if path and os.path.exists(path):
                os.remove(path)
        site_settings.drive_root_folder_id = ""
        site_settings.save(update_fields=["drive_root_folder_id"])
        messages.success(request, "Drive connection removed — start again from step 1.", extra_tags="drive")
        return redirect("admin-management")

    if request.method == "POST" and "choose_folder" in request.POST:
        choice = request.POST.get("folder_choice", "").strip()
        new_name = request.POST.get("new_folder_name", "").strip()
        try:
            if choice == "__new__":
                if not new_name:
                    raise drive_service.DriveError("Give the new folder a name.")
                folder_id = drive_service.create_root_folder(new_name)
            elif choice:
                folder_id = choice
            else:
                raise drive_service.DriveError("Choose a folder.")
        except drive_service.DriveError as exc:
            drive_error = str(exc)
        else:
            site_settings.drive_root_folder_id = folder_id
            site_settings.save(update_fields=["drive_root_folder_id"])
            return redirect("admin-management")
        # Falls through to the render below with drive_error set, so
        # step 3's dialog can reopen showing what went wrong.

    verify_token = request.GET.get("verify_token", "")
    verify_ip = request.GET.get("verify_ip", "")
    # Dead/expired query params (bookmarked, or the 10-minute window passed)
    # shouldn't render a QR code that can never succeed.
    if verify_token and not cache.get(_verify_pending_key(verify_token)):
        verify_token = ""

    verified_ip = site_settings.server_host.split(":", 1)[0] if site_settings.server_host else ""

    # Drive step status — live checks, same honesty principle as verify-ip:
    # a step is only "verified" once it's proven to actually work, not just
    # "a file is present".
    has_client_secret = bool(client_secret_path and os.path.exists(client_secret_path))
    has_token = bool(token_path and os.path.exists(token_path))

    client_secret_valid = False
    if has_client_secret:
        try:
            Flow.from_client_secrets_file(client_secret_path, scopes=drive_service.SCOPES)
            client_secret_valid = True
        except Exception:
            client_secret_valid = False

    drive_folders = None
    token_valid = False
    if has_token:
        try:
            drive_folders = drive_service.list_root_folders()
            token_valid = True
        except drive_service.DriveError:
            token_valid = False

    current_folder_id = site_settings.drive_root_folder_id
    folder_valid = bool(token_valid and current_folder_id and drive_service.folder_exists(current_folder_id))
    drive_ready = bool(client_secret_valid and token_valid and folder_valid)
    drive_attention = bool(
        (has_client_secret and not client_secret_valid)
        or (has_token and not token_valid)
        or (current_folder_id and not folder_valid)
    )
    drive_progress = sum([client_secret_valid, token_valid, folder_valid])

    support_email_format_valid = True
    if site_settings.support_email:
        try:
            validate_email(site_settings.support_email)
        except ValidationError:
            support_email_format_valid = False

    host = request.get_host()
    port = host.split(":", 1)[1] if ":" in host else "8000"

    return render(request, "photos/admin_management.html", {
        "invites": AdminInvite.objects.all(),
        "site_settings": site_settings,
        "verify_token": verify_token,
        "verify_ip": verify_ip,
        "verified_ip": verified_ip,
        "client_secret_form": DriveClientSecretForm(),
        "has_client_secret": has_client_secret,
        "client_secret_valid": client_secret_valid,
        "has_token": has_token,
        "token_valid": token_valid,
        "drive_folders": drive_folders,
        "current_folder_id": current_folder_id,
        "folder_valid": folder_valid,
        "drive_ready": drive_ready,
        "drive_attention": drive_attention,
        "drive_progress": drive_progress,
        "drive_error": drive_error,
        "drive_redirect_uri": _localhost_redirect_uri(request),
        "drive_is_localhost": _is_localhost(request),
        "drive_localhost_url": f"http://localhost:{port}{reverse('admin-management')}",
        "support_email_format_valid": support_email_format_valid,
    })


@superuser_required
def verify_ip_status_view(request, token):
    if cache.get(_verify_failed_key(token)):
        return JsonResponse({"verified": False, "failed": True, "host": None})
    confirmed_host = cache.get(_verify_result_key(token))
    return JsonResponse({"verified": confirmed_host is not None, "failed": False, "host": confirmed_host})


def verify_ip_page_view(request, token):
    if cache.get(_verify_pending_key(token)) is None:
        return render(request, "photos/verify_ip_page.html", {"expired": True})

    # The fact that this request arrived here at all, over this exact
    # host:port, is the proof — not whatever IP the admin originally typed.
    confirmed_host = request.get_host()
    cache.set(_verify_result_key(token), confirmed_host, timeout=_VERIFY_TTL_SECONDS)
    site_settings = SiteSettings.get_solo()
    site_settings.server_host = confirmed_host
    site_settings.save(update_fields=["server_host"])
    return render(request, "photos/verify_ip_page.html", {"expired": False, "host": confirmed_host})


def verify_support_email_view(request, token):
    key = _support_email_verify_pending_key(token)
    pending_email = cache.get(key)
    if pending_email is None:
        return render(request, "photos/verify_support_email_page.html", {"expired": True})
    cache.delete(key)
    site_settings = SiteSettings.get_solo()
    if pending_email != site_settings.support_email:
        # The support email was changed again after this link was sent —
        # don't let a stale link verify whatever address is current now.
        return render(request, "photos/verify_support_email_page.html", {"expired": True})
    site_settings.support_email_verified = True
    site_settings.save(update_fields=["support_email_verified"])
    return render(request, "photos/verify_support_email_page.html", {"expired": False})


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
            messages.success(request, f"Access revoked for {invite.invitee_name}.", extra_tags="staff")
    return redirect("admin-management")


@superuser_required
def delete_invite_view(request, token):
    if request.method == "POST":
        invite = get_object_or_404(AdminInvite, token=token, revoked_at__isnull=False)
        invitee_name = invite.invitee_name
        invite.delete()
        messages.success(request, f"Removed {invitee_name} from the list.", extra_tags="staff")
    return redirect("admin-management")


def subadmin_invite_view(request, token):
    invite = get_object_or_404(AdminInvite, token=token)
    if invite.status != AdminInvite.STATUS_PENDING:
        return render(request, "photos/invite_invalid.html", {"invite": invite})

    if request.method == "POST":
        form = AdminAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(username=username).exists():
                form.add_error("username", "That username is already taken.")
            else:
                user = User.objects.create_user(
                    username, form.cleaned_data["email"].strip(), form.cleaned_data["password"], is_staff=True
                )
                invite.used_at = timezone.now()
                invite.used_by = user
                invite.save(update_fields=["used_at", "used_by"])
                login(request, user)
                return redirect("dashboard")
    else:
        form = AdminAccountForm()
    return render(request, "photos/subadmin_invite.html", {"form": form, "invite": invite})
