from django.db import models
from organisation.models import Organisation, Room
from booking.models import Booking, BookingDetail
from users.models import User
from package.models import PackageBooking

# Create your models here.


class PaymentMethod(models.Model):
    """
    model to store payment information of users and hotliers
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="User to whom payment method belong to",
    )
    method = models.CharField(
        max_length=20,
        choices=(
            ("Cash", "Cash"),
            ("Card", "Card"),
            ("Bank Transfer", "Bank Transfer"),
        ),
        help_text="Type of payment method cash card or bank transfer",
    )
    number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Bank account number or card number or phone number",
    )
    name = models.CharField(
        null=True, blank=True, max_length=100, help_text="Name of person"
    )
    expiry = models.CharField(
        null=True, blank=True, max_length=10, help_text="Expiry date of card"
    )
    cvv = models.CharField(
        null=True, blank=True, max_length=10, help_text="CVV of card"
    )
    bank_name = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        help_text="Card or bank account issuing bank",
    )
    address = models.CharField(
        null=True,
        blank=True,
        max_length=200,
        help_text="Address of person to collect cash or bank",
    )
    iban_number = models.CharField(
        null=True, blank=True, max_length=34, help_text="IBAN number for bank transfer"
    )
    account_type = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        help_text="Type of bank account saving or current?",
    )
    bsb = models.CharField(
        null=True, blank=True, max_length=6, help_text="BSB Code of bank"
    )
    swift_code = models.CharField(
        null=True, blank=True, max_length=11, help_text="Swift code of bank"
    )
    is_active = models.BooleanField(
        blank=True,
        default=False,
        help_text="Is this the default payment method you want to use for transaction?",
    )

    def __str__(self):
        return f"{self.user.email, self.method}"


class SetRate(models.Model):
    """
    model to store variable dates
    """

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        help_text="Room type to set price for",
        related_name="setrate",
    )
    from_date = models.DateTimeField(help_text="Set price from this date")
    to_date = models.DateTimeField(help_text="Set price upto one day before this date")
    price = models.IntegerField(help_text="Price to set.")


class GST(models.Model):
    """
    model to have gst informations based on countries
    """

    country = models.CharField(
        max_length=100, help_text="Country to which GST belong to"
    )
    gst_percentage = models.IntegerField(
        default=0, help_text="Percentage of GST applicable in country"
    )
    cgst_percentage = models.IntegerField(
        default=0, help_text="Percentage of CGST applicable in country"
    )
    sgst_percentage = models.IntegerField(
        default=0, help_text="Percentage of SGST applicable in country"
    )

    def __str__(self):
        return self.country


PAYMENT_STATUS = (("success", "Success"), ("failure", "Failure"))


class KhaltiTransactionDetail(models.Model):

    token = models.CharField(max_length=30)
    payment_status = models.CharField(choices=PAYMENT_STATUS, max_length=20)
    booking_id = models.ForeignKey(Booking, related_name="khalti_booking_payment", on_delete=models.CASCADE,null=True,blank=True)
    packagebooking_id = models.ForeignKey(PackageBooking,related_name="khalti_packagebooking_payment", on_delete=models.CASCADE,null=True,blank=True)
    amount = models.FloatField()
    payment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.token

    class Meta:
        db_table = "khalti_transaction_detail"
        ordering = ["-payment_date"]


class EsewaTransactionDetail(models.Model):
    token = models.CharField(max_length=30)
    payment_status = models.CharField(choices=PAYMENT_STATUS, max_length=20)
    booking_id = models.ForeignKey(
        Booking,
        related_name="esewa_transaction",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    package_booking_id = models.ForeignKey(
        PackageBooking,
        related_name="esewa_transaction",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.FloatField()
    payment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.token

    class Meta:
        db_table = "esewa_transaction_detail"
        ordering = ["-payment_date"]
