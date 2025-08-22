from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
