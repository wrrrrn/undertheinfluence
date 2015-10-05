from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from model_utils.managers import PassThroughManager
from django.utils.translation import ugettext_lazy as _

from .popolo.behaviors import Timestampable, Dateframeable, GenericRelatable
# from .popolo.querysets import DateframeableQuerySet
from datafetch.models import models as popolo_models


# class RelationshipQuerySet(DateframeableQuerySet):
#     pass

class Relationship(Dateframeable, Timestampable, models.Model):
    """
    A relationship between two actors
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(_("label"), max_length=512, blank=True, help_text=_("A label describing the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    links = GenericRelation('Link', help_text="URLs to documents about the relationship")

    source = models.URLField(_("source"), blank=True, null=True, help_text=_("URL to the source that documents the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/identifier.json#"
    identifiers = GenericRelation('Identifier', help_text="Issued identifiers")

    # objects = PassThroughManager.for_queryset_class(RelationshipQuerySet)()

    class Meta:
        abstract = True

    def __str__(self):
        return self.label


class Consultancy(Relationship):
    client = models.ForeignKey(popolo_models.Actor, related_name='consultants', null=True)
    agency = models.ForeignKey(popolo_models.Actor, related_name='consults_for', null=True)


class Donation(Relationship):
    CATEGORY_CHOICES = (
        "Non Cash",
        "Cash",
        "Impermissible Donor",
        "Visit",
        "Public Funds",
        "Exempt Trust",
        "Permissible Donor Exempt Trust",
        "Total value of donations not reported individually",
        "Unidentified Donor",
    )
    NATURE_CHOICES = (
        "Travel",
        "Sponsorship",
        "Auction prizes",
        "Administration services",
        "Other",
        "Premises",
        "Consultancy services",
        "Staff costs",
        "Advertising",
        "Hospitality",
        "Loan conversion",
        "Short Money (House of Commons)",
        "Designated Organisation (Referendum)",
        "Assistance for Parties (Scottish Parliament)",
        "Policy Development Grant",
        "Cranborne Money (House of Lords)",
        "Other Payment",
        "Start Up Grant (Discontinued)",
    )

    donor = models.ForeignKey(popolo_models.Actor, related_name='donated_to', null=True)
    recipient = models.ForeignKey(popolo_models.Actor, related_name='received_donations_from', null=True)

    value = models.DecimalField(_("value"), blank=True, max_digits=12, decimal_places=2, help_text=_("The monetary value of the donation"))
    donation_type = models.CharField(_("donation type"), max_length=128, help_text=_("The type of donation e.g. cash"))
    nature_of_donation = models.CharField(_("nature of donation"), max_length=128, blank=True, help_text=_("The nature of the donation e.g. hospitality"))
    received_date = models.DateField(_("received date"), null=True, blank=True)
    accepted_date = models.DateField(_("accepted date"), null=True, blank=True)
    reported_date = models.DateField(_("reported date"), null=True, blank=True)
    accounting_unit_name = models.CharField(_("accounting unit name"), max_length=128, blank=True)
    accounting_units_as_central_party = models.BooleanField(_("accounting units as central party"))
    purpose_of_visit = models.CharField(_("purpose of visit"), max_length=512, blank=True)
    is_bequest = models.BooleanField(_("is bequest"))
    is_aggregation = models.BooleanField(_("is aggregation"))
    is_sponsorship = models.BooleanField(_("is sponsorship"))

    def start_date(self):
        return self.accepted_date

    def __str__(self):
        if self.donation_type == "Cash":
            return "Donation of £{:,d}".format(int(self.value))
        if self.donation_type == "Visit":
            return "Donation of £{:,d} (Visit to {})".format(int(self.value), self.purpose_of_visit)
        if self.donation_type == "Non Cash":
            return "Donation of £{:,d} ({})".format(int(self.value), self.nature_of_donation)


class Note(Timestampable, GenericRelatable, models.Model):
    content = models.TextField(_("content"), blank=True, help_text=_("A note about this person or organization"))
