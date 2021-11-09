from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mobileapi.views.pricing import OrganisationRoomUnPricingViewset

router = DefaultRouter()
router.register('room_pricing', OrganisationRoomUnPricingViewset)

urlpatterns = [
    path('', include(router.urls))
]