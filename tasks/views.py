from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.constants import (
    ADMIN_ROLE_IDS, ROLE_CURATOR_SENIOR, ROLE_CURATOR_PERSONAL,
    ROLE_CURATOR_STANDARD, ROLE_MENTOR_PERSONAL, ROLE_MENTOR_STANDARD,
    ROLE_CHAT_MANAGER, ROLE_OKK
)


class AssignmentPolicyView(APIView):
    '''Список тех, кому можно назначить задачу'''
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        u = request.user
        role_id = getattr(getattr(u, 'role', None), 'id_role', None)

        if not getattr(u, 'confirm', False):
            return Response({
                'can_assign': False,
                'reason_if_denied': 'Ваш профиль не подтверждён, обратитесь к руководителю'
            })

        payload = {
            'can_assign': True,
            'reason_if_denied': None,
            'can_pick_subject': False,
            'can_pick_department': False,
            'allowed_recipient_role_ids': [],
            'defaults': {
                'subject_id': u.subject_id,
                'department_id': u.department_id,
            }
        }

        if role_id in ADMIN_ROLE_IDS or role_id == ROLE_OKK:
            payload.update({
                'can_pick_subject': True,
                'can_pick_department': True,
                'allowed_recipient_role_ids': [1, 2, 3, 4, 5, 6, 7, 9],
            })
        elif role_id == ROLE_MENTOR_STANDARD:
            payload.update({
                'can_pick_subject': False,
                'can_pick_department': False,
                'allowed_recipient_role_ids': [ROLE_CURATOR_STANDARD],
            })
        elif role_id == ROLE_MENTOR_PERSONAL:
            payload.update({
                'can_pick_subject': False,
                'can_pick_department': False,
                'allowed_recipient_role_ids': [ROLE_CURATOR_SENIOR, ROLE_CURATOR_PERSONAL],
            })
        elif role_id == ROLE_CHAT_MANAGER:
            payload.update({
                'can_pick_subject': False,
                'can_pick_department': False,
                'allowed_recipient_role_ids': [ROLE_CURATOR_STANDARD],
            })
        else:
            # другие роли — запретим
            payload.update({
                'can_assign': False,
                'reason_if_denied': 'Ваша роль не может назначать задачи'
            })

        return Response(payload)
