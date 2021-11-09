from django.urls import path
from webapi.views.organisation import (
    UserSearchHistoryAPIView,
    PopularDestinationAPIView,
    OrganisationRoomListAPIView,
    OrganisationRoomAvailability,
)
from webapi.views.calendar_price import OrganisationCalendarPricingAPIView

urlpatterns = [
    path("search_history/", UserSearchHistoryAPIView.as_view(), name="search_history"),
    path(
        "popular_destination/",
        PopularDestinationAPIView.as_view(),
        name="popular_destination",
    ),
    path(
        "organisation_calendar_price/",
        OrganisationCalendarPricingAPIView.as_view(),
        name="organisation_pricing",
    ),
    path("organisation_rooms/", OrganisationRoomListAPIView.as_view()),
    path("room-availability", OrganisationRoomAvailability.as_view()),
]
