"""First-run setup wizard: a web-only path from "fresh clone" to "usable
app", replacing manual .env/docker-compose editing and CLI commands
(createsuperuser, manage.py google_drive_auth) with a guided web flow.

Access rule: open to anyone while no superuser exists yet (that's the
"fresh install" state); once one exists, only that authenticated superuser
can still reach these views (e.g. to finish a skipped step later) — a
stranger on the LAN can't run/re-run the wizard once it's been completed.
"""

import os

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import reverse
from google_auth_oauthlib.flow import Flow

from . import drive_service, event_service
from .forms import AdminAccountForm, DriveClientSecretForm, FirstEventForm, NetworkForm
from .models import Event, SiteSettings


def _setup_accessible(request):
    if not User.objects.filter(is_superuser=True).exists():
        return True
    return request.user.is_authenticated and request.user.is_superuser


def _denied():
    return redirect("dashboard")


def _client_secret_path():
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "").strip()


def _token_path():
    return os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", "").strip()


def _google_flow(request):
    redirect_uri = request.build_absolute_uri(reverse("setup-google-callback"))
    return Flow.from_client_secrets_file(
        _client_secret_path(), scopes=drive_service.SCOPES, redirect_uri=redirect_uri
    )


def _safe_list_folders():
    try:
        return drive_service.list_root_folders()
    except drive_service.DriveError:
        return []


def welcome_view(request):
    if not _setup_accessible(request):
        return _denied()
    if User.objects.filter(is_superuser=True).exists():
        # Wizard already has an admin account — jump straight back into
        # wherever they left off instead of re-showing "let's get started".
        return redirect("setup-drive")
    return render(request, "photos/setup_welcome.html")


def admin_account_view(request):
    if not _setup_accessible(request):
        return _denied()
    if User.objects.filter(is_superuser=True).exists():
        return redirect("setup-drive")

    if request.method == "POST":
        form = AdminAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(username=username).exists():
                form.add_error("username", "That username is already taken.")
            else:
                user = User.objects.create_superuser(username, "", form.cleaned_data["password"])
                login(request, user)
                return redirect("setup-drive")
    else:
        form = AdminAccountForm()
    return render(request, "photos/setup_admin.html", {"form": form})


def drive_view(request):
    if not _setup_accessible(request):
        return _denied()

    client_secret_path = _client_secret_path()
    token_path = _token_path()
    has_client_secret = bool(client_secret_path and os.path.exists(client_secret_path))
    has_token = bool(token_path and os.path.exists(token_path))
    error = None

    if request.method == "POST":
        if "skip" in request.POST:
            return redirect("setup-network")

        if "upload_client_secret" in request.POST:
            client_secret_form = DriveClientSecretForm(request.POST, request.FILES)
            if client_secret_form.is_valid():
                os.makedirs(os.path.dirname(client_secret_path) or ".", exist_ok=True)
                with open(client_secret_path, "wb") as f:
                    for chunk in client_secret_form.cleaned_data["client_secret_file"].chunks():
                        f.write(chunk)
                return redirect("setup-drive")
        elif "choose_folder" in request.POST:
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
                error = str(exc)
            else:
                site_settings = SiteSettings.get_solo()
                site_settings.drive_root_folder_id = folder_id
                site_settings.save(update_fields=["drive_root_folder_id"])
                return redirect("setup-network")

    return render(request, "photos/setup_drive.html", {
        "client_secret_form": DriveClientSecretForm(),
        "has_client_secret": has_client_secret,
        "has_token": has_token,
        "folders": _safe_list_folders() if has_token else None,
        "redirect_uri": request.build_absolute_uri(reverse("setup-google-callback")),
        "error": error,
    })


def google_connect_view(request):
    if not _setup_accessible(request):
        return _denied()
    flow = _google_flow(request)
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["google_oauth_state"] = state
    return redirect(auth_url)


def google_callback_view(request):
    if not _setup_accessible(request):
        return _denied()
    flow = _google_flow(request)
    flow.state = request.session.get("google_oauth_state")
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    token_path = _token_path()
    os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
    with open(token_path, "w") as f:
        f.write(flow.credentials.to_json())
    return redirect("setup-drive")


def network_view(request):
    if not _setup_accessible(request):
        return _denied()
    site_settings = SiteSettings.get_solo()
    if request.method == "POST":
        form = NetworkForm(request.POST)
        if form.is_valid():
            site_settings.server_host = form.cleaned_data["server_host"].strip()
            site_settings.save(update_fields=["server_host"])
            return redirect("setup-event")
    else:
        initial_host = site_settings.server_host or request.get_host()
        form = NetworkForm(initial={"server_host": initial_host})
    return render(request, "photos/setup_network.html", {"form": form})


def first_event_view(request):
    if not _setup_accessible(request):
        return _denied()
    if request.method == "POST":
        form = FirstEventForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            event = Event.objects.filter(name=name).first()
            if event is None:
                event = Event.objects.create(name=name)
            if not event.drive_folder_id and drive_service.is_configured():
                event_service.ensure_drive_folder(event)
            event_service.switch_active_event(event)
            return redirect("dashboard")
    else:
        form = FirstEventForm()
    return render(request, "photos/setup_event.html", {"form": form})
