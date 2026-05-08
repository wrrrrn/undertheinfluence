"""
URL routing for API v2
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter
from api.v2 import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

app_name = 'api_v2'

router = SimpleRouter()
router.register(r'politicians', views.PoliticianViewSet, basename='politician')
router.register(r'parties', views.PartyViewSet, basename='party')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # OpenAPI schema and documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_v2:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api_v2:schema'), name='redoc'),

    # Aggregate endpoints
    path('aggregates/stats/', views.HomepageStatsView.as_view(), name='homepage-stats'),
    path('aggregates/top-donors/', views.TopDonorsView.as_view(), name='top-donors'),
    path('aggregates/top-recipients/', views.TopRecipientsView.as_view(), name='top-recipients'),
    path('aggregates/network-stats/', views.NetworkStatsView.as_view(), name='network-stats'),
    path('aggregates/party-donations/', views.PartyDonationsView.as_view(), name='party-donations'),
    path('aggregates/dual-influence/', views.DualInfluenceView.as_view(), name='dual-influence'),
    path('aggregates/top-lobbying-clients/', views.TopLobbyingClientsView.as_view(), name='top-lobbying-clients'),
    path('aggregates/donor-concentration/', views.DonorConcentrationView.as_view(), name='donor-concentration'),
    path('aggregates/minister-network/', views.MinisterNetworkView.as_view(), name='minister-network'),
    path('aggregates/department-meetings/', views.DepartmentMeetingsView.as_view(), name='department-meetings'),

    # Actor detail endpoints
    path('actors/<int:pk>/', views.ActorDetailView.as_view(), name='actor-detail'),
    path('actors/<int:pk>/donations/', views.ActorDonationsView.as_view(), name='actor-donations'),
    path('actors/<int:pk>/consultancies/', views.ActorConsultanciesView.as_view(), name='actor-consultancies'),
    path('actors/<int:pk>/memberships/', views.ActorMembershipsView.as_view(), name='actor-memberships'),
    path('actors/<int:pk>/meetings/', views.ActorMeetingsView.as_view(), name='actor-meetings'),
    path('actors/<int:pk>/agency-clients/', views.AgencyClientsView.as_view(), name='agency-clients'),
    path('actors/<int:pk>/cross-connections/', views.ActorCrossConnectionsView.as_view(), name='actor-cross-connections'),
    path('actors/<int:pk>/funding-summary/', views.FundingSummaryView.as_view(), name='actor-funding-summary'),
    path('actors/<int:pk>/activity-by-year/', views.ActorActivityByYearView.as_view(), name='actor-activity-by-year'),
    path('departments/<int:pk>/meetings-summary/', views.DepartmentMeetingsSummaryView.as_view(), name='department-meetings-summary'),
]
