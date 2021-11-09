from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mobileapi.viewsets.booking import UserBookedByViewset

router = DefaultRouter()

router.register("bookings", UserBookedByViewset, basename='user-booked-by')

urlpatterns = [
    path('', include(router.urls)),
]
