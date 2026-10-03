from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("admin-panel/", views.dashboard, name="dashboard"),
    path("informes/", views.informes, name="informes"),
    path("informes/consolidado/", views.consolidado, name="consolidado"),
    path("informes/grafico/", views.grafico, name="grafico"),
    path("informes/grafico/datos/", views.grafico_datos, name="grafico_datos"),
    path("informes/tabular/", views.tabular, name="tabular"),
]
