from rest_framework import serializers
from .models import Role, Subject, Department, Status


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id_role', 'role')


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ('id_subject', 'subject')


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ('id_department', 'department')


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ('id_status', 'status')
