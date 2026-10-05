from django.urls import path

from .views import TripPlanView

urlpatterns = [
    path("route/", TripPlanView.as_view(), name="trip-plan"),
]