from django.contrib.auth.models import User
from django.shortcuts import redirect


class FirstRunRedirectMiddleware:
    """While no superuser exists yet, every page funnels to admin account
    creation instead of letting guests reach upload/gallery/etc. on a
    freshly cloned, unclaimed install."""

    EXEMPT_PREFIXES = ("/create-admin/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(self.EXEMPT_PREFIXES):
            if not User.objects.filter(is_superuser=True).exists():
                return redirect("create-admin")
        return self.get_response(request)
