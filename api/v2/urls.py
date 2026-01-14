"""
URL routing for API v2
"""

from django.urls import path
from api.v2 import views

app_name = 'api_v2'

urlpatterns = [
    # Aggregate endpoints
    path('aggregates/top-donors/', views.TopDonorsView.as_view(), name='top-donors'),
    path('aggregates/top-recipients/', views.TopRecipientsView.as_view(), name='top-recipients'),
    path('aggregates/network-stats/', views.NetworkStatsView.as_view(), name='network-stats'),

    # TODO: Add more aggregate endpoints
    # path('aggregates/party-donations/', views.PartyDonationsView.as_view(), name='party-donations'),
    # path('aggregates/dual-influence/', views.DualInfluenceView.as_view(), name='dual-influence'),
    # path('aggregates/donor-concentration/', views.DonorConcentrationView.as_view(), name='donor-concentration'),

    # TODO: Add actor detail endpoints
    # path('actors/<int:pk>/', views.ActorDetailView.as_view(), name='actor-detail'),
    # path('actors/<int:pk>/summary/', views.ActorSummaryView.as_view(), name='actor-summary'),
    # path('actors/<int:pk>/donations/', views.ActorDonationsView.as_view(), name='actor-donations'),
    # path('actors/<int:pk>/consultancies/', views.ActorConsultanciesView.as_view(), name='actor-consultancies'),
    # path('actors/<int:pk>/network/', views.ActorNetworkView.as_view(), name='actor-network'),
]
