from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from catalogs.models import Subject, Department, Role
from django.contrib.auth.password_validation import validate_password
from .constants import ADMIN_ROLE_IDS, MANAGER_ROLE_IDS

Curator = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    id_tg = serializers.IntegerField()
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=100)

    subject_id = serializers.IntegerField()
    department_id = serializers.IntegerField()
    role_id = serializers.IntegerField()

    mail_mg = serializers.CharField(
        max_length=100, required=False, allow_blank=True)

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = Curator
        fields = ('id_tg', 'email', 'name', 'subject_id', 'password',
                  'department_id', 'role_id', 'mail_mg', 'access', 'refresh')

    def validate_email(self, v: str):
        v = v.strip().lower()
        if Curator.objects.filter(email=v).exists():
            raise serializers.ValidationError('email_already_used')
        return v

    def validate(self, data):
        if not Subject.objects.filter(pk=data['subject_id']).exists():
            raise serializers.ValidationError({'subject_id': 'not_found'})
        if not Department.objects.filter(pk=data['department_id']).exists():
            raise serializers.ValidationError({'department_id': 'not_found'})
        if not Role.objects.filter(pk=data['role_id']).exists():
            raise serializers.ValidationError({'role_id': 'not_found'})
        if Curator.objects.filter(pk=data['id_tg']).exists():
            raise serializers.ValidationError({'id_tg': 'already_exists'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['email'] = validated_data['email'].lower()

        curator = Curator(**validated_data)
        curator.set_password(password)
        curator.save()

        refresh = RefreshToken.for_user(curator)
        validated_data = {
            'access':  str(refresh.access_token),
            'refresh': str(refresh)
        }
        curator._tokens = validated_data
        return curator

    def to_representation(self, instance):
        data = super().to_representation(instance)
        tokens = getattr(instance, '_tokens', {})
        data.update(tokens)
        return data


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'


class UserProfileSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.subject', read_only=True)

    department = serializers.CharField(
        source='department.department', read_only=True)

    role = serializers.CharField(source='role.role', read_only=True)

    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Curator
        fields = (
            'email',
            'first_name',
            'last_name',
            'subject',
            'department',
            'role',
            'is_admin'
        )
        read_only_fields = (
            'id_tg',
            'email',
            'subject',
            'department',
            'role',
            'is_admin'
        )

    def get_first_name(self, obj) -> str:
        if not obj.name:
            return ''
        parts = str(obj.name).strip().split()
        return parts[0] if parts else ''

    def get_last_name(self, obj) -> str:
        if not obj.name:
            return ''
        parts = str(obj.name).strip().split()
        return parts[-1] if len(parts) > 1 else ''

    def get_is_admin(self, obj) -> bool:
        role_id = getattr(getattr(obj, 'role', None), 'id_role', None)
        return role_id in ADMIN_ROLE_IDS


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(
        write_only=True, required=False, validators=[validate_password])
    new_password_confirm = serializers.CharField(
        write_only=True, required=False)

    class Meta:
        model = Curator
        fields = (
            'current_password',
            'new_password',
            'new_password_confirm',
        )

    def validate(self, attrs):
        user = self.context['request'].user

        current = attrs.get('current_password')
        new = attrs.get('new_password')
        confirm = attrs.get('new_password_confirm')

        if current or new or confirm:
            if not current or not new or not confirm:
                raise serializers.ValidationError(
                    'Для смены пароля нужно заполнить все три поля: текущий пароль, новый пароль и подтверждение')

            if not user.check_password(current):
                raise serializers.ValidationError(
                    {'current_password': 'Текущий пароль неверен'})

            if new != confirm:
                raise serializers.ValidationError(
                    {'new_password_confirm': 'Новый пароль и подтверждение не совпадают'})

        return attrs

    def update(self, instance, validated_data):
        new_password = validated_data.get('new_password', None)
        if new_password:
            instance.set_password(new_password)

        instance.save()
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.subject', read_only=True)
    department = serializers.CharField(
        source='department.department', read_only=True)
    role = serializers.CharField(source='role.role', read_only=True)

    need_confirmation = serializers.SerializerMethodField()
    mentor_name = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()

    class Meta:
        model = Curator
        fields = (
            'id_tg',
            'name',
            'subject',
            'department',
            'role',
            'role_id',
            'need_confirmation',
            'mentor_name',
            'is_manager'
        )

    def get_need_confirmation(self, obj) -> bool:
        return not bool(obj.confirm)

    def get_mentor_name(self, obj) -> str | None:
        email = (obj.mail_mg or '').strip().lower()
        if not email:
            return None
        mentor = Curator.objects.filter(
            email__iexact=email).only('name').first()
        return mentor.name if mentor else None

    def get_is_manager(self, obj):
        role_id = getattr(getattr(obj, 'role', None), 'id_role', None)
        return bool(role_id in MANAGER_ROLE_IDS)


class ConfirmPayloadSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=False, default=True)


class MentorShortSerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(source='role.id_role', read_only=True)
    role = serializers.CharField(source='role.role', read_only=True)
    subject = serializers.CharField(
        source='subject.subject', read_only=True, allow_null=True)
    department = serializers.CharField(
        source='department.department', read_only=True, allow_null=True)

    class Meta:
        model = Curator
        fields = ('id_tg', 'name', 'role_id', 'role', 'subject', 'department')
