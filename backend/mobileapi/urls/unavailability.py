from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mobileapi.views.unavailability import OrganisationRoomUnAvailabilityViewset

router = DefaultRouter()
router.register('room_unavailability', OrganisationRoomUnAvailabilityViewset)

urlpatterns = [
    path('', include(router.urls))
]
