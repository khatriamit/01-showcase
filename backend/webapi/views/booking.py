from numpy import inf
from checkin.serializers import CheckInCheckOutInformationSerialzer
from webapi.utils.booking import get_booked_rooms, get_room_unavailability
from webapi.serializers.booking import UpdateBookingCheckoutSerializer
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import (
    UpdateAPIView,
    get_object_or_404,
    RetrieveUpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from booking.serializers import UserBookingSerializer, UserBookingUpdateSerializer
from booking.domain.model import RoomDetail, booking_factory
from organisation.models import OrganisationRoomUnavailability, Room
from booking.models import Booking, BookingDetail
from booking.helpers import get_booking_price_detail
from datetime import date, datetime
from webapi.views.abstract.validation import UserInfo, CustomRequest
from webapi.utils.helpers import validate_booking
from webapi.utils.booking import get_detail_booking_pricing
from backend.utils import convert_str_to_date
from booking.util.update_booking import update_booking
from checkin.models import CheckInCheckOutInformation
from booking.helpers import get_dates
import json


class UpdateBookingAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserBookingSerializer

    def get_object(self):
        booking = get_object_or_404(
            Booking,
            id=self.kwargs.get("id"),
            is_deleted=False,
            cancelled=False,
            property__user=self.request.user,
        )
        return booking

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        booking_price_info = get_booking_price_detail(self.request)
        request.data.update(
            {
                "total_amount": booking_price_info.get("total"),
                "gst_amount": booking_price_info.get("gst_amount"),
            }
        )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        rooms = self.request.data.get("room_detail")
        checkin_date = datetime.strptime(
            request.data.get(
                "checkin_date", instance.checkin_date.strftime("%Y-%m-%d")
            ),
            "%Y-%m-%d",
        ).date()
        checkout_date = datetime.strptime(
            request.data.get(
                "checkout_date", instance.checkout_date.strftime("%Y-%m-%d")
            ),
            "%Y-%m-%d",
        ).date()
        booked_rooms = get_booked_rooms(checkin_date, checkout_date, instance=instance)
        booking_unavailability = OrganisationRoomUnavailability.objects.filter(
            Q(from_date__gte=checkin_date, to_date__lte=checkout_date)
            | Q(from_date__lte=checkin_date, to_date__gte=checkin_date)
            | Q(from_date__lte=checkout_date, to_date__gte=checkout_date),
            organisation=instance.property,
            is_deleted=False,
        ).values("id", "room_type", "room_numbers")
        room_id_to_book = [room.get("room") for room in rooms]
        rooms = Room.objects.filter(
            id__in=room_id_to_book, organisation=instance.property
        ).values("id", "category", "children_accomodate", "accomodates", "no_of_rooms")
        try:
            booking_factory(
                **request.data,
                unavailable_rooms=list(booking_unavailability),
                booked_rooms=list(booked_rooms),
                rooms=list(rooms)
            )
        except Exception as e:
            raise ValidationError({"error": e})

        self.perform_update(serializer)
        res = {"booking_detail": serializer.data}
        res.update(booking_price_info)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(res)


class UpdateBookingUserInfo(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_booking(booking_id, self.request.user)
        return Response(booking.user_info)

    def put(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_booking(booking_id, self.request.user)
        try:
            user_info = UserInfo(**request.data)
        except Exception as e:
            raise ValidationError({"error": json.loads(e.json())})
        booking.user_info = request.data
        booking.save()
        return Response(booking.user_info)


class UpdateBookingDetailView(APIView):
    """
    APIView to update the booking checkin, checkout and Room detail
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_booking(booking_id, self.request.user)

        serializer = UserBookingUpdateSerializer(booking)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_booking(booking_id, self.request.user)
        request.data.update(
            {
                "user_info": booking.user_info,
                "property": booking.property.id,
                "discount_code": booking.discount_code,
            }
        )

        serializer = UserBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checkin_date = convert_str_to_date(serializer.data.get("checkin_date"))
        checkout_date = convert_str_to_date(serializer.data.get("checkout_date"))
        room_id_to_book = [room.get("room") for room in request.data.get("room_detail")]
        rooms = Room.objects.filter(
            id__in=room_id_to_book, organisation=booking.property
        ).values(
            "id",
            "category",
            "children_accomodate",
            "accomodates",
            "no_of_rooms",
            "price",
        )
        booked_rooms = get_booked_rooms(checkin_date, checkout_date, instance=booking)
        booking_unavailability = get_room_unavailability(
            checkin_date, checkout_date, booking
        )
        try:
            booking_model = booking_factory(
                **request.data,
                unavailable_rooms=list(booking_unavailability),
                booked_rooms=list(booked_rooms),
                rooms=list(rooms)
            )
            booking_price_info = get_booking_price_detail(request)
            booking = update_booking(
                booking_model,
                booking_id,
                booking_price_info.get("total"),
                booking_price_info.get("gst_amount"),
            )
        except Exception as e:
            raise ValidationError({"error": e})
        serializer = UserBookingUpdateSerializer(booking)
        return Response(serializer.data)


class GetBookingPriceDetail(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_booking(booking_id, self.request.user)
        request.data.update(
            {
                "user_info": booking.user_info,
                "property": booking.property.id,
                "discount_code": booking.discount_code,
            }
        )
        serializer = UserBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking_price_info = get_booking_price_detail(
            request,
            additional_discount=serializer.validated_data.get("additional_discount"),
        )
        paid_amount = booking.paid_amount

        booking_price_info.update(
            {
                "paid_amount": paid_amount,
                "additional_discount": serializer.validated_data.get(
                    "additional_discount"
                ),
            }
        )
        booking_price_info = get_detail_booking_pricing(booking_price_info, booking)

        return Response(booking_price_info)


class UpdateBookingCheckoutView(APIView):
    """API View to update the booking checkout date"""

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        checkin_id = self.kwargs.get("id")
        checkin = get_object_or_404(
            CheckInCheckOutInformation,
            id=checkin_id,
            booking__property__user=self.request.user,
        )
        serializer = UpdateBookingCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking_room_detail = BookingDetail.objects.filter(
            booking=checkin.booking
        ).values("room__id", "no_of_rooms", "no_of_children", "no_of_adults")
        room_detail = []
        for detail in list(booking_room_detail):
            room_detail.append(
                {
                    "room": detail.get("room__id"),
                    "no_of_rooms": detail.get("no_of_rooms"),
                    "no_of_children": detail.get("no_of_children"),
                    "no_of_adults": detail.get("no_of_adults"),
                }
            )

        if (
            serializer.validated_data.get("checkout_date")
            == checkin.booking.checkin_date
        ) or serializer.validated_data.get(
            "checkout_date"
        ) < checkin.booking.checkin_date:
            raise ValidationError(
                {
                    "checkout_date": "checkout date does not accept the date that is equals to or less than checkin date"
                }
            )

        if (
            serializer.validated_data.get("checkout_date")
            < checkin.booking.checkout_date
        ):
            checkin.updated_checkout_date = serializer.validated_data.get(
                "checkout_date"
            )
            checkin.save()

        elif (
            serializer.validated_data.get("checkout_date")
            == checkin.booking.checkout_date
        ):
            checkin.updated_checkout_date = None
            checkin.save()
        else:
            booked_rooms = get_booked_rooms(
                checkin.booking.checkout_date,
                serializer.validated_data.get("checkout_date"),
                instance=checkin.booking,
            )
            booking_unavailability = get_room_unavailability(
                checkin.booking.checkout_date,
                serializer.validated_data.get("checkout_date"),
                checkin.booking,
            )
            data = {
                "property": checkin.booking.property.id,
                "checkin_date": checkin.booking.checkout_date,
                "checkout_date": serializer.validated_data.get("checkout_date"),
                "user_info": checkin.booking.user_info,
                "room_detail": room_detail,
            }
            room_id_to_book = [room.get("room") for room in room_detail]
            rooms = Room.objects.filter(
                id__in=room_id_to_book, organisation=checkin.booking.property
            ).values(
                "id",
                "category",
                "children_accomodate",
                "accomodates",
                "no_of_rooms",
                "room_numbers",
                "price",
            )
            try:
                booking_factory(
                    **data,
                    unavailable_rooms=list(booking_unavailability),
                    booked_rooms=list(booked_rooms),
                    rooms=list(rooms)
                )
                checkin.updated_checkout_date = serializer.validated_data.get(
                    "checkout_date"
                )
                checkin.save()

            except Exception as e:
                raise ValidationError({"error": e})
        serializer = CheckInCheckOutInformationSerialzer(checkin)
        return Response(serializer.data)


class GetUpdatedCheckoutPricing(APIView):
    """fetching the room checkout price after updating"""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        checkin_id = self.kwargs.get("id")
        checkin = get_object_or_404(
            CheckInCheckOutInformation,
            id=checkin_id,
            booking__property__user=self.request.user,
            checkin_status="Ci",
        )
        booking_room_detail = BookingDetail.objects.filter(
            booking=checkin.booking
        ).values("room__id", "no_of_rooms", "no_of_children", "no_of_adults")
        room_detail = []
        for detail in list(booking_room_detail):
            room_detail.append(
                {
                    "room": detail.get("room__id"),
                    "no_of_rooms": detail.get("no_of_rooms"),
                    "no_of_children": detail.get("no_of_children"),
                    "no_of_adults": detail.get("no_of_adults"),
                }
            )

        if checkin.updated_checkout_date:
            if checkin.booking.checkout_date < checkin.updated_checkout_date.date():
                request_ = CustomRequest(
                    data={
                        "property": checkin.booking.property.id,
                        "checkin_date": datetime.strftime(
                            checkin.booking.checkout_date, "%Y-%m-%d"
                        ),
                        "checkout_date": datetime.strftime(
                            checkin.updated_checkout_date, "%Y-%m-%d"
                        ),
                        "room_detail": room_detail,
                    }
                )
                response_ = get_booking_price_detail(request_)
                response_.pop("fees_tax")
                response_.pop("booked_rooms")
                return Response(response_)

            elif checkin.booking.checkout_date > checkin.updated_checkout_date.date():
                print(checkin.booking.checkout_date)
                print(checkin.updated_checkout_date.date())
                request_ = CustomRequest(
                    data={
                        "property": checkin.booking.property.id,
                        "checkin_date": datetime.strftime(
                            checkin.updated_checkout_date, "%Y-%m-%d"
                        ),
                        "checkout_date": datetime.strftime(
                            checkin.booking.checkout_date, "%Y-%m-%d"
                        ),
                        "room_detail": room_detail,
                    }
                )
                response_ = get_booking_price_detail(request_)
                response_.pop("fees_tax")
                response_.pop("booked_rooms")
                total_refund_amount = 0
                for info in response_.get("more_info"):
                    info["refund_amount"] = info["total"]
                    total_refund_amount += info["total"]
                    info.pop("total")
                response_.pop("sub_total")
                response_.pop("gst_percentage")
                response_.pop("gst_amount")
                response_.pop("special_deal_discount_amount")
                response_.pop("total")
                response_.update({"total_refund_amount": total_refund_amount})
                return Response(response_)
        else:
            request_ = CustomRequest(
                data={
                    "property": checkin.booking.property.id,
                    "checkin_date": datetime.strftime(
                        checkin.booking.checkin_date, "%Y-%m-%d"
                    ),
                    "checkout_date": datetime.strftime(
                        checkin.booking.checkout_date, "%Y-%m-%d"
                    ),
                    "room_detail": room_detail,
                }
            )
            response_ = get_booking_price_detail(request_)
            response_.pop("fees_tax")
            response_.pop("booked_rooms")
            return Response(response_)


class CancelBooking(APIView):
    """API to cancel the user booking by hotel owner"""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.request.query_params.get("booking_id")
        booking = get_object_or_404(
            Booking,
            Q(checkin_checkout_information=None)
            | Q(checkin_checkout_information__checkin_status="B"),
            ~Q(payment_status="Draft"),
            id=booking_id,
            is_deleted=False,
            cancelled=False,
            property__user=self.request.user,
        )
        booking.cancelled = True
        booking.save()
        serializer = UserBookingSerializer(booking)
        return Response(serializer.data)
