from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from model_utils.managers import PassThroughManager
from django.utils.translation import ugettext_lazy as _
from polymorphic import PolymorphicModel

from .popolo.behaviors import Timestampable, Dateframeable, GenericRelatable
from .popolo.querysets import DateframeableQuerySet
from datafetch.models import Actor


class RelationshipQuerySet(DateframeableQuerySet):
    pass

class Relationship(Dateframeable, Timestampable, PolymorphicModel):
    """
    A relationship between two actors
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(_("label"), max_length=512, blank=True, help_text=_("A label describing the influence"))

    influenced_by = models.ForeignKey(Actor, related_name='influenced_by', null=True)
    influences = models.ForeignKey(Actor, related_name='influences', null=True)

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    links = GenericRelation('Link', help_text="URLs to documents about the relationship")

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation('Source', help_text="URLs to source documents about the relationship")

    # array of items referencing "http://popoloproject.com/schemas/identifier.json#"
    identifiers = GenericRelation('Identifier', help_text="Issued identifiers")

    objects = PassThroughManager.for_queryset_class(RelationshipQuerySet)()

    def __str__(self):
        return self.label


class Note(Timestampable, GenericRelatable, models.Model):
    content = models.TextField(_("content"), blank=True, help_text=_("A note about this person or organization"))
