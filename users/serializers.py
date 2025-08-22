from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from catalogs.models import Subject, Department, Role

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
            raise serializers.ValidationError("email_already_used")
        return v

    def validate(self, data):
        if not Subject.objects.filter(pk=data["subject_id"]).exists():
            raise serializers.ValidationError({"subject_id": "not_found"})
        if not Department.objects.filter(pk=data["department_id"]).exists():
            raise serializers.ValidationError({"department_id": "not_found"})
        if not Role.objects.filter(pk=data["role_id"]).exists():
            raise serializers.ValidationError({"role_id": "not_found"})
        if Curator.objects.filter(pk=data["id_tg"]).exists():
            raise serializers.ValidationError({"id_tg": "already_exists"})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["email"] = validated_data["email"].lower()

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
