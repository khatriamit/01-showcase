from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
import datetime
from organisation.models import Organisation, Room, OrganisationRoomPricing
from mobileapi.serializers.pricing import (
    OrganisationRoomPricingSerializer,
)
from mobileapi.utils.custom_filter import RoomPricingFilter


class OrganisationRoomUnPricingViewset(viewsets.ModelViewSet):
    """
    api view to set organisation room pricing CRUD:
    """
    serializer_class = OrganisationRoomPricingSerializer
    queryset = OrganisationRoomPricing.objects.none()
    filter_backends = [DjangoFilterBackend]
    filter_class = RoomPricingFilter
    permission_classes_by_action = {'create': [IsAuthenticated],
                                    'list': [AllowAny],
                                    'update': [IsAuthenticated],
                                    'delete': [IsAuthenticated],
                                    'retrieve': [AllowAny]}

    def get_queryset(self):
        queryset = OrganisationRoomPricing.objects.filter(is_deleted=False).exclude(to_date__lt=datetime.date.today())
        property = self.request.query_params.get("property")
        if property:
            queryset = queryset.filter(organisation__id=property)
        return queryset

    def perform_create(self, serializer):
        organisation = self.request.query_params.get("organisation")
        if organisation:
            try:
                Organisation.objects.get(id=organisation, user=self.request.user)
            except Organisation.DoesNotExist:
                raise PermissionDenied({"unauthorized": "you dont have enough permission"})
            serializer.save(organisation=Organisation(id=organisation), created_by=self.request.user)
        else:
            raise ValidationError({"organisation_id": "Organisation id is required query parameter"})

    def get_permissions(self):
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]