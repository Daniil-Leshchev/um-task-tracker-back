from typing import Iterable, Optional
from django.db import transaction, connection
from users.models import Curator
from tasks.models import Task, Assignment, Report
from catalogs.models import Subject
from .policies import allowed_recipients_base_qs
from django.db.models import (
    Q, Count, F, Case, When, Value, QuerySet, FloatField, CharField,
    Min, OuterRef, Subquery, Exists
)
from django.contrib.postgres.aggregates import ArrayAgg
from .constants import EXCLUDE_FROM_TOTAL_STATUSES, COMPLETED_STATUSES
from .bot_client import (
    bot_ping,
    bot_send_assignment,
)


def _next_task_id_for_subject(subject_id: int | None) -> str:
    lock_id = subject_id or 0

    prefix = 'tsk'
    if subject_id:
        subj = Subject.objects.filter(pk=subject_id).only('subject').first()
        if subj and getattr(subj, 'subject', None):
            prefix = (subj.subject or '').strip().lower()[:3] or 'tsk'

    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s);', [lock_id])

        max_num = 0
        for task_id in Task.objects.filter(id_task__startswith=f'{prefix}-').values_list('id_task', flat=True):
            try:
                suffix = str(task_id).split('-', 1)[1]
                num = int(suffix)
                if num > max_num:
                    max_num = num
            except Exception:
                continue

        return f'{prefix}-{max_num + 1}'


class AssignmentInput:
    def __init__(
        self,
        *,
        subject_id: Optional[int] = None,
        department_ids: Optional[Iterable[int]] = None,
        role_ids: Optional[Iterable[int]] = None,
        emails: Optional[Iterable[str]] = None,
        single_email: Optional[str] = None,
    ):
        self.subject_id = subject_id
        self.department_ids = list(department_ids) if department_ids else None
        self.role_ids = list(role_ids) if role_ids else None

        self.emails = list(emails) if emails else None
        self.single_email = single_email


def build_targets_qs(author: Curator, inp: AssignmentInput) -> QuerySet[Curator]:
    base = (allowed_recipients_base_qs(author)
            .select_related('role', 'department', 'subject'))

    if getattr(inp, 'single_email', None):
        return base.filter(email=inp.single_email)
    if getattr(inp, 'emails', None):
        return base.filter(email__in=inp.emails)

    if inp.subject_id:
        base = base.filter(subject_id=inp.subject_id)
    if inp.department_ids:
        base = base.filter(department_id__in=inp.department_ids)
    if inp.role_ids:
        base = base.filter(role__id_role__in=inp.role_ids)

    return base


def create_task_and_assign(
    *,
    author: Curator,
    deadline,
    name: str,
    description: str,
    report_template: str,
    recipients: AssignmentInput
) -> tuple[Task, list[Assignment], dict]:
    qs_allowed = build_targets_qs(author, recipients)
    if not qs_allowed.exists():
        raise ValueError('Нет ни одного получателя по вашим правам/фильтрам.')

    task_id = _next_task_id_for_subject(
        recipients.subject_id or getattr(author, 'subject_id', None)
    )

    delivery_result: dict = {
        'ok': None,
        'bot_unavailable': False,
        'assignments': [],
        'summary': {
            'total': 0,
            'sent': 0,
            'partial': 0,
            'failed': 0,
        },
    }

    assignments: list[Assignment] = []
    assignment_ids: list[int] = []

    with transaction.atomic():
        task = Task.objects.create(
            id_task=task_id,
            deadline=deadline,
            name=name,
            description=description,
            report=report_template,
            author=author
        )

        is_individual = bool(recipients.single_email or recipients.emails)

        if is_individual:
            curators = list(qs_allowed)
            if not curators:
                raise ValueError('Получатель не найден или недоступен.')
            for curator in curators:
                a = Assignment.objects.create(
                    task=task,
                    subject=curator.subject,
                    department=curator.department,
                    role=curator.role,
                    curator=curator,
                    author=author
                )
                assignments.append(a)
                assignment_ids.append(a.id_assignment)

        else:
            if not (recipients.subject_id and recipients.department_ids and recipients.role_ids):
                raise ValueError('Для группового назначения укажите subject_id, department_ids и role_ids.')
            for department_id in recipients.department_ids:
                for role_id in recipients.role_ids:
                    a = Assignment.objects.create(
                        task=task,
                        subject_id=recipients.subject_id,
                        department_id=department_id,
                        role_id=role_id,
                        curator=None,
                        author=author
                    )
                    assignments.append(a)
                    assignment_ids.append(a.id_assignment)

        def _after_commit():
            if not bot_ping():
                delivery_result['ok'] = False
                delivery_result['bot_unavailable'] = True
                delivery_result['summary'] = {
                    'total': len(assignment_ids),
                    'sent': 0,
                    'partial': 0,
                    'failed': len(assignment_ids),
                }
                return

            a_by_id = {a.id_assignment: a for a in assignments}

            total = len(assignment_ids)
            sent = partial = failed = 0
            detailed: list[dict] = []
            all_undelivered_tg: list[int] = []

            for a_id in assignment_ids:
                a = a_by_id[a_id]
                cur = a.curator

                if cur and not cur.id_tg:
                    detailed.append({
                        'assignment_id': a_id,
                        'status': 'failed',
                        'undelivered_tg': [],
                        'error': 'no_id_tg',
                    })
                    failed += 1
                    continue

                r = bot_send_assignment(a_id)

                undelivered = (r.get('undelivered_tg') or r.get('undelivered') or [])
                is_individual = bool(a_by_id.get(a_id) and a_by_id[a_id].curator_id)
                status = r.get('status')

                if status != 'sent':
                    if is_individual and undelivered:
                        status = 'failed'
                    elif undelivered and status != 'failed':
                        status = 'partially_sent'
                    elif r.get('error'):
                        status = 'failed'

                if status == 'sent':
                    sent += 1
                elif status == 'partially_sent':
                    partial += 1
                else:
                    failed += 1

                all_undelivered_tg.extend(undelivered)
                detailed.append({
                    'assignment_id': a_id,
                    'status': status,
                    'undelivered_tg': undelivered,
                    'error': r.get('error')
                })

            id_to_name = dict(
                Curator.objects
                .filter(id_tg__in=all_undelivered_tg)
                .values_list('id_tg', 'name')
            )

            for row in detailed:
                names = [id_to_name.get(tg_id, str(tg_id)) for tg_id in row.pop('undelivered_tg', [])]
                row['undelivered_names'] = names

            delivery_result['assignments'] = detailed
            delivery_result['summary'] = {
                'total': total,
                'sent': sent,
                'partial': partial,
                'failed': failed,
            }
            delivery_result['ok'] = (failed == 0)
            delivery_result['undelivered_names_all'] = [
                id_to_name.get(tg_id, str(tg_id)) for tg_id in all_undelivered_tg
            ]

        transaction.on_commit(_after_commit)

    return task, assignments, delivery_result


