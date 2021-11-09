from django.db.models import Q, Case, When, Value, CharField
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
import datetime

from rest_framework.response import Response

from mobileapi.serializers.special_deal import OrganisationSpecialDealSerializer
from organisation.models import OrganisationSpecialDeal, Organisation


def special_deal_validation(request):
    """
    helper function to validate special deals during create and update
    """

    if request.data.get("from_date"):
        if (
            datetime.datetime.strptime(request.data.get("from_date"), "%Y-%m-%d").date()
            < datetime.date.today()
        ):
            raise ValidationError(
                {"invalid_from_date": "from_date should not accept past dates"}
            )
    if request.data.get("to_date"):
        if (
            datetime.datetime.strptime(request.data.get("to_date"), "%Y-%m-%d").date()
            <= datetime.date.today()
        ):
            raise ValidationError(
                {"invalid_to_date": "to_date should not accept past dates"}
            )
    if request.data.get("discount_off") and not request.data.get("discount_percentage"):
        raise ValidationError({"invalid": "Discount percentage can't be empty"})


class OrganisationSpecialDealViewset(viewsets.ModelViewSet):
    """
    organisation special deal viewset
    """

    queryset = OrganisationSpecialDeal.objects.none()
    # permission_classes = (IsAuthenticated, )
    serializer_class = OrganisationSpecialDealSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["discount_code", "organisation"]
    search_fields = ["name"]
    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "list": [AllowAny],
        "update": [IsAuthenticated],
        "delete": [IsAuthenticated],
        "retrieve": [AllowAny],
    }

    def get_queryset(self):
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        special_deal_status = self.request.query_params.get("status")
        room_type = self.request.query_params.get("room_type")
        q = self.request.query_params.get("q")
        property_type = self.request.query_params.get("property_type")
        if self.request.query_params.get("mine") == "true":
            if self.request.user.is_authenticated:
                queryset = OrganisationSpecialDeal.objects.filter(
                    organisation__user=self.request.user, is_deleted=False
                )
            else:
                raise ValidationError(
                    {"detail": "Authentication credentials were not provided."}
                )
        else:
            queryset = OrganisationSpecialDeal.objects.filter(is_deleted=False).exclude(
                to_date__lt=datetime.date.today()
            )
        if q:
            queryset = queryset.filter(
                Q(organisation__location__city__icontains=q)
                | Q(organisation__location__country__icontains=q)
                | Q(organisation__location__street_name__icontains=q)
                | Q(organisation__location__street_address__icontains=q)
                | Q(organisation__location__zip_code__icontains=q)
                | Q(organisation__name__icontains=q)
                | Q(organisation__category__name__icontains=q)
            )

        queryset = queryset.annotate(
            upcoming=Case(
                When(from_date__gt=datetime.date.today(), then=Value(True)),
                default=False,
                output_field=CharField(),
            )
        )
        queryset = queryset.annotate(
            ongoing=Case(
                When(
                    from_date__lte=datetime.date.today(),
                    to_date__gte=datetime.date.today(),
                    then=Value(True),
                ),
                default=False,
                output_field=CharField(),
            )
        )
        if self.request.query_params.get("upcoming"):
            queryset = queryset.filter(upcoming=True)

        if self.request.query_params.get("ongoing"):
            queryset = queryset.filter(ongoing=True)

        if property_type:
            queryset = queryset.filter(organisation__category__id=property_type)
        if from_date:
            queryset = queryset.filter(from_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(to_date__lte=to_date)

        if from_date and to_date:
            queryset = queryset.filter(from_date__gte=from_date, to_date__lte=to_date)
        if special_deal_status == "active":
            queryset = queryset.filter(to_date__gte=datetime.date.today())
        elif special_deal_status == "expired":
            queryset = queryset.filter(to_date__lt=datetime.date.today())
        if room_type:
            queryset = queryset.filter(category__icontains=room_type)
        for q in list(queryset):
            if q.to_date >= datetime.date.today():
                q.status = "Active"
            elif q.to_date < datetime.date.today():
                q.status = "Expired"
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organisation = self.request.data.get("organisation")
        special_deal_validation(request)
        if Organisation.objects.filter(
            id=organisation, user=self.request.user
        ).exists():
            organisation_room_categories = Organisation.objects.filter(
                id=organisation, user=self.request.user
            ).values("rooms__category")
            categories = [
                category.get("rooms__category")
                for category in list(organisation_room_categories)
            ]
            applied_categories = request.data.get("category")
            for category in applied_categories:
                if category not in categories:
                    raise ValidationError(
                        {
                            "unauthorized": f"you don't have any room with room category {category}"
                        }
                    )
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        raise ValidationError(
            {"permission": "you don't have enough permission to perform this action"}
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        organisation = self.request.data.get("organisation")
        special_deal_validation(self.request)
        if Organisation.objects.filter(
            id=organisation, user=self.request.user
        ).exists():
            self.perform_update(serializer)
            if getattr(instance, "_prefetched_objects_cache", None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}
            return Response(serializer.data)

        raise ValidationError(
            {"permission": "you don't have enough permission to perform this action"}
        )

    def get_permissions(self):
        try:
            # return permission_classes depending on `action`
            return [
                permission()
                for permission in self.permission_classes_by_action[self.action]
            ]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]
