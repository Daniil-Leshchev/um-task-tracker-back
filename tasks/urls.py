from django.urls import path
from .views import (
    AssignmentPolicyView, AllowedRecipientsListView, TaskListCreateView, TaskDetailView, ReportDetailView
)

urlpatterns = [
    path('assignment-policy/', AssignmentPolicyView.as_view(),
         name='assignment-policy-list'),
    path('recipients/', AllowedRecipientsListView.as_view(), name='tasks-recipients'),
    path('<str:task_id>/', TaskDetailView.as_view(), name='task-detail'),
    path('reports/<str:task_id>/<str:email>/', ReportDetailView.as_view(), name='report-detail'),
    path('', TaskListCreateView.as_view(), name='tasks'),
]
