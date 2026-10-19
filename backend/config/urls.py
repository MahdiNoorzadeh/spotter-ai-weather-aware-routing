from django.urls import path

from api.views import analyze_routes, geocode

urlpatterns = [
    path("api/geocode", geocode, name="geocode"),
    path("api/routes/analyze", analyze_routes, name="analyze-routes"),
]
