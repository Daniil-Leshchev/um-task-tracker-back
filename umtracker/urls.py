from django.urls import path, include

urlpatterns = [
    path('api/', include([
        path('catalogs/', include('catalogs.urls')),
        path('tasks/', include('tasks.urls')),
        path('', include('users.urls'))
    ])),
]
