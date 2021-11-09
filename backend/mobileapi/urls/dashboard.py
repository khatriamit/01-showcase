from django.urls import path
from mobileapi.views.dashboard import (
    DashboardEarningAnalyticsView,
    DashboardTodaysBookingView,
    DashboardTotalBooking,
    DashboardTotalAnalytics,
    DashboardTodayToBeCheckInListView
)


urlpatterns = [
    path("dashboard_earning_analytics/", DashboardEarningAnalyticsView.as_view()),
    path("dashboard_todays_booking/", DashboardTodaysBookingView.as_view()),
    path("dashboard_total_booking/", DashboardTotalBooking.as_view()),
    path("dashboard_total_analytics/", DashboardTotalAnalytics.as_view()),
    path("dashboard_today_checkin/", DashboardTodayToBeCheckInListView.as_view())
]
