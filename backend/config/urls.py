from django.urls import path

from api.views import analyze_routes, geocode, heatmap_view

urlpatterns = [
    path("api/geocode", geocode, name="geocode"),
    path("api/routes/analyze", analyze_routes, name="analyze-routes"),
    path("api/heatmap", heatmap_view, name="heatmap"),
]
