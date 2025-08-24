from django.urls import path
from .views import (
    AssignmentPolicyView
)

urlpatterns = [
    path('assignment-policy/', AssignmentPolicyView.as_view(),
         name='assignment-policy-list'),
]
