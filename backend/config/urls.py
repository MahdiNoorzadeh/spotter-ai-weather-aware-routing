
from django.urls import path

from api.views import analyze_routes, geocode, health_check, heatmap_view

urlpatterns = [
    path("api/health", health_check, name="health-check"),
    path("api/geocode", geocode, name="geocode"),
    path("api/routes/analyze", analyze_routes, name="analyze-routes"),
    path("api/heatmap", heatmap_view, name="heatmap"),
]
