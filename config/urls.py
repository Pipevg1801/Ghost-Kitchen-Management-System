from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("menu.urls")),
    path("", include("orders.urls")),
    path("", include("reports.urls")),
]
