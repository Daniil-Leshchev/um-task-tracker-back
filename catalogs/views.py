from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from .models import Role, Subject, Department, Status
from .serializers import (
    RoleSerializer, SubjectSerializer, DepartmentSerializer, StatusSerializer
)

ALLOWED_REG_ROLE_NAMES = {
    'Асессор ОКК',
    'Менеджер чата',
    'Наставник Стандартов',
    'Наставник Личных',
    'Старший наставник',
    'Руководитель предмета',
}


class BaseCatalogListView(ListAPIView):
    permission_classes = (AllowAny,)


class RolesListView(BaseCatalogListView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RolesManagersListView(BaseCatalogListView):
    queryset = Role.objects.filter(role__in=ALLOWED_REG_ROLE_NAMES)
    serializer_class = RoleSerializer


class SubjectsListView(BaseCatalogListView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class DepartmentsListView(BaseCatalogListView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class StatusesListView(BaseCatalogListView):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
