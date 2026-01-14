from django.views.generic import TemplateView
from django.urls import path


urlpatterns = [
    path('', TemplateView.as_view(template_name='appc_redirect.html'), name='appc_redirect'),
]
