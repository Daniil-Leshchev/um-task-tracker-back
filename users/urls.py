from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, UserProfileUpdateView, AdminUserListView, ConfirmUserView, DeleteUserView, MentorListForAssignmentView, AssignMentorView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='refresh-token'),
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/update/', UserProfileUpdateView.as_view(),
         name='user-profile-update'),
    path('users/admin-list/', AdminUserListView.as_view(), name='admin-users-list'),
    path('users/<int:id_tg>/confirm/', ConfirmUserView.as_view(), name='user-confirm'),
    path('users/<int:id_tg>/delete/', DeleteUserView.as_view(), name='delete-user'),
    path('users/mentors-for-assignment/', MentorListForAssignmentView.as_view(), name='mentors-for-assignment'),
    path('users/<int:id_tg>/assign-mentor/', AssignMentorView.as_view(), name='assign-mentor'),
]
