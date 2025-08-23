from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Curator
from .constants import MANAGER_ROLE_IDS
from .permissions import IsAdmin
from .serializers import AdminUserListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from django.db.models import Q
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, EmailTokenObtainPairSerializer, UserProfileSerializer, UserProfileUpdateSerializer, ConfirmPayloadSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Curator.objects.all()

    def get_object(self):
        return self.get_queryset().get(pk=self.request.user.pk)


class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    http_method_names = ['patch']

    def get_queryset(self):
        return Curator.objects.all()

    def get_object(self):
        return self.get_queryset().get(pk=self.request.user.pk)

    def perform_update(self, serializer):
        serializer.save()


class AdminUserListView(ListAPIView):
    '''
    Список пользователей для админки.
    По умолчанию: все пользователи, сортировка — неподтвержденные сверху, затем по имени.
    Фильтры (query params):
      - q: строка поиска по name/email
      - subject_id: int
      - department_id: int
      - confirmed: 0/1
      - scope=current — ограничить по предмету/направлению как у текущего пользователя
      - only_curators=1 — исключить менеджерские роли
    '''
    serializer_class = AdminUserListSerializer
    permission_classes = (IsAuthenticated, IsAdmin,)

    def get_queryset(self):
        qs = Curator.objects.select_related(
            'subject', 'department', 'role'
        ).all()

        # поиск
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))

        # фильтры по справочникам
        sid = self.request.query_params.get('subject_id')
        did = self.request.query_params.get('department_id')
        if sid:
            qs = qs.filter(subject_id=sid)
        if did:
            qs = qs.filter(department_id=did)

        # подтверждение
        confirmed = self.request.query_params.get('confirmed')
        if confirmed == '1':
            qs = qs.filter(confirm=True)
        elif confirmed == '0':
            qs = qs.filter(confirm=False)

        # TODO: вот это можно будет оставить реально
        # область ответственности текущего пользователя (по предмету/направлению)
        if self.request.query_params.get('scope') == 'current':
            u = self.request.user
            if getattr(u, 'subject_id', None):
                qs = qs.filter(subject_id=u.subject_id)

        # только кураторы (исключить менеджерские роли)
        if self.request.query_params.get('only_curators') == '1':
            qs = qs.exclude(role_id__in=MANAGER_ROLE_IDS)

        # сортировка: сначала неподтвержденные (confirm=False), потом имя
        qs = qs.order_by('confirm', 'name')
        return qs


class ConfirmUserView(APIView):
    permission_classes = (IsAuthenticated, IsAdmin,)

    def patch(self, request, id_tg: int):
        user = get_object_or_404(Curator.objects.select_related('subject', 'department', 'role'),
                                 pk=id_tg)
        # можно прислать { "confirm": true/false }, по умолчанию true
        payload = ConfirmPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        confirm = payload.validated_data['confirm']

        user.confirm = bool(confirm)
        user.save(update_fields=['confirm'])

        data = AdminUserListSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class DeleteUserView(generics.DestroyAPIView):
    queryset = Curator.objects.all()
    serializer_class = AdminUserListSerializer
    permission_classes = (IsAdmin,)
    lookup_field = 'id_tg'
