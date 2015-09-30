from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from model_utils.managers import PassThroughManager
from django.utils.translation import ugettext_lazy as _

from .popolo.behaviors import Timestampable, Dateframeable, GenericRelatable
from .popolo.querysets import RelationshipQuerySet


class Relationship(Dateframeable, Timestampable, models.Model):
    """
    A relationship between two actors
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(_("label"), max_length=512, blank=True, help_text=_("A label describing the influence"))

    # # reference to "http://popoloproject.com/schemas/person.json#"
    # influencer = models.ForeignKey('GenericRelatable', to_field="id", related_name='influencer',
    #                            help_text=_("The actor that is the influencer in the relationship"))

    # # reference to "http://popoloproject.com/schemas/organization.json#"
    # influencee = models.ForeignKey('GenericRelatable', to_field="id", related_name='influencee',
    #                            help_text=_("The actor that is the influencee in the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    links = GenericRelation('Link', help_text="URLs to documents about the relationship")

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation('Source', help_text="URLs to source documents about the relationship")

    objects = PassThroughManager.for_queryset_class(RelationshipQuerySet)()

    def __str__(self):
        return self.label
