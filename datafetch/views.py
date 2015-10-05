from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.db.models import Q

from datafetch import models


class ActorRedirectView(RedirectView):

    permanent = False
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        actor = get_object_or_404(models.Actor, pk=kwargs['id'])
        self.pattern_name = actor.url_name
        kwargs['slug'] = slugify(actor.name)
        return super(ActorRedirectView, self).get_redirect_url(*args, **kwargs)


class SearchView(TemplateView):
    template_name = 'search.html'

    def get_context_data(self, *args, **kwargs):
        context = super(SearchView, self).get_context_data(**kwargs)

        query = self.request.GET.get('q', '')

        context["query"] = query
        qset = models.Actor.objects.filter(
            Q(name__icontains=query) |
            Q(Organization___other_names__name__icontains=query) |
            Q(Person___other_names__name__icontains=query)
        ).distinct('id')
        context["num_results"] = format(qset.count(), ",d")
        context["results"] = qset[:10]

        return context


class ActorView(TemplateView):
    template_name = 'actor.html'

    def get_context_data(self, **kwargs):
        context = super(ActorView, self).get_context_data(**kwargs)

        actor = get_object_or_404(models.Actor, pk=kwargs['id'])
        context['actor'] = actor
        context['links'] = actor.links.all()

        context['memberships'] = actor.memberships.order_by('-end_date', '-start_date')[:10]

        context['donations_from'] = actor.received_donations_from.order_by('-received_date')[:10]
        context['donations_to'] = actor.donated_to.order_by('-received_date')[:10]

        context['consults_for'] = actor.consults_for.order_by('-received_date')[:10]
        context['consultants'] = actor.consultants.order_by('-received_date')[:10]

        return context
