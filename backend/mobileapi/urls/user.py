from django.urls import path, include
from mobileapi.views.user import UserInfoView


urlpatterns = [
    path('user/profile/', UserInfoView.as_view()),
]
