"""Intentionally vulnerable Django examples for SAST validation only.

This file is parsed by SonarQube but is not imported by the sample service.
"""

from django.db import connection
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def unsafe_login(request):
    username = request.POST.get("username", "")
    password = request.POST.get("password", "")
    query = (
        "SELECT id FROM users "
        f"WHERE username = '{username}' AND password = '{password}'"
    )
    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
    return HttpResponse(str(row))


def unsafe_html_preview(request):
    untrusted_html = request.GET.get("html", "")
    return HttpResponse(mark_safe(untrusted_html))
