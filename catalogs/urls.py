from django.urls import path
from .views import (
    RolesListView, RolesManagersListView, SubjectsListView, DepartmentsListView, StatusesListView
)

urlpatterns = [
    path('roles/', RolesListView.as_view(), name='roles-list'),
    path('roles/managers/', RolesManagersListView.as_view(),
         name='roles-managers-list'),
    path('subjects/', SubjectsListView.as_view(), name='subjects-list'),
    path('departments/', DepartmentsListView.as_view(),
         name='departments-list'),
    path('statuses/', StatusesListView.as_view(), name='statuses-list'),
]
