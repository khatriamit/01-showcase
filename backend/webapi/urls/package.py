from django.urls import path, include
from rest_framework.routers import DefaultRouter

from webapi.views.package import (
    PackageListView,
    PackageDetailAPIView,
    PackageBookingAPI,
    PackageViewset,
    PackageSearchAPIView,
    PackageTypeListView,
    PopularPackageListAPIView,
    PackageNameSuggestion,
)

router = DefaultRouter()
router.register("package_booking", PackageBookingAPI)
router.register("packages", PackageViewset)

urlpatterns = [
    path("package/", PackageListView.as_view()),
    path("package/<pk>/", PackageDetailAPIView.as_view()),
    path("", include(router.urls)),
    path("package_search_result/", PackageSearchAPIView.as_view()),
    path("package_type/", PackageTypeListView.as_view(), name="package_list"),
    path(
        "popular_package/",
        PopularPackageListAPIView.as_view(),
        name="popular_package_list",
    ),
    path("package_name_suggestion/", PackageNameSuggestion.as_view()),
]
