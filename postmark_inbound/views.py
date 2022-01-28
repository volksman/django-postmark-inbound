from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils.module_loading import import_string

from .serializers import InboundMailSerializer
from .parsers import PostmarkJSONParser
from .signals import inbound_mail_received, inbound_mail_filtered
from .settings import inbound_mail_options as option


class PostmarkPermission(permissions.BasePermission):
    """
    Basic permission to whitelist IPs used by Postmark's inbound web hooks.
    """
    postmark_inbound_ip = option.IP_WHITE_LIST

    def has_permission(self, request, view):
        print("Checking postmark IP")
        ip_forward = request.META.get('HTTP_X_FORWARDED_FOR')
        print("ip_forward: ", ip_forward)
        if ip_forward:
            remote_addr = ip_forward.split(",")[-1]
        else:
            remote_addr = (request.META.get('HTTP_X_REAL_IP') or
                        request.META.get('REMOTE_ADDR'))
        return remote_addr in self.postmark_inbound_ip


class InboundMailWebhook(APIView):
    """
    API endpoint that allows inbound mail from Postmark to be received and
    saved to the database.
    """
    serializer_class = InboundMailSerializer
    permission_classes = (PostmarkPermission,)
    parser_classes = (PostmarkJSONParser,)

    def post(self, request, format=None):
        serializer = InboundMailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mail_data = serializer.validated_data
        if option.SAVE_FILTER and not import_string(option.SAVE_FILTER)(mail_data):
            inbound_mail_filtered.send_robust(
                sender=self.__class__,
                mail_data=mail_data,
            )
            success_msg = {'detail': 'Inbound mail received but filtered. Thanks Postmark!'}
            return Response(success_msg, status=status.HTTP_202_ACCEPTED)

        mail_object = serializer.save() if option.SAVE_MAIL_TO_DB else None

        # Send signal notifying that a new inbound mail has been received
        inbound_mail_received.send_robust(sender=self.__class__,
                                          mail_data=mail_data,
                                          mail_object=mail_object)

        success_msg = {'detail': 'Inbound mail received. Thanks Postmark!'}
        return Response(success_msg, status=status.HTTP_202_ACCEPTED)
