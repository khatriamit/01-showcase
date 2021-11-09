from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mobileapi.views.room import OrganisationRoomView
from mobileapi.views.organisation import (
    OrganisationDetailView,
    OrganisationListView,
    MineOrganisationListView,
    OrganisationRoomCategoryAPIListView
)
from organisation.views import PropertyCategoryViewset
from mobileapi.viewsets.organisation import UserOrganisationFavouriteViewSet
from mobileapi.views.organisation import HotelRecommendationAPIView, OrganisationFetchRoomNumberAPIView

router = DefaultRouter()
router.register('property-category', PropertyCategoryViewset)
router.register('organisation-favourite', UserOrganisationFavouriteViewSet)

urlpatterns = [
    path('organisations/', OrganisationListView.as_view()),
    path('organisation/<pk>/', OrganisationDetailView.as_view()),
    path('organisation-rooms/', OrganisationRoomView.as_view()),
    path('recommendation/organisation/', HotelRecommendationAPIView.as_view()),
    path('my/organisations/', MineOrganisationListView.as_view()),
    path('get/room_numbers/', OrganisationFetchRoomNumberAPIView.as_view()),
    path("organisation_room_categories/", OrganisationRoomCategoryAPIListView.as_view()),
    path('', include(router.urls))
]