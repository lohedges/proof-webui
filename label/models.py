from django.db import models
from django_mysql.models import ListTextField

class Micrograph(models.Model):
    path = models.CharField(
            max_length = 100,
            help_text = "The path to the micrograph image."
            )
    ip_addresses = ListTextField(
                base_field = models.CharField(max_length=39),
                help_text = "A list of IP addresses that have uploaded labels "
                           "for this micrograph."
                )
    num_labels = models.IntegerField(
            default = 0,
            help_text = "The number of uploaded labels for this micrograph."
            )
