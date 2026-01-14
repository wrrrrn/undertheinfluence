from django.db import models
from django.contrib.auth.models import User

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.images.blocks import ImageChooserBlock


class MyPage(Page):
    class Meta:
        verbose_name = "Page"

    body = RichTextField(blank=True)
    quote = models.ForeignKey(
        'Quote',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    analysis = models.ForeignKey(
        'Analysis',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    profile = models.ForeignKey(
        'Profile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('quote'),
        FieldPanel('analysis'),
        FieldPanel('profile'),
    ]

    @property
    def menu_title(self):
        if self.seo_title:
            return self.seo_title
        return self.title


class DataPage(Page):
    body = RichTextField(blank=True)
    analysis = models.ForeignKey(
        'Analysis',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('analysis'),
    ]

    @property
    def menu_title(self):
        if self.seo_title:
            return self.seo_title
        return self.title


@register_snippet
class Profile(models.Model):
    name = models.CharField(max_length=255)
    body = RichTextField(blank=True)
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('image'),
        FieldPanel('body'),
    ]

    def __str__(self):
        return self.name


@register_snippet
class Analysis(models.Model):
    class Meta:
        verbose_name_plural = "Analyses"

    title = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    date = models.DateField("Post date")
    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
    ], use_json_field=True)

    panels = [
        FieldPanel('title'),
        FieldPanel('date'),
        FieldPanel('owner'),
        FieldPanel('body'),
    ]

    def __str__(self):
        return self.title


@register_snippet
class Quote(models.Model):
    quote = models.TextField()
    attribution = models.CharField(max_length=255)

    panels = [
        FieldPanel('quote'),
        FieldPanel('attribution'),
    ]

    def __str__(self):
        return self.attribution
