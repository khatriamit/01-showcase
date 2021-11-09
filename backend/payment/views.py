from django.db import transaction
from django.shortcuts import render
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
import requests
import json
from rest_framework.response import Response
from booking.models import Booking
from booking.serializers import BookingInvoiceSerializer, UserBookingSerializer
from .models import PaymentMethod, SetRate, GST, KhaltiTransactionDetail
from .serializers import PaymentMethodSerializer, SetRateSerializer
from organisation.models import Organisation, Room
from booking.models import Booking, BookingDetail
from django.db.models import Sum
from users.models import UserReferStat


# Create your views here.

    
class VerifyKhaltiPayment(APIView):
    """
    api for khalti payment verification
    :parameter
    token
    amount
    bookingID
    paymentProcessor
    """

    def khalti_verification(self, token, amount, booking_id, payment_processor):
        payload = {
            "token": token,
            "amount": amount,
        }
        headers = {
            "Authorization": "Key {}".format(settings.KHALTI_SECRET_KEY)
        }
        try:
            booking = Booking.objects.get(id=booking_id)
            if amount < float(booking.total_amount) * 0.10:
                raise ValidationError({"amount": "you must pay minimum 10% to confirm booking"})
            try:
                response = requests.post(settings.KHALTI_VERIFY_URL, payload, headers=headers)
                if response.status_code == 200:
                    booking.khalti_payment_status = "success"
                    booking.payment_status = "Paid"
                    booking.payment_method = payment_processor
                    booking.paid_amount = amount
                    booking.save()
                    KhaltiTransactionDetail.objects.create(
                        token=token,
                        payment_status="success",
                        booking_id=booking,
                        amount=amount
                    )
                    serializer = UserBookingSerializer(booking)
                    return {"status": 200, "detail": serializer.data}

                else:
                    booking.khalti_payment_status = "failure"
                    booking.save()
                    KhaltiTransactionDetail.objects.create(
                        token=token,
                        payment_status="failure",
                        booking_id=booking,
                        amount=amount
                    )
                    return {"status": 401, "detail": response.json()}

            except requests.exceptions.HTTPError as e:
                booking.status = "failed verification"
                booking.save()
                return Response({
                    'status': False,
                    'detail': 'unable to send payment verification request to khalti',
                })
        except Booking.DoesNotExist:
            return Response({
                'status': False,
                'details': "Unable to verify payment.Booking not available."
            })

    def esewa_verification(self, token, amount, booking_id):
        payload = {
            'amt': amount,
            'scd': settings.ESEWA_SCD,
            'rid': token,
            'pid': booking_id,
        }
        try:
            booking = Booking.objects.get(id=booking_id)
            try:
                response = requests.post(settings.ESEWA_VERIFY_URL, payload)
                if response.text.__contains__('Success'):
                    booking.status = "success"
                    booking.save()
                    return {"status": 200, "detail": response.text}

                else:
                    booking.status = "failed"
                    booking.save()
                    return {"status": 200, "detail": response.text}

            except requests.exceptions.HTTPError as e:
                booking.status = "failed verification"
                booking.save()
                return Response({
                    'status': False,
                    'detail': 'unable to send payment verification request to esewa',
                })
        except Booking.DoesNotExist:
            return {"status": 400, "detail": "booking id doesn't exists"}

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        token = request.data.get('token', False)
        amount = request.data.get('amount', False)
        booking_id = request.data.get('booking_id', False)
        payment_processor = request.data.get('payment_processor', False)
        if payment_processor == 'Khalti':
            res = self.khalti_verification(token, amount, booking_id, payment_processor)
            if res.get('status') == 200:
                return Response({"detail": res.get('detail')}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": res.get('detail')}, status=status.HTTP_400_BAD_REQUEST)
                
        elif payment_processor == 'eSewa':
            if not token:
                raise ValidationError({"error": "A unique payment reference code from eSewa "
                                                "generated on SUCCESSFUL transaction is missing"})
            if not amount:
                raise ValidationError({"error": "Total payment amount of product or service is missing"})

            if not booking_id:
                raise ValidationError({"error": "A unique ID of product or item or ticket etc "
                                                "generated by merchant for payment is missing"})
            res = self.esewa_verification(token, amount, booking_id)
            if res.get('status_code') == 200:
                return Response({"detail": res.get("detail")}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": res.get("detail")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'status': False,
                'detail': "Choose a valid payment processor"
            })
        return Response({
            'Server Error'
        })


