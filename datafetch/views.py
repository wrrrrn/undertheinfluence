from django.views.generic import TemplateView

from datafetch import models


class PersonView(TemplateView):
    template_name = 'person.html'

    def get_context_data(self, **kwargs):
        context = super(PersonView, self).get_context_data(**kwargs)

        person = models.Person.objects.get(
            id=self.kwargs['person_id']
        )
        memberships = person.memberships.order_by('-start_date')

        context['person'] = person
        context['memberships'] = memberships

        return context

