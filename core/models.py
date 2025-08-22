from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager


class CuratorManager(BaseUserManager):
    use_in_migrations = True

    def _normalize_email(self, email: str) -> str:
        if not email:
            raise ValueError("Email обязателен")
        return self.normalize_email(email)

    def create_user(self, email: str, password: str = None, **extra_fields):
        email = self._normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Curator(AbstractBaseUser):
    id_tg = models.BigIntegerField(primary_key=True, db_column="id_tg")
    name = models.CharField(max_length=100, db_column="name")

    subject = models.ForeignKey(
        "Subject", on_delete=models.PROTECT, db_column="id_subject", related_name="curators"
    )
    department = models.ForeignKey(
        "Department", on_delete=models.PROTECT, db_column="id_department", related_name="curators"
    )
    role = models.ForeignKey(
        "Role", on_delete=models.PROTECT, db_column="id_role", related_name="curators"
    )

    email = models.EmailField(max_length=100, db_column="mail", unique=True)
    password = models.TextField(db_column="password")

    mail_mg = models.CharField(
        max_length=100, db_column="mail_mg", null=True, blank=True)
    confirm = models.BooleanField(db_column="confirm", default=False)
    last_login = None

    objects = CuratorManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "curator"
        managed = False
        verbose_name = "Куратор"
        verbose_name_plural = "Кураторы"

    def __str__(self):
        return f"{self.name}"


class Role(models.Model):
    id_role = models.AutoField(primary_key=True, db_column="id_role")
    role = models.CharField(max_length=100, db_column="role")

    class Meta:
        db_table = "role"
        managed = False
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self):
        return self.role


class Department(models.Model):
    id_department = models.AutoField(
        primary_key=True, db_column="id_department")
    department = models.CharField(max_length=10, db_column="department")

    class Meta:
        db_table = "department"
        managed = False
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"

    def __str__(self):
        return self.department


class Subject(models.Model):
    id_subject = models.AutoField(primary_key=True, db_column="id_subject")
    subject = models.CharField(max_length=15, db_column="subject")

    class Meta:
        db_table = "subject"
        managed = False
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    def __str__(self):
        return self.subject


class Status(models.Model):
    id_status = models.AutoField(primary_key=True, db_column="id_status")
    status = models.CharField(max_length=100, db_column="status")

    class Meta:
        db_table = "status"
        managed = False
        verbose_name = "Статус"
        verbose_name_plural = "Статусы"

    def __str__(self):
        return self.status


class Task(models.Model):
    id_task = models.CharField(
        primary_key=True, max_length=100, db_column="id_task")
    deadline = models.DateTimeField(db_column="deadline")
    name = models.CharField(max_length=200, db_column="name")
    description = models.TextField(db_column="description")
    report = models.TextField(db_column="report")
    author = models.ForeignKey(
        Curator,
        to_field="id_tg",
        on_delete=models.PROTECT,
        db_column="id_author",
        related_name="authored_tasks",
    )

    class Meta:
        db_table = "task"
        managed = False
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    def __str__(self):
        return f"{self.id_task}: {self.name}"


class Assignment(models.Model):
    id_assignment = models.AutoField(
        primary_key=True, db_column="id_assignment")

    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, db_column="id_task", related_name="assignments"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        db_column="id_subject",
        related_name="assignments",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column="id_department",
        related_name="assignments",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column="id_role",
        related_name="assignments",
        null=True,
        blank=True,
    )
    curator = models.ForeignKey(
        Curator,
        to_field="id_tg",
        on_delete=models.PROTECT,
        db_column="id_tg",
        related_name="assignments",
        null=True,
        blank=True,
    )
    author = models.ForeignKey(
        Curator,
        to_field="id_tg",
        on_delete=models.PROTECT,
        db_column="id_author",
        related_name="created_assignments",
    )

    class Meta:
        db_table = "assignment"
        managed = False
        verbose_name = "Назначение"
        verbose_name_plural = "Назначения"

    def __str__(self):
        return f"Assignment #{self.id_assignment} for task {self.task_id}"


class Report(models.Model):
    id_report = models.AutoField(primary_key=True, db_column="id_report")

    curator = models.ForeignKey(
        Curator,
        to_field="id_tg",
        on_delete=models.PROTECT,
        db_column="id_tg",
        related_name="reports",
    )
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, db_column="id_task", related_name="reports"
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        db_column="id_status",
        related_name="reports"
    )

    timestamp_start = models.DateTimeField(
        db_column="timestamp_start")
    timestamp_end = models.DateTimeField(
        db_column="timestamp_end", null=True, blank=True)

    report_text = models.TextField(
        db_column="report_text", null=True, blank=True)
    report_url = models.TextField(
        db_column="report_url", null=True, blank=True)

    class Meta:
        db_table = "report"
        managed = False
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"

    def __str__(self):
        return f"Report #{self.id_report} ({self.curator_id} -> {self.task_id})"
