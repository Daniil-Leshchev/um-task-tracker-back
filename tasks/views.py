from django.shortcuts import get_object_or_404
from tasks.serializers import RecipientCuratorSerializer
from users.models import Curator
from rest_framework import status
from django.db.models import QuerySet
from typing import Optional, List, Sequence
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsConfirmedUser
from users.constants import (
    ADMIN_ROLE_IDS, ROLE_CURATOR_SENIOR, ROLE_CURATOR_PERSONAL,
    ROLE_CURATOR_STANDARD, ROLE_MENTOR_PERSONAL, ROLE_MENTOR_STANDARD,
    ROLE_CHAT_MANAGER, ROLE_OKK
)
from .services import AssignmentInput, create_task_and_assign, task_cards_queryset, visible_reports_for, build_targets_qs
from .serializers import TaskCreateSerializer, TaskCardSerializer, TaskDetailSerializer, ReportDetailSerializer
from .constants import EXCLUDE_FROM_TOTAL_STATUSES
from .models import Task, Report


class AssignmentPolicyView(APIView):
    permission_classes = (IsAuthenticated, IsConfirmedUser)

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
                'role_id': u.role_id
            }
        }

        if role_id in ADMIN_ROLE_IDS:
            payload.update({
                'can_pick_subject': True,
                'can_pick_department': True,
                'allowed_recipient_role_ids': [1, 2, 3, 4, 5, 6],
            })
        elif role_id == ROLE_OKK:
            payload.update({
                'can_pick_subject': False,
                'can_pick_department': False,
                'allowed_recipient_role_ids': [ROLE_CURATOR_STANDARD, ROLE_CURATOR_SENIOR, ROLE_CURATOR_PERSONAL],
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
                'can_pick_department': True,
                'allowed_recipient_role_ids': [ROLE_CURATOR_STANDARD],
            })
        else:
            payload.update({
                'can_assign': False,
                'reason_if_denied': 'Ваша роль не может назначать задачи'
            })

        return Response(payload)


class TaskListCreateView(APIView):
    permission_classes = (IsAuthenticated, IsConfirmedUser)

    def get(self, request):
        scope = request.query_params.get('scope', 'all')
        subject_id = request.query_params.get('subject_id')
        department_id = request.query_params.get('department_id')
        q = request.query_params.get('q')

        try:
            subject_id = int(subject_id) if subject_id else None
            department_id = int(department_id) if department_id else None
        except ValueError:
            return Response({'detail': 'IDs must be integers'}, status=status.HTTP_400_BAD_REQUEST)

        qs = task_cards_queryset(
            request.user,
            scope=scope,
            subject_id=subject_id,
            department_id=department_id,
            q=q,
        ).order_by('-deadline', '-id_task')

        return Response(TaskCardSerializer(qs, many=True).data, status=200)

    def post(self, request):
        ser = TaskCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        department_ids = (
            ser.validated_data.get('department_ids')
            or ([ser.validated_data.get('department_id')]
                if ser.validated_data.get('department_id') is not None else None)
        )

        author = request.user
        inp = AssignmentInput(
            subject_id=ser.validated_data.get('subject_id'),
            department_ids=department_ids,
            role_ids=ser.validated_data.get('role_ids'),
            emails=ser.validated_data.get('emails'),
            single_email=ser.validated_data.get('single_email'),
        )

        try:
            task, assignments, delivery = create_task_and_assign(
                author=author,
                deadline=ser.validated_data['deadline'],
                name=ser.validated_data['name'],
                description=ser.validated_data['description'],
                report_template=ser.validated_data['report'],
                recipients=inp,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if delivery.get('bot_unavailable'):
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif not delivery.get('ok', False):
            http_status = status.HTTP_207_MULTI_STATUS
        else:
            http_status = status.HTTP_201_CREATED

        payload = {
            'id_task': task.id_task,
            'assignments': [
                {
                    'assignment_id': r['assignment_id'],
                    'status': r['status'],
                    'undelivered': r.get('undelivered_names', []),
                    'error': r['error'],
                }
                for r in delivery.get('assignments', [])
            ],
            'summary': delivery.get('summary', {}),
            'ok': delivery.get('ok'),
            'undelivered_all': delivery.get('undelivered_names_all', []),
            'bot_unavailable': delivery.get('bot_unavailable', False),
        }

        return Response(payload, status=http_status)


def _to_int(val: Optional[str]) -> Optional[int]:
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _to_int_list(val: Optional[str]) -> Optional[List[int]]:
    if not val:
        return None
    out: List[int] = []
    for part in val.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            return None
    return out or None


def _to_str_list(val: Optional[str]) -> Optional[List[str]]:
    if not val:
        return None
    out: List[str] = []
    for part in val.split(','):
        part = part.strip()
        if part:
            out.append(part)
    return out or None


class AllowedRecipientsListView(APIView):
    permission_classes = (IsAuthenticated, IsConfirmedUser)

    def get(self, request):
        author: Curator = request.user

        subject_id = _to_int(request.query_params.get('subject_id'))
        department_ids = _to_int_list(
            request.query_params.get('department_ids'))
        if department_ids is None:
            single_dep = _to_int(request.query_params.get('department_id'))
            department_ids = [single_dep] if single_dep is not None else None
        role_ids = _to_int_list(request.query_params.get('role_ids'))
        single_email = request.query_params.get('single_email') or None
        emails = _to_str_list(request.query_params.get('emails'))

        inp = AssignmentInput(
            subject_id=subject_id,
            department_ids=department_ids,
            role_ids=role_ids,
            emails=emails,
            single_email=single_email,
        )

        qs: QuerySet[Curator] = (
            build_targets_qs(author, inp)
            .select_related('role', 'subject', 'department')
            .order_by('name')
        )

        data = RecipientCuratorSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class TaskDetailView(APIView):
    permission_classes = (IsAuthenticated, IsConfirmedUser)

    def get(self, request, task_id: str):
        get_object_or_404(Task, pk=task_id)

        qs = (
            visible_reports_for(request.user)
            .filter(task_id=task_id)
            .exclude(status_id__in=EXCLUDE_FROM_TOTAL_STATUSES)
            .select_related('curator', 'curator__role')
        )

        data = TaskDetailSerializer(qs, many=True).data
        return Response(data, status=200)


class ReportDetailView(APIView):
    permission_classes = (IsAuthenticated, IsConfirmedUser)

    def get(self, request, task_id, email):
        report = get_object_or_404(
            Report.objects.select_related('task', 'curator', 'curator__role'),
            task__id_task=task_id,
            curator__email=email
        )
        data = ReportDetailSerializer(report).data
        return Response(data, status=status.HTTP_200_OK)
