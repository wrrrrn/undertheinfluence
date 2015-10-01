from django.contrib import admin
from django.contrib.admin.options import StackedInline
from django.contrib.contenttypes import admin as generic

from datafetch import models


class MembershipInline(admin.StackedInline):
    model = models.Membership
    fields = (
        'label', 'organization', 'role', 'on_behalf_of', 'start_date',
        'end_date')
    extra = 0


class IdentifierInline(generic.GenericTabularInline):
    model = models.Identifier
    exclude = ('identifier', 'scheme',)
    extra = 0


class OtherNameInline(generic.GenericTabularInline):
    model = models.OtherName
    fields = (
        'name',)
    extra = 0


class PersonAdmin(admin.ModelAdmin):
    search_fields = ('other_names__name',)
    fields = (
        'name', 'given_name', 'family_name', 'honorific_prefix', 'honorific_suffix',
        'image', 'email', 'gender', 'birth_date', 'death_date')
    inlines = [
        OtherNameInline,
        IdentifierInline,
        MembershipInline,
    ]


class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    fields = ('name', 'classification', 'founding_date', 'dissolution_date')
    inlines = [
        OtherNameInline,
        IdentifierInline,
    ]

admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Organization, OrganizationAdmin)
