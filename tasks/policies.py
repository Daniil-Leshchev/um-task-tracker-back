from django.db.models import QuerySet
from users.models import Curator
from users.constants import (
    ADMIN_ROLE_IDS, MENTOR_ROLE_IDS, ROLE_CHAT_MANAGER,
    ROLE_CURATOR_STANDARD, ROLE_OKK
)


def allowed_recipients_base_qs(author: Curator) -> QuerySet[Curator]:
    """Вернёт базовый QS тех, кому автор В ПРИНЦИПЕ может выдавать задачи."""
    role_id = getattr(getattr(author, 'role', None), 'id_role', None)

    # тут проверка, что пользователь подтвержденный

    # Суперюзеры — всем
    if role_id in ADMIN_ROLE_IDS or role_id == ROLE_OKK:
        return Curator.objects.all()
    # если надо – тут фильтрация по предмету

    # Наставник стандарт/личных — только «свои» кураторы.
    # Т.к. при привязке куратора уже учитываются ограничения на того, кто может быть наставником, доп проверку тут можно не делать
    if role_id in MENTOR_ROLE_IDS:
        return (Curator.objects
                .filter(subject_id=author.subject_id,
                        department_id=author.department_id,
                        mail_mg=author.email))  # связь «мой куратор»

    # # Наставник личных — только «свои» личные кураторы
    # if role_id == ROLE_MENTOR_PERSONAL:
    #     return (Curator.objects
    #             .filter(subject_id=author.subject_id,
    #                     department_id=author.department_id,
    #                     mail_mg=author.email))

    # Менеджер чата (пример) — стандарт-кураторы своего отдела
    if role_id == ROLE_CHAT_MANAGER:
        return (Curator.objects
                .filter(subject_id=author.subject_id)
                .filter(role__id_role__in=[ROLE_CURATOR_STANDARD]))

    # По умолчанию — никому
    return Curator.objects.none()
