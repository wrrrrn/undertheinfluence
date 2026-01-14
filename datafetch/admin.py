from django.contrib import admin
from django.contrib.admin.options import StackedInline
from django.contrib.contenttypes import admin as generic
from django.utils.html import format_html

from datafetch import models


class MembershipInline(admin.StackedInline):
    model = models.Membership
    fields = (
        'label', 'organization', 'role', 'on_behalf_of', 'start_date',
        'end_date')
    readonly_fields = ('organization', 'on_behalf_of',)
    extra = 0


# class InfluencedByInline(admin.StackedInline):
#     model = models.Relationship
#     verbose_name_plural = "Seeks to influence"
#     fk_name = 'influenced_by'
#     fields = ('influences', 'source',)
#     readonly_fields = ('influences', 'source',)
#     ordering = ('start_date',)
#     extra = 0


# class InfluencingInline(admin.StackedInline):
#     model = models.Relationship
#     verbose_name_plural = "Is influenced by"
#     fk_name = 'influences'
#     fields = ('influenced_by', 'source',)
#     readonly_fields = ('influenced_by', 'source',)
#     ordering = ('start_date',)
#     extra = 0


class IdentifierInline(generic.GenericTabularInline):
    model = models.Identifier
    exclude = ('identifier', 'scheme',)
    extra = 0


class OtherNameInline(generic.GenericTabularInline):
    model = models.OtherName
    fields = ('name',)
    extra = 0


class PersonAdmin(admin.ModelAdmin):
    search_fields = ('name', 'other_names__name',)
    fields = (
        'name', 'given_name', 'family_name', 'honorific_prefix', 'honorific_suffix',
        'image', 'email', 'gender', 'birth_date', 'death_date')
    inlines = [
        MembershipInline,
        OtherNameInline,
        IdentifierInline,
    ]


class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    fields = ('name', 'classification', 'founding_date', 'dissolution_date')
    inlines = [
        OtherNameInline,
        IdentifierInline,
    ]

class ActorResolutionAdmin(admin.ModelAdmin):
    """Admin interface for reviewing and managing entity resolution."""

    list_display = (
        'colored_decision_badge',
        'actor1_display',
        'actor2_display',
        'confidence',
        'match_reason',
        'review_status',
        'created_at',
    )

    list_filter = (
        'review_status',
        'decision',
        'match_reason',
        'created_at',
    )

    search_fields = (
        'actor1__name',
        'actor2__name',
        'notes',
    )

    readonly_fields = (
        'actor1',
        'actor2',
        'confidence',
        'decision',
        'match_reason',
        'created_at',
        'updated_at',
        'reviewed_at',
        'reviewed_by',
    )

    fieldsets = (
        ('Potential Duplicate Actors', {
            'fields': ('actor1', 'actor2', 'canonical_actor')
        }),
        ('Match Details', {
            'fields': ('confidence', 'decision', 'match_reason')
        }),
        ('Review', {
            'fields': ('review_status', 'notes')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'reviewed_at', 'reviewed_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_resolutions', 'reject_resolutions']

    def colored_decision_badge(self, obj):
        """Display decision with color-coded badge."""
        colors = {
            'auto_merge': '#28a745',  # Green
            'review': '#ffc107',      # Yellow
            'suggest': '#17a2b8',     # Blue
            'ignore': '#6c757d',      # Gray
        }
        color = colors.get(obj.decision, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_decision_display()
        )
    colored_decision_badge.short_description = 'Decision'

    def actor1_display(self, obj):
        """Display actor1 with type badge."""
        actor_type = obj.actor1.__class__.__name__
        return format_html(
            '<strong>{}</strong><br><span style="color: #666; font-size: 11px;">{} (ID: {})</span>',
            obj.actor1.name,
            actor_type,
            obj.actor1.id
        )
    actor1_display.short_description = 'Actor 1'

    def actor2_display(self, obj):
        """Display actor2 with type badge."""
        actor_type = obj.actor2.__class__.__name__
        return format_html(
            '<strong>{}</strong><br><span style="color: #666; font-size: 11px;">{} (ID: {})</span>',
            obj.actor2.name,
            actor_type,
            obj.actor2.id
        )
    actor2_display.short_description = 'Actor 2'

    def approve_resolutions(self, request, queryset):
        """Approve selected resolutions (bulk action)."""
        pending = queryset.filter(review_status='pending')
        count = 0

        for resolution in pending:
            resolution.approve(user=request.user, notes="Bulk approved via admin")
            count += 1

        self.message_user(
            request,
            f"Successfully approved {count} resolution(s).",
            level='success'
        )
    approve_resolutions.short_description = "✓ Approve selected resolutions"

    def reject_resolutions(self, request, queryset):
        """Reject selected resolutions (bulk action)."""
        pending = queryset.filter(review_status='pending')
        count = 0

        for resolution in pending:
            resolution.reject(user=request.user, notes="Bulk rejected via admin")
            count += 1

        self.message_user(
            request,
            f"Successfully rejected {count} resolution(s).",
            level='warning'
        )
    reject_resolutions.short_description = "✗ Reject selected resolutions"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('actor1', 'actor2', 'canonical_actor', 'reviewed_by')


admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.ActorResolution, ActorResolutionAdmin)
