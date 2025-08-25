from django.urls import path
from .views import (
    AssignmentPolicyView, AllowedRecipientsListView, TaskCardListView
)

urlpatterns = [
    path('assignment-policy/', AssignmentPolicyView.as_view(),
         name='assignment-policy-list'),
    path('recipients/', AllowedRecipientsListView.as_view(), name='tasks-recipients'),
    path('', TaskCardListView.as_view(), name='tasks-cards'),
]
