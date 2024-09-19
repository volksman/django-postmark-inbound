import django.dispatch

inbound_mail_received = django.dispatch.Signal("mail_data", "mail_object")
inbound_mail_filtered = django.dispatch.Signal("mail_data")
