from django.urls import path, re_path

from .views import ActorRedirectView, ActorView, SearchView, PoliticiansView


urlpatterns = [
    path('search/', SearchView.as_view(), name='search'),
    path('politicians/', PoliticiansView.as_view(), name='politicians'),

    # re_path(r'^api/(?P<rel_type>.+)/(?P<direction>.+)/(?P<id>\d+)/?$', ApiView.as_view()),

    re_path(r'^actor/(?P<pk>\d+)(?:/(?P<slug>.*))?$', ActorRedirectView.as_view(), name='actor-detail'),
    re_path(r'^person/(?P<pk>\d+)(?:/(?P<slug>.*))?$', ActorView.as_view(), name='person-detail'),
    re_path(r'^organization/(?P<pk>\d+)(?:/(?P<slug>.*))?$', ActorView.as_view(), name='organization-detail'),
]
