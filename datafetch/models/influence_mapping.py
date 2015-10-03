from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from model_utils.managers import PassThroughManager
from django.utils.translation import ugettext_lazy as _
from polymorphic import PolymorphicModel

from .popolo.behaviors import Timestampable, Dateframeable, GenericRelatable
# from .popolo.querysets import DateframeableQuerySet
from datafetch.models import Actor


# class RelationshipQuerySet(DateframeableQuerySet):
#     pass


class Relationship(PolymorphicModel, Dateframeable, Timestampable):
    """
    A relationship between two actors
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(_("label"), max_length=512, blank=True, help_text=_("A label describing the relationship"))

    influenced_by = models.ForeignKey(Actor, related_name='influenced_by', null=True)
    influences = models.ForeignKey(Actor, related_name='influences', null=True)

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    links = GenericRelation('Link', help_text="URLs to documents about the relationship")

    source = models.URLField(_("source"), blank=True, null=True, help_text=_("URL to the source that documents the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/identifier.json#"
    identifiers = GenericRelation('Identifier', help_text="Issued identifiers")

    # objects = PassThroughManager.for_queryset_class(RelationshipQuerySet)()

    def __str__(self):
        return self.label


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
    value = models.DecimalField(_("value"), blank=True, max_digits=12, decimal_places=2, help_text=_("The monetary value of the donation"))
    category = models.CharField(_("category"), max_length=512, help_text=_("The category of the donation e.g. cash"))
    nature = models.CharField(_("nature"), max_length=512, blank=True, help_text=_("The nature of the donation e.g. hospitality"))
    accepted_date = models.CharField(_("accepted date"), max_length=10, help_text=_("The date the donation was accepted"))

    def start_date(self):
        return self.accepted_date

    def __str__(self):
        return "Donation of £{:,d} ({}, {})".format(int(self.value), self.category, self.nature)


class Note(Timestampable, GenericRelatable, models.Model):
    content = models.TextField(_("content"), blank=True, help_text=_("A note about this person or organization"))