def visible_reports_for(user: Curator):
    allowed_curators = allowed_recipients_base_qs(user).values('pk')
    return (Report.objects
            .select_related('task', 'curator', 'curator__role', 'curator__department', 'curator__subject')
            .filter(curator_id__in=Subquery(allowed_curators)))


def task_cards_queryset(
    user: Curator, *,
    scope: str = 'all',
    subject_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
):
    rep_qs = visible_reports_for(user)

    rep_qs = rep_qs.filter(task__author__subject_id=user.subject_id)

    if subject_id:
        rep_qs = rep_qs.filter(curator__subject_id=subject_id)
    if department_id:
        rep_qs = rep_qs.filter(curator__department_id=department_id)
    if q:
        rep_qs = rep_qs.filter(task__name__icontains=q)

    task_ids = rep_qs.values('task_id').distinct()
    qs = Task.objects.filter(id_task__in=Subquery(task_ids))

    visible_curators = allowed_recipients_base_qs(user).values('pk')

    personal_exists = Exists(
        Assignment.objects
        .filter(task_id=OuterRef('id_task'), curator_id__in=Subquery(visible_curators))
    )
    group_exists = Exists(
        Assignment.objects
        .filter(task_id=OuterRef('id_task'), curator_id__isnull=True)
    )

    qs = qs.annotate(_has_personal=personal_exists,
                     _has_group=group_exists)

    cancelled_for_visible = rep_qs.filter(
        task_id=OuterRef('id_task'), status_id=4)
    qs = qs.annotate(_has_cancelled=Exists(
        cancelled_for_visible)).filter(_has_cancelled=False)

    if scope == 'group':
        qs = qs.filter(_has_group=True)
    elif scope == 'individual':
        qs = qs.filter(
            Q(_has_personal=True, _has_group=False)
            # Q(_has_personal=True, _has_group=True)
        )

    qs = qs.annotate(
        total=Count(
            'reports',
            filter=Q(reports__curator_id__in=Subquery(rep_qs.values('curator_id'))) &
            ~Q(reports__status_id__in=EXCLUDE_FROM_TOTAL_STATUSES),
            distinct=True,
        ),
        completed=Count(
            'reports',
            filter=Q(reports__curator_id__in=Subquery(rep_qs.values('curator_id'))) &
            Q(reports__status_id__in=COMPLETED_STATUSES),
            distinct=True,
        ),
    ).annotate(
        not_completed=F('total') - F('completed'),
        progress=Case(
            When(total__gt=0, then=(100.0 * F('completed') / F('total'))),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        card_status=Case(
            When(total__gt=0, completed=F('total'), then=Value('Завершено')),
            When(completed__gt=0, then=Value('В процессе')),
            default=Value('Не начато'),
            output_field=CharField(),
        ),
        sample_names=ArrayAgg(
            'reports__curator__name',
            filter=Q(reports__curator_id__in=Subquery(
                rep_qs.values('curator_id'))),
            distinct=True,
        ),
        created=Min(
            'reports__timestamp_start',
            filter=Q(reports__curator_id__in=Subquery(
                rep_qs.values('curator_id')))
        ),
        on_time=Count(
            'reports',
            filter=Q(reports__curator_id__in=Subquery(rep_qs.values('curator_id'))) &
            Q(reports__status_id__in=COMPLETED_STATUSES) &
            Q(reports__timestamp_end__lte=F('deadline')),
            distinct=True,
        ),
    )

    return qs
