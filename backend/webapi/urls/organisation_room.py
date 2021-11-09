from django.urls import path
from webapi.views.organisation_room import OrganisationRoomDetailAPIView

urlpatterns = [
    path("organisation-room-detail", OrganisationRoomDetailAPIView.as_view())
]
