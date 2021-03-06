from concurrency.fields import IntegerVersionField
from django.db import models
from django_mysql.models import ListTextField

class Micrograph(models.Model):
    version = IntegerVersionField(
            help_text = "A version identifier to avoid concurrent edits.",
            )
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
    average = models.BinaryField(
            default = b"",
            help_text = "The average of the micrograph labels."
            )
    variance = models.FloatField(
            default = 0.0,
            help_text = "The variance in the labelling for this micrograph."
            )
