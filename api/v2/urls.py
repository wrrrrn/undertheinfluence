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
    path('aggregates/party-donations/', views.PartyDonationsView.as_view(), name='party-donations'),
    path('aggregates/dual-influence/', views.DualInfluenceView.as_view(), name='dual-influence'),

    # Actor detail endpoints
    path('actors/<int:pk>/', views.ActorDetailView.as_view(), name='actor-detail'),
    path('actors/<int:pk>/donations-made/', views.ActorDonationsMadeView.as_view(), name='actor-donations-made'),
    path('actors/<int:pk>/donations-received/', views.ActorDonationsReceivedView.as_view(), name='actor-donations-received'),
    path('actors/<int:pk>/consultancies/', views.ActorConsultanciesView.as_view(), name='actor-consultancies'),
]
