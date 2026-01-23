"""
User profile URL routes.
"""
from django.urls import path
from apps.user.views import ProfileView

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='user-profile'),
]