class PaymentMethodViewset(viewsets.ModelViewSet):
    """
    api for crud payment method
    """
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [filters.SearchFilter]
    search_fields = ['=user__id', ]


class SetRateViewSet(viewsets.ModelViewSet):
    """
    api for setting rate
    """
    queryset = SetRate.objects.none()
    serializer_class = SetRateSerializer
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):
        org = self.request.query_params.get('propertyID')
        if org:
            return SetRate.objects.filter(room__organisation__id=org)
        else:
            return SetRate.objects.none()


class InvoiceView(APIView):
    """
    api for generating invoice
    :param
    bookingID
    redeemPoint
    discount
    """

    def get(self, request, *args, **kwargs):
        booking = self.request.query_params.get('bookingID', False)
        redeem_point = self.request.query_params.get('redeemPoint', False)
        discount = self.request.query_params.get('discount', False)
        try:
            booking_object = Booking.objects.get(id=booking)
            booking_user = booking_object.booked_by
            available_points = 0
            property = booking_object.property
            no_of_days = booking_object.reserved_days
            country = property.location['country']
            booking_detail = BookingDetail.objects.filter(booking=booking_object)
            room_charge = booking_detail.aggregate(charge=Sum('room__price'))
            total_room_charge = room_charge['charge'] * no_of_days
            try:
                gst_object = GST.objects.get(country=country)
                gst_percentage = gst_object.gst_percentage
                cgst_percentage = gst_object.cgst_percentage
                sgst_percentage = gst_object.sgst_percentage
                gst_amount = total_room_charge * gst_percentage / 100
            except GST.DoesNotExist:
                gst_percentage = 0
                cgst_percentage = 0
                sgst_percentage = 0
                gst_amount = 0
            paid = booking_object.paid_amount
            including_gst = total_room_charge + gst_amount
            if not redeem_point:
                redeemed_points = 0
            else:
                redeemed_points = int(redeem_point)
                try:
                    refer_stat = UserReferStat.objects.get(user=booking_user)
                    available_points = refer_stat.total_earning
                    if refer_stat.total_earning < redeemed_points:
                        return Response({
                            'status': False,
                            'detail': 'Not Sufficient Points to redeem'
                        })
                    else:
                        refer_stat.total_earning = refer_stat.total_earning - redeemed_points
                        refer_stat.save()
                except UserReferStat.DoesNotExist:
                    return Response({
                        'status': False,
                        'detail': 'You have no any referrals'
                    })
            refer_point_amount = redeemed_points / 100
            if not discount:
                discount_percent = 0
            else:
                discount_percent = int(discount)
            total_amount = including_gst - paid - refer_point_amount
            discount_amount = total_amount * (discount_percent / 100)
            total_amount = total_amount - discount_amount
            booking = BookingInvoiceSerializer(booking_detail, many=True).data
            return Response({
                'status': True,
                'detail': {
                    'subTotal': total_room_charge,
                    'advance': paid,
                    'gstRate': gst_percentage,
                    'cgstRate': cgst_percentage,
                    'sgstRate': sgst_percentage,
                    'gstAmount': gst_amount,
                    'total': including_gst,
                    'availablePoints': available_points,
                    'redeemedPoints': redeemed_points,
                    'redemmedAmount': refer_point_amount,
                    'discount': discount_percent,
                    'discountAmount': discount_amount,
                    'totalAmount': total_amount,
                    'booking': booking
                }
            })
        except Booking.DoesNotExist:
            return Response({
                'status': False,
                'detail': 'Booking Doesnot Exist'
            })