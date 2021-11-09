from django.urls import path
from mobileapi.views.booking_search import BookingSearchAPIView


urlpatterns = [
    path("booking_search/", BookingSearchAPIView.as_view())
]