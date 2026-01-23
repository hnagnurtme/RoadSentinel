"""
URL configuration for RoadSentinel project.
"""
from django.contrib import admin
from django.urls import path, include
from config.swagger import schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Application routes
    path('api/auth/', include('apps.auth.urls')),
    path('api/user/', include('apps.user.urls')),
]
