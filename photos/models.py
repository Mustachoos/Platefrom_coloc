import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def photo_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    username_part = slugify(instance.username) or "user"
    time_part = timezone.localtime().strftime("%Hh%M")
    unique_id = uuid.uuid4().hex[:8]
    return f"photos/{username_part}_{time_part}_{unique_id}{ext}"


def default_drive_folder_name():
    return timezone.localtime().strftime("%d/%m/%Y")


def whiteboard_upload_path(instance, filename):
    username_part = slugify(instance.username) or "user"
    time_part = timezone.localtime().strftime("%Hh%M")
    unique_id = uuid.uuid4().hex[:8]
    return f"whiteboard/{username_part}_{time_part}_{unique_id}.png"


def whiteboard_board_path(instance, filename):
    return f"whiteboard/boards/board_{instance.pk}_{uuid.uuid4().hex[:8]}.png"


class Event(models.Model):
    """One 'soirée': its own guests, photos, and (optionally) Drive folder.

    Exactly one Event has is_active=True at a time — that's the one the
    public pages (upload, tv, gallery) read and write. A connected Drive
    folder is optional but recommended: switching away from an event with
    one backs up/restores its photos safely through it; an event with no
    Drive folder just keeps its local photos in place (hidden, not deleted)
    while it's inactive, with no off-machine backup.
    """

    name = models.CharField(max_length=200, unique=True, default=default_drive_folder_name)
    is_active = models.BooleanField(default=False)
    drive_folder_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="Auto-filled from the event name above. To point to a different/existing "
        "folder instead, paste its Drive URL or ID here directly.",
    )
    drive_folder_url = models.URLField(blank=True)
    drive_sharing_enabled = models.BooleanField(
        default=False,
        help_text="When on, every guest with an email on file is added as a reader on the "
        "Drive folder. When off, that access is revoked for all of them.",
    )
    likes_enabled = models.BooleanField(
        default=True,
        help_text="When off, the heart/like button is hidden and the TV leaderboard is hidden.",
    )
    whiteboard_enabled = models.BooleanField(
        default=False,
        help_text="When on, guests get a button on the home page to draw on the collective whiteboard.",
    )
    WIFI_SECURITY_WPA = "WPA"
    WIFI_SECURITY_WEP = "WEP"
    WIFI_SECURITY_NOPASS = "NOPASS"
    WIFI_SECURITY_CHOICES = [
        (WIFI_SECURITY_WPA, "WPA / WPA2 / WPA3"),
        (WIFI_SECURITY_WEP, "WEP"),
        (WIFI_SECURITY_NOPASS, "Open (no password)"),
    ]
    wifi_qr_enabled = models.BooleanField(
        default=False,
        help_text="When on, a second QR code to join the Wi-Fi is shown next to the upload QR code on the TV screen.",
    )
    wifi_ssid = models.CharField(max_length=100, blank=True, verbose_name="Wi-Fi network name (SSID)")
    wifi_password = models.CharField(max_length=200, blank=True, verbose_name="Wi-Fi password")
    wifi_security = models.CharField(max_length=10, choices=WIFI_SECURITY_CHOICES, default=WIFI_SECURITY_WPA)
    TV_LAYOUT_SLIDESHOW = "slideshow"
    TV_LAYOUT_WHITEBOARD = "whiteboard"
    TV_LAYOUT_CHOICES = [
        (TV_LAYOUT_SLIDESHOW, "Photo slideshow"),
        (TV_LAYOUT_WHITEBOARD, "Collective whiteboard"),
    ]
    tv_layout = models.CharField(max_length=20, choices=TV_LAYOUT_CHOICES, default=TV_LAYOUT_SLIDESHOW)
    TV_BOTTOM_RIGHT_LEADERBOARD = "leaderboard"
    TV_BOTTOM_RIGHT_NONE = "none"
    TV_BOTTOM_RIGHT_CHOICES = [
        (TV_BOTTOM_RIGHT_LEADERBOARD, "Leaderboard"),
        (TV_BOTTOM_RIGHT_NONE, "Nothing"),
    ]
    tv_bottom_right = models.CharField(
        max_length=20, choices=TV_BOTTOM_RIGHT_CHOICES, default=TV_BOTTOM_RIGHT_LEADERBOARD
    )
    whiteboard_image = models.ImageField(upload_to=whiteboard_board_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class Photo(models.Model):
    event = models.ForeignKey(Event, related_name="photos", on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    image = models.ImageField(upload_to=photo_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    drive_file_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.username} - {self.uploaded_at:%Y-%m-%d %H:%M}"

    @property
    def filename(self):
        return os.path.basename(self.image.name)

    @property
    def likes_count(self):
        return self.likes.count()


class WhiteboardDrawing(models.Model):
    """One guest's contribution to the collective whiteboard: a transparent
    PNG layer, stacked on top of every earlier surviving layer (oldest
    first) to render the current board. Storing layers separately (rather
    than only keeping the flattened board) is what lets an admin delete a
    single guest's drawing out of the middle of the stack."""

    event = models.ForeignKey(Event, related_name="whiteboard_drawings", on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    image = models.ImageField(upload_to=whiteboard_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.username} - {self.uploaded_at:%Y-%m-%d %H:%M}"


class UserIdentity(models.Model):
    event = models.ForeignKey(Event, related_name="identities", on_delete=models.CASCADE)
    pseudo = models.CharField(max_length=50)
    session_key = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    drive_shared = models.BooleanField(default=False)
    drive_permission_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("event", "pseudo"), ("event", "session_key"))

    def __str__(self):
        return f"{self.pseudo} ({self.event.name})"


class Like(models.Model):
    photo = models.ForeignKey(Photo, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(UserIdentity, related_name="likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("photo", "user")

    def __str__(self):
        return f"{self.user.pseudo} ♥ {self.photo.id}"


class SiteSettings(models.Model):
    server_host = models.CharField(
        max_length=255,
        blank=True,
        help_text="Address guests' phones use to reach this server (e.g. 192.168.1.13:8000), "
        "encoded in the upload QR code. Only ever set by scanning the verification QR code on "
        "the admin account page — that's what proves the address is actually reachable. Leave "
        "blank to fall back to whatever address loaded the current page.",
    )
    drive_root_folder_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="ID of the Drive folder under which each event creates its own subfolder. "
        "Set from the setup wizard's Drive step (or the GOOGLE_DRIVE_ROOT_FOLDER_ID env var, "
        "which takes priority if set).",
    )
    support_email = models.EmailField(
        blank=True,
        help_text="Gmail address used to send admin password-reset emails. Auto-filled from "
        "whichever Google account is connected via OAuth2 (see gmail_service.py) — never "
        "typed in directly, since Google no longer accepts plain-password Gmail logins.",
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return f"Site settings: {self.server_host or '(not set)'}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AdminInvite(models.Model):
    """A single-use link the admin can hand out so someone else can create
    their own subadmin account (is_staff, not is_superuser) without needing
    the admin's own credentials."""

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_REVOKED = "revoked"
    STATUS_EXPIRED = "expired"

    EXPIRY = timedelta(hours=1)

    invitee_name = models.CharField(
        max_length=150, help_text="Who this invite link was generated for."
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="invites_created", on_delete=models.CASCADE
    )
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="used_invite", null=True, blank=True, on_delete=models.SET_NULL
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite for {self.invitee_name} ({self.status})"

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + self.EXPIRY

    @property
    def status(self):
        if self.revoked_at:
            return self.STATUS_REVOKED
        if self.used_at:
            return self.STATUS_ACTIVE
        if self.is_expired:
            return self.STATUS_EXPIRED
        return self.STATUS_PENDING


class SlideshowSettings(models.Model):
    interval_seconds = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(100)],
        help_text="How long each photo stays on screen, in seconds (0.1-100).",
    )

    class Meta:
        verbose_name = "Slideshow settings"
        verbose_name_plural = "Slideshow settings"

    def __str__(self):
        return f"Slideshow interval: {self.interval_seconds}s"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
