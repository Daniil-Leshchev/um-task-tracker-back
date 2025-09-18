from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Curator
from .constants import ROLE_TO_ALLOWED_MENTOR_ROLE_IDS
from .permissions import IsAdmin, IsConfirmedUser
from rest_framework.generics import ListAPIView
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, EmailTokenObtainPairSerializer, UserProfileSerializer, UserProfileUpdateSerializer, ConfirmPayloadSerializer, AdminUserSerializer, MentorShortSerializer


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
    serializer_class = AdminUserSerializer
    permission_classes = (IsAuthenticated, IsAdmin, IsConfirmedUser)

    def get_queryset(self):
        qs = Curator.objects.select_related('subject', 'department', 'role').all()
        u = self.request.user
        if getattr(u, 'subject_id', None):
            qs = qs.filter(subject_id=u.subject_id)
        qs = qs.order_by('confirm', 'name')
        return qs


class ConfirmUserView(APIView):
    permission_classes = (IsAuthenticated, IsAdmin, IsConfirmedUser)

    def patch(self, request, email: str):
        user = get_object_or_404(Curator.objects.select_related('subject', 'department', 'role'),
                                 pk=email)
        # можно прислать { "confirm": true/false }, по умолчанию true
        payload = ConfirmPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        confirm = payload.validated_data['confirm']

        user.confirm = bool(confirm)
        user.save(update_fields=['confirm'])

        data = AdminUserSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class DeleteUserView(generics.DestroyAPIView):
    queryset = Curator.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = (IsAuthenticated, IsAdmin, IsConfirmedUser)
    lookup_field = 'email'


class MentorListForAssignmentView(APIView):
    permission_classes = (IsAuthenticated, IsAdmin, IsConfirmedUser)

    def get(self, request):
        target_email = request.query_params.get('target_email')
        if not target_email:
            return Response({'detail': 'Параметр target_email обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        target = get_object_or_404(
            Curator.objects.select_related('role', 'department', 'subject'),
            pk=target_email
        )
        target_role_id = getattr(
            getattr(target, 'role', None), 'id_role', None)
        target_dept_id = getattr(
            getattr(target, 'department', None), 'id_department', None)
        target_subject_id = getattr(target, 'subject_id', None)
        if target_role_id is None:
            return Response({'detail': 'У целевого куратора не задана роль.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_roles = ROLE_TO_ALLOWED_MENTOR_ROLE_IDS.get(
            target_role_id, set())
        if not allowed_roles:
            return Response([], status=status.HTTP_200_OK)

        qs = (
            Curator.objects
            .select_related('role', 'subject', 'department')
            .filter(role__id_role__in=allowed_roles, confirm=True)
        )
        if target_dept_id:
            qs = qs.filter(department__id_department=target_dept_id)
        if target_subject_id:
            qs = qs.filter(subject_id=target_subject_id)

        qs = qs.order_by('name')
        data = MentorShortSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class AssignMentorView(APIView):
    permission_classes = (IsAuthenticated, IsAdmin, IsConfirmedUser)

    def patch(self, request, email: str):
        mentor_email = request.data.get('mentor_email')
        if not mentor_email:
            return Response({'detail': 'mentor_email обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        curator = get_object_or_404(
            Curator.objects.select_related('role', 'department', 'subject'),
            pk=email
        )

        mentor = get_object_or_404(
            Curator.objects.select_related('role', 'department', 'subject'),
            pk=mentor_email
        )

        curator_role_id = getattr(
            getattr(curator, 'role', None), 'id_role', None)
        mentor_role_id = getattr(
            getattr(mentor,  'role', None), 'id_role', None)
        allowed = ROLE_TO_ALLOWED_MENTOR_ROLE_IDS.get(curator_role_id, set())
        if mentor_role_id not in allowed:
            return Response({'detail': 'Этот наставник не подходит по роли.'}, status=status.HTTP_400_BAD_REQUEST)

        curator_dept_id = getattr(
            getattr(curator, 'department', None), 'id_department', None)
        mentor_dept_id = getattr(
            getattr(mentor,  'department', None), 'id_department', None)
        if curator_dept_id and mentor_dept_id and curator_dept_id != mentor_dept_id:
            return Response({'detail': 'Наставник должен быть из того же направления.'}, status=status.HTTP_400_BAD_REQUEST)
        curator_subject_id = getattr(curator, 'subject_id', None)
        mentor_subject_id = getattr(mentor, 'subject_id', None)
        if curator_subject_id and mentor_subject_id and curator_subject_id != mentor_subject_id:
            return Response({'detail': 'Наставник должен быть по тому же предмету.'}, status=status.HTTP_400_BAD_REQUEST)

        if not mentor.confirm:
            return Response({'detail': 'Наставник ещё не подтверждён.'}, status=status.HTTP_400_BAD_REQUEST)

        if mentor.email is None:
            return Response({'detail': 'У наставника нет почты.'}, status=status.HTTP_400_BAD_REQUEST)

        curator.mail_mg = mentor.email
        curator.save(update_fields=['mail_mg'])

        data = AdminUserSerializer(curator).data
        return Response(data, status=status.HTTP_200_OK)
