from django.urls import path
from .views import (
    AssignmentPolicyView, AllowedRecipientsListView, TaskCardListView, TaskDetailView
)

urlpatterns = [
    path('assignment-policy/', AssignmentPolicyView.as_view(),
         name='assignment-policy-list'),
    path('recipients/', AllowedRecipientsListView.as_view(), name='tasks-recipients'),
    path('<str:task_id>/', TaskDetailView.as_view(), name='task-detail'),
    path('', TaskCardListView.as_view(), name='tasks-cards'),
]
