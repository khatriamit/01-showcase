import math

from django.db.models import Q, Avg, Count, Min, Max, F, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import filters
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
import datetime

import pandas as pd
from booking.models import RatingByIndividual
from mobileapi.serializers.organisation import *
from mobileapi.serializers.organisation import OrganisationListFilterInfoSerilizer
from backend.utils import hotel_recommendor_model
from booking.models import BookingDetail
from mobileapi.serializers.organisation import OrganisationFetchRoomNumberSerializer
from django.db.models.query import Prefetch
from organisation.models import OrganisationRoomUnavailability, Organisation
from mobileapi.utils.helpers import get_country_flag, validate_rating
from backend.utils import (
    CustomPageSizePagination,
    OrganisationListCustomPageSizePagination,
)
from mobileapi.utils.helpers import get_filter_organisations
from webapi.utils.helpers import get_client_ip, get_visitor_info


class OrganisationListView(generics.ListAPIView):
    """
    viewset for the organisation with all the necessary description of organisation
    """

    queryset = Organisation.objects.filter(
        is_deleted=False, property_status="Published"
    )
    serializer_class = OrganisationListInfoSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    # filter_class = CustomPropertyFilter
    search_fields = [
        "location",
        "ratings",
        "category__name",
        "name",
        "facilities",
    ]
    filter_fields = ["category"]
    ordering_fields = ["views"]

    def get_queryset(self):
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        facilities = self.request.query_params.get("facilities")
        city = self.request.query_params.get("city")
        queryset = self.queryset
        search_key = self.request.query_params.get("search_key")
        if search_key:
            queryset = queryset.filter(
                Q(name__icontains=search_key)
                | Q(location__city__icontains=search_key)
                | Q(location__country__icontains=search_key)
                | Q(category__name__icontains=search_key)
            )

        if facilities:
            queryset = queryset.filter(facilities__contains=facilities)

        if city:
            queryset = queryset.filter(location__city=city)

        if max_price or min_price:
            organisation_ids = Room.objects.filter(
                price__lte=max_price if max_price else 100000,
                price__gte=min_price if min_price else 0,
            ).values("organisation__id")
            queryset = queryset.filter(id__in=organisation_ids).prefetch_related(
                Prefetch(
                    "rooms",
                    queryset=Room.objects.filter(
                        price__lte=max_price if max_price else 100000,
                        price__gte=min_price if min_price else 0,
                    ),
                )
            )

        queryset = queryset.annotate(user_rating=Avg("rating__rating_star") or 0)
        if self.request.query_params.get("ratings"):
            queryset = queryset.filter(
                user_rating=self.request.query_params.get("ratings")
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            favourite_organisation = []
            if request.user.is_authenticated:
                favourite_organisation = UserOrganisationFavorites.objects.filter(
                    user=request.user
                ).values("organisation__id")
                favourite_organisation = [
                    i.get("organisation__id") for i in favourite_organisation
                ]
                if self.request.query_params.get("favourite") == "true":
                    queryset = queryset.filter(id__in=favourite_organisation)

                elif self.request.query_params.get("favourite") == "false":
                    queryset = queryset.exclude(id__in=favourite_organisation)
                page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)

            for q in serializer.data:
                if q.get("id") in favourite_organisation:
                    q["favourite"] = True
                else:
                    q["favourite"] = False
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrganisationListViewV2(generics.ListAPIView):
    """
    viewset for the organisation with all the necessary description of organisation
    """

    serializer_class = OrganisationListFilterInfoSerilizer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    # filter_class = CustomPropertyFilter
    search_fields = [
        "location",
        "category__name",
        "name",
        "facilities",
    ]
    filter_fields = ["category"]
    ordering_fields = ["views"]
    pagination_class = OrganisationListCustomPageSizePagination
    # page_size = 5

    def get_serializer_context(self, request, *args, **kwargs):
        context = super(OrganisationListViewV2, self).get_serializer_context(
            request, *args, **kwargs
        )
        context["user"] = self.request.user
        print(context)
        return context

    def get_queryset(self):
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        facilities = self.request.query_params.get("facilities")
        city = self.request.query_params.get("city")
        checkin_date = self.request.query_params.get("checkin_date")
        checkout_date = self.request.query_params.get("checkout_date")
        queryset = Organisation.objects.filter(
            is_deleted=False, property_status="Published", is_visible=True
        ).order_by("-pk")
        rooms = Room.objects.filter(is_deleted=False).annotate(
            number_of_available_rooms=F("no_of_rooms")
            - Coalesce(
                Sum(
                    "booked_room__no_of_rooms",
                    filter=Q(
                        booked_room__booking__is_deleted=False,
                        booked_room__booking__checkin_date__gte=datetime.date.today(),
                        booked_room__booking__checkout_date__gt=datetime.date.today(),
                    ),
                ),
                0,
            )
        )
        if min_price and float(min_price) < 0:
            raise ValidationError({"error": "min_price must be valid positive value"})

        if max_price and float(max_price) < 0:
            raise ValidationError({"error": "max_price must be valid positive value"})

        if min_price and max_price:
            if max_price < min_price:
                raise ValidationError(
                    {"error": "max_price should not be less than min price"}
                )

        search_key = self.request.query_params.get("search_key")
        if search_key:
            queryset = queryset.filter(
                Q(name__icontains=search_key)
                | Q(location__city__icontains=search_key)
                | Q(location__country__icontains=search_key)
                | Q(category__name__icontains=search_key)
            )

        if facilities:
            queryset = queryset.filter(facilities__contains=facilities)

        if city:
            queryset = queryset.filter(location__city=city)

        if checkin_date and checkout_date:
            if (
                datetime.datetime.strptime(checkin_date, "%Y-%m-%d").date()
                < datetime.date.today()
            ):
                raise ValidationError({"error": "Invalid checkin date"})
            if (
                datetime.datetime.strptime(checkout_date, "%Y-%m-%d").date()
                <= datetime.date.today()
            ):
                raise ValidationError({"error": "Invalid checkout date"})

            if (
                datetime.datetime.strptime(checkin_date, "%Y-%m-%d").date()
                > datetime.datetime.strptime(checkout_date, "%Y-%m-%d").date()
            ):
                raise ValidationError(
                    {"error": "checkin date should not be greater than checkout date"}
                )

        elif checkin_date:
            raise ValidationError({"error": "checkout_date is required"})

        elif checkout_date:
            raise ValidationError({"error": "checkin_date is required"})

        if max_price or min_price:
            organisation_ids = rooms.filter(
                price__lte=max_price if max_price else 100000,
                price__gte=min_price if min_price else 0,
            ).values("organisation__id")
            queryset = queryset.filter(id__in=organisation_ids).prefetch_related(
                Prefetch(
                    "rooms",
                    queryset=rooms.filter(
                        price__lte=max_price if max_price else 100000,
                        price__gte=min_price if min_price else 0,
                        number_of_available_rooms__gt=0,
                    ),
                )
            )
        elif max_price and min_price:
            organisation_ids = rooms.filter(
                price__lte=max_price,
                price__gte=min_price,
            ).values("organisation__id")
            queryset = queryset.filter(id__in=organisation_ids).prefetch_related(
                Prefetch(
                    "rooms",
                    queryset=rooms.filter(
                        price__lte=max_price,
                        price__gte=min_price,
                        number_of_available_rooms__gt=0,
                    ),
                )
            )

        queryset = queryset.annotate(
            user_rating=Avg("rating__rating_star", filter=Q(rating__is_deleted=False))
        )

        if self.request.query_params.get("ratings"):
            queryset = validate_rating(
                self.request.query_params.get("ratings"), queryset
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.annotate(min_room_price=Min("rooms__price"))
        page_size = int(self.request.query_params.get("page_size", 10))
        page_no = int(self.request.query_params.get("page_no", 0))
        queryset = queryset.annotate(
            user_review_count=Count(
                "rating", distinct=True, filter=Q(rating__is_deleted=False)
            )
        )
        rating_filter_count = {}
        rating_filter_count.update(
            {
                "rating_start": 5,
                "rating_star_count": queryset.filter(user_rating=5).count(),
            }
        )
        return self.get_paginated_response(queryset)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data, self.request)


