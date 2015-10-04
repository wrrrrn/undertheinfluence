from django.conf.urls import url

from .views import ActorRedirectView, ActorView, SearchView


urlpatterns = [
    url(r'^search/$', SearchView.as_view(), name='search'),

    url(r'^actor/(?P<id>\d+)(?:/(?P<slug>.*))?$', ActorRedirectView.as_view(), name='actor-detail'),
    url(r'^person/(?P<id>\d+)(?:/(?P<slug>.*))?$', ActorView.as_view(), name='person-detail'),
    url(r'^organization/(?P<id>\d+)(?:/(?P<slug>.*))?$', ActorView.as_view(), name='organization-detail'),
]
