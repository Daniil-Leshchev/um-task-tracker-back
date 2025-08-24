from typing import Iterable, Optional
from django.utils import timezone
from django.db import transaction, connection
from django.db.models import QuerySet
from users.models import Curator
from tasks.models import Task, Assignment, Report
from .policies import allowed_recipients_base_qs

NOT_COMPLETED_STATUS = 3

SUBJECT_PREFIXES = {
    'информатика': 'инф',
    'математика': 'мат',
    'русский язык': 'рус',
    'английский язык': 'анг',
    'биология': 'био',
    'география': 'гео',
    'история': 'ист',
    'литература': 'лит',
    'обществознание': 'общ',
    'физика': 'физ',
    'химия': 'хим',
    'окк': 'окк',
}


def _subject_prefix_for(author: Curator) -> str:
    """Get the subject prefix for the given curator's subject."""
    name = getattr(getattr(author, "subject", None), "name", None)
    if name:
        name = name.lower()
        return SUBJECT_PREFIXES.get(name, name[:3].lower() if len(name) >= 3 else 'tsk')
    return 'tsk'


def _next_task_id_for_subject(author: Curator) -> str:
    """
    Generate the next unique task id for the subject of the given author.
    Uses advisory lock to avoid race conditions.
    """
    subject_id = getattr(getattr(author, "subject", None), "id_subject", None)
    lock_id = subject_id if subject_id is not None else 0
    prefix = _subject_prefix_for(author)
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
