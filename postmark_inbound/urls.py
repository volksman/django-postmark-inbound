from django.urls import path

from .views import InboundMailWebhook


urlpatterns = [
    path('inbound/', InboundMailWebhook.as_view(), name='inbound-webhook')
]
