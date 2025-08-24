from django.urls import path
from .views import (
    AssignmentPolicyView, AllowedRecipientsListView
)

urlpatterns = [
    path('assignment-policy/', AssignmentPolicyView.as_view(),
         name='assignment-policy-list'),
    path('recipients/', AllowedRecipientsListView.as_view(), name='tasks-recipients'),
]
