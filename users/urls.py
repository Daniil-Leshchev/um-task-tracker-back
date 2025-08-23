from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, UserProfileUpdateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='refresh-token'),
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/update/', UserProfileUpdateView.as_view(), name='user-profile-update')
]
