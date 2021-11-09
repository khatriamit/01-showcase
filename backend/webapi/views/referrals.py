from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from webapi.serializers.referrals import (
    ReferralSerializer,
    UserReferPointStatSerializer,
    SecondaryReferralSerializer,
)
from users.models import Referrals, UserReferPointStat, SecondaryUserReferral
from backend.utils import CustomPageSizePagination


class ReferralsView(APIView, CustomPageSizePagination):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReferralSerializer

    def get(self, request, *args, **kwargs):
        queryset = Referrals.objects.filter(referred_by=self.request.user)
        page = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)


class UserReferralsPointStatView(APIView, CustomPageSizePagination):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserReferPointStatSerializer

    def get(self, request, *args, **kwargs):
        queryset = UserReferPointStat.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )
        page = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)


class SecondaryUserReferralView(APIView, CustomPageSizePagination):
    permission_classes = (IsAuthenticated,)
    serializer_class = SecondaryReferralSerializer

    def get(self, request, *args, **kwargs):
        queryset = SecondaryUserReferral.objects.filter(
            main_referred_by=self.request.user
        ).order_by("-created_date")
        page = self.paginate_queryset(queryset, request)
        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)
