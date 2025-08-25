from typing import Iterable, Optional
from django.utils import timezone
from django.db import transaction, connection
from users.models import Curator
from tasks.models import Task, Assignment, Report
from .policies import allowed_recipients_base_qs
from django.db.models import (
    Q, Count, F, Case, When, Value, QuerySet, FloatField, CharField,
    Min, OuterRef, Subquery, Exists
)
from django.contrib.postgres.aggregates import ArrayAgg
from .constants import NOT_COMPLETED_STATUS, EXCLUDE_FROM_TOTAL_STATUSES, COMPLETED_STATUSES


def _next_task_id_for_subject(author: Curator) -> str:
    subject_id = getattr(getattr(author, "subject", None), "id_subject", None)
    lock_id = subject_id if subject_id is not None else 0
    name = getattr(getattr(author, "subject", None), "name", None)
    if name:
        prefix = name[:3].lower()
    else:
        prefix = "tsk"
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s);", [lock_id])
        qs = Task.objects.filter(id_task__startswith=f"{prefix}-")
        max_num = 0
        for t in qs:
            try:
                suffix = t.id_task.split("-", 1)[1]
                num = int(suffix)
                if num > max_num:
                    max_num = num
            except Exception:
                continue
        return f"{prefix}-{max_num + 1}"


class AssignmentInput:
    def __init__(
        self,
        *,
        subject_id: Optional[int] = None,
        department_id: Optional[int] = None,
        role_ids: Optional[Iterable[int]] = None,
        id_tg_list: Optional[Iterable[int]] = None,
        single_id_tg: Optional[int] = None
    ):
        self.subject_id = subject_id
        self.department_id = department_id
        self.role_ids = list(role_ids) if role_ids else None
        self.id_tg_list = list(id_tg_list) if id_tg_list else None
        self.single_id_tg = single_id_tg


def build_targets_qs(author: Curator, inp: AssignmentInput) -> QuerySet[Curator]:
    base = (allowed_recipients_base_qs(author)
            .select_related('role', 'department', 'subject'))

    # индивидуальная выдача имеет приоритет
    if inp.single_id_tg:
        return base.filter(pk=inp.single_id_tg)
    if inp.id_tg_list:
        return base.filter(pk__in=inp.id_tg_list)

    # групповые фильтры (только узкое пересечение с base)
    if inp.subject_id:
        base = base.filter(subject_id=inp.subject_id)
    if inp.department_id:
        base = base.filter(department_id=inp.department_id)
    if inp.role_ids:
        base = base.filter(role__id_role__in=inp.role_ids)

    return base


@transaction.atomic
def create_task_and_assign(
    *,
    author: Curator,
    deadline,
    name: str,
    description: str,
    report_template: str,
    recipients: AssignmentInput
) -> Task:
    """
    Создаёт задачу с уникальным id_task для предмета автора, и назначает её выбранным получателям.
    """
    # 1) Валидация, что автор вообще кому-то может назначать
    qs_allowed = build_targets_qs(author, recipients)
    targets = list(qs_allowed)
    if not targets:
        raise ValueError('Нет ни одного получателя по вашим правам/фильтрам.')

    # 2) Генерируем уникальный id_task для предмета
    task_id = _next_task_id_for_subject(author)

    # 3) Создаём Task
    task = Task.objects.create(
        id_task=task_id,
        deadline=deadline,
        name=name,
        description=description,
        report=report_template,
        author=author
    )

    # 4) Готовим Assignment и стартовые Report
    now = timezone.now()
    assigns = []
    reports = []
    for tgt in targets:
        assigns.append(Assignment(
            task=task,
            subject=tgt.subject,
            department=tgt.department,
            role=tgt.role,
            curator=tgt,
            author=author
        ))
        reports.append(Report(
            curator=tgt,
            task=task,
            status_id=NOT_COMPLETED_STATUS,
            timestamp_start=now
        ))

    Assignment.objects.bulk_create(assigns, batch_size=1000)
    Report.objects.bulk_create(reports, batch_size=1000)

    return task


def visible_assignments_for(user: Curator):
    allowed_curators = allowed_recipients_base_qs(user).values('id_tg')
    return Assignment.objects.filter(curator_id__in=Subquery(allowed_curators))


def task_cards_queryset(
    user: Curator, *,
    scope: str = 'all',
    subject_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
):
    ass_qs = visible_assignments_for(user) \
        .select_related('task')

    ass_qs = ass_qs.filter(task__author__subject_id=user.subject_id)

    if subject_id:
        ass_qs = ass_qs.filter(task__author__subject_id=subject_id)
    if department_id:
        ass_qs = ass_qs.filter(department_id=department_id)
    if q:
        ass_qs = ass_qs.filter(task__name__icontains=q)

    task_ids = ass_qs.values('task_id').distinct()
    qs = Task.objects.filter(id_task__in=Subquery(task_ids))

    # Исключаем задачи, которые хотя бы у одного видимого получателя были отменены
    cancelled_for_visible = Report.objects.filter(
        task_id=OuterRef('id_task'),
        status_id=4,
        curator_id__in=Subquery(ass_qs.values('curator_id')),
    )
    qs = qs.annotate(_has_cancelled=Exists(cancelled_for_visible)) \
           .filter(_has_cancelled=False)

    if scope in ('group', 'individual'):
        ass_count = (ass_qs.values('task_id')
                           .annotate(n=Count('curator_id'))
                           .filter(task_id=OuterRef('id_task'))
                           .values('n')[:1])
        qs = qs.annotate(_n=Subquery(ass_count))
        qs = qs.filter(_n__gte=2) if scope == 'group' else qs.filter(_n=1)

    qs = qs.annotate(
        total=Count(
            'reports',
            filter=Q(
                reports__curator_id__in=Subquery(ass_qs.values('curator_id'))
            ) & ~Q(reports__status_id__in=EXCLUDE_FROM_TOTAL_STATUSES),
            distinct=True,
        ),
        completed=Count(
            'reports',
            filter=Q(
                reports__curator_id__in=Subquery(ass_qs.values('curator_id'))
            ) & Q(reports__status_id__in=COMPLETED_STATUSES),
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
        sample_names=ArrayAgg('assignments__curator__name',
                              filter=Q(assignments__in=ass_qs),
                              distinct=True),
        created=Min(
            'reports__timestamp_start',
            filter=Q(reports__curator_id__in=Subquery(ass_qs.values('curator_id')))
        ),
    )

    return qs
