from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('api/', include([
        path('catalogs/', include('catalogs.urls')),
        path('tasks/', include('tasks.urls')),
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
        path('', include('users.urls'))
    ])),
]