class OrganisationListViewV3(generics.ListAPIView):
    """
    viewset for the organisation with all the necessary description of organisation
    """

    serializer_class = OrganisationListInfoSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    # filter_class = CustomPropertyFilter
    search_fields = [
        "location",
        "category__name",
        "name",
        "facilities",
    ]
    ordering_fields = ["views"]
    pagination_class = CustomPageSizePagination

    def get_queryset(self):
        queryset = get_filter_organisations(self.request)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.annotate(category_name=F("category__name"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for data in serializer.data:
                if (
                    self.request.user.is_authenticated
                    and UserOrganisationFavorites.objects.filter(
                        organisation__id=data.get("id"), user=self.request.user
                    ).exists()
                ):
                    data.update({"is_favourite": True})
                else:
                    data.update({"is_favourite": False})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrganisationSearchResult(APIView):
    def get(self, request, *args, **kwargs):
        queryset = get_filter_organisations(self.request)
        rating_filter_count = []
        for i in range(1, 6):
            rating_filter_count.append(
                {
                    "rating_star": i,
                    "rating_star_count": queryset.filter(user_rating=i).count(),
                }
            )
        property_type_filter_count = []
        property_categorys = list(PropertyCategory.objects.all())
        for category in property_categorys:
            property_type_filter_count.append(
                {
                    "id": category.id,
                    "property_type": category.name,
                    "property_type_count": queryset.filter(
                        category__id=category.id
                    ).count(),
                }
            )

        facility_filter_count = []
        FACILITIES_PROPERTY_OPTIONS = (
            ("Desk/workspace", "Desk/workspace"),
            ("Private pool", "Private pool"),
            ("Gym", "Gym"),
        )
        for facility in FACILITIES_PROPERTY_OPTIONS:
            facility_filter_count.append(
                {
                    "facility_name": facility[1],
                    "facility_count": queryset.filter(
                        facilities__contains=facility
                    ).count(),
                }
            )
        min_room_price = queryset.aggregate(Min("rooms__price")).get(
            "rooms__price__min"
        )
        max_room_price = queryset.aggregate(Max("rooms__price")).get(
            "rooms__price__max"
        )
        res = {
            "min_room_price": min_room_price,
            "max_room_price": max_room_price,
            "facility_filter_count": facility_filter_count,
            "property_type_filter_count": property_type_filter_count,
            "rating_filter_count": rating_filter_count,
        }
        return Response(res)


class OrganisationDetailView(generics.RetrieveAPIView):
    """
    viewset for the organisation with all the necessary description of organisation
    """

    queryset = Organisation.objects.filter(
        property_status="Published", is_deleted=False, is_visible=True
    )
    serializer_class = OrganisationSerializer

    def get_object(self):
        # rooms = Room.objects.filter(
        #     is_deleted=False, organisation=self.kwargs.get("pk")
        # ).annotate(
        #     number_of_available_rooms=F("no_of_rooms")
        #     - Coalesce(
        #         Sum(
        #             "booked_room__no_of_rooms",
        #             distinct=True,
        #             filter=Q(
        #                 booked_room__booking__is_deleted=False,
        #                 booked_room__booking__checkin_date__gte=datetime.date.today(),
        #                 booked_room__booking__checkout_date__gt=datetime.date.today(),
        #             ),
        #         ),
        #         0,
        #     )
        # )
        queryset = (
            self.get_queryset()
            .filter(is_deleted=False, is_visible=True, property_status="Published")
            .annotate(
                rating_location_average=Avg(
                    "rating__location", filter=Q(rating__is_deleted=False)
                ),
                rating_comfort_average=Avg(
                    "rating__comfort", filter=Q(rating__is_deleted=False)
                ),
                rating_personnel_average=Avg(
                    "rating__personnel", filter=Q(rating__is_deleted=False)
                ),
                rating_cleanliness_average=Avg(
                    "rating__cleanliness", filter=Q(rating__is_deleted=False)
                ),
                rating_good_offer_average=Avg(
                    "rating__good_offer", filter=Q(rating__is_deleted=False)
                ),
                rating_service_average=Avg(
                    "rating__service", filter=Q(rating__is_deleted=False)
                ),
            )
        )
        queryset = self.filter_queryset(queryset)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)

        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user_rating = RatingByIndividual.objects.filter(
            rated_on__id=instance.id, is_deleted=False
        ).aggregate(Avg("rating_star"))
        instance.user_rating = user_rating.get("rating_star__avg")
        instance.favourite = False
        instance.user_review_count = RatingByIndividual.objects.filter(
            rated_on__id=instance.id, is_deleted=False
        ).count()
        instance.favourite = False
        if request.user.is_authenticated:
            if UserOrganisationFavorites.objects.filter(
                user=self.request.user, organisation=self.get_object()
            ).exists():
                instance.favourite = True

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class HotelRecommendationAPIView(APIView, CustomPageSizePagination):
    page_size = 10

    def get(self, request, *args, **kwargs):
        country = self.request.query_params.get("country")
        continent = self.request.query_params.get("continent")
        queryset = Organisation.objects.filter(
            is_deleted=False, property_status="Published", is_visible=True
        ).values(
            "photo_url",
            "location",
            "name",
            "category",
            "description",
            "safety",
            "facilities",
            "recommended",
            "safety",
            "id",
        )
        queryset = queryset.annotate(
            user_rating=Avg("rating__rating_star", filter=Q(rating__is_deleted=False)),
            min_room_price=Min("rooms__price", filter=Q(rooms__is_deleted=False)),
            category_name=F("category__name"),
        )
        organisation = pd.DataFrame(queryset)
        if country is None:
            client_ip = get_client_ip(request)
            result = get_visitor_info(client_ip, request)
            country = result.get("country") if result.get("country") else "Nepal"
        recommended_organisations = hotel_recommendor_model(
            country, organisation, continent
        )
        organisations = queryset.filter(id__in=recommended_organisations)
        if country:
            for organisation in list(organisations):
                organisation["flag"] = get_country_flag(country)
        organisations = self.paginate_queryset(organisations, self.request)
        serializer = OrganisationListInfoSerializer(organisations, many=True)
        return self.get_paginated_response(serializer.data)


class MineOrganisationListView(APIView, CustomPageSizePagination):
    """
    API View to list the my organisations
    """

    permission_classes = (IsAuthenticated,)
    page_size = 10

    def get(self, request, *args, **kwargs):
        queryset = Organisation.objects.filter(
            user=self.request.user, is_deleted=False
        ).order_by("-id")
        organisation_ids = [org.get("id") for org in queryset.values("id")]
        rooms = Room.objects.filter(
            is_deleted=False, organisation__id__in=organisation_ids
        ).annotate(
            number_of_available_rooms=F("no_of_rooms")
            - Coalesce(
                Sum(
                    "booked_room__no_of_rooms",
                    filter=Q(
                        booked_room__booking__is_deleted=False,
                        booked_room__booking__checkin_date__gte=datetime.date.today(),
                        booked_room__booking__checkout_date__gt=datetime.date.today(),
                    ),
                ),
                0,
            )
        )
        queryset = queryset.filter(is_deleted=False).prefetch_related(Prefetch("rooms"))
        page = self.paginate_queryset(queryset, self.request)
        serializer = OrganisationListInfoSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class OrganisationFetchRoomNumberAPIView(APIView):
    """
    api view to fetch the room numbers from the organisation
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        organisation_id = self.request.query_params.get("organisation")
        room_category = self.request.query_params.get("category")
        try:
            organisation = Organisation.objects.get(
                id=organisation_id, is_deleted=False, user=self.request.user
            )
        except Organisation.DoesNotExist:
            raise ValidationError(
                {
                    "error": "Either organisation with this ID doesn't exists or you are unauthorized "
                }
            )
        category = self.request.query_params.get("category")
        if category and "," in category:
            category = category.split(",")
        if Organisation.objects.filter(
            id=organisation_id, user=self.request.user, is_deleted=False
        ).exists():
            rooms = Room.objects.filter(organisation=organisation)
            if category:
                rooms = (
                    rooms.filter(category__in=category)
                    if isinstance(category, list)
                    else rooms.filter(category=category)
                )
            serializer = OrganisationFetchRoomNumberSerializer(rooms, many=True)
            return Response(serializer.data)
        raise PermissionDenied({"error": "You don't have enough permission"})


class OrganisationRoomCategoryAPIListView(APIView):
    """
    api view to list the organisation
    """

    def get(self, request, *args, **kwargs):
        organisation_id = self.request.query_params.get("property")
        if organisation_id:
            organisation = get_object_or_404(
                Organisation, id=organisation_id, is_deleted=False, is_visible=True
            )
            rooms = Room.objects.filter(organisation=organisation).values("category")
            categories = [room.get("category") for room in rooms]
            res = {"organisation": organisation.id, "room_categories": categories}
            return Response(res)
        else:
            raise ValidationError({"property": "this is required query parameter"})
