from django.urls import path
from webapi.views.booking import (
    UpdateBookingAPIView,
    UpdateBookingUserInfo,
    UpdateBookingDetailView,
    GetBookingPriceDetail,
    UpdateBookingCheckoutView,
    GetUpdatedCheckoutPricing,
    CancelBooking
)

urlpatterns = [
    # path("update_booking/<id>/", UpdateBookingAPIView.as_view()),
    path("update/user-info/<id>/", UpdateBookingUserInfo.as_view()),
    path("update/booking-detail/<id>/", UpdateBookingDetailView.as_view()),
    path("get-booking-pricing/<id>/", GetBookingPriceDetail.as_view()),
    path("update/checkout-date/<id>/", UpdateBookingCheckoutView.as_view()),
    path("updated/pricing-detail/<id>/", GetUpdatedCheckoutPricing.as_view()),
    path("cancel-booking/", CancelBooking.as_view(), name="cancel-booking")
]
