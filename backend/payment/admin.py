from django.contrib import admin
from .models import PaymentMethod, GST, SetRate, KhaltiTransactionDetail
# Register your models here.
admin.site.register(PaymentMethod)
admin.site.register(GST)
admin.site.register(SetRate)
admin.site.register(KhaltiTransactionDetail)