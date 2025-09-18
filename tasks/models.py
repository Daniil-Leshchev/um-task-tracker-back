from django.db import models
from users.models import Curator


class Task(models.Model):
    id_task = models.CharField(
        primary_key=True, max_length=100, db_column="id_task")
    deadline = models.DateTimeField(db_column="deadline")
    name = models.CharField(max_length=200, db_column="name")
    description = models.TextField(db_column="description")
    report = models.TextField(db_column="report")
    author = models.ForeignKey(
        Curator,
        to_field="email",
        on_delete=models.PROTECT, # если удалим автора задачи – сотрется история выполнения по определенной задаче, но это поле not null
        db_column="mail_author",
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
        'catalogs.Subject',
        on_delete=models.PROTECT,
        db_column="id_subject",
        related_name="assignments",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        'catalogs.Department',
        on_delete=models.PROTECT,
        db_column="id_department",
        related_name="assignments",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        'catalogs.Role',
        on_delete=models.PROTECT,
        db_column="id_role",
        related_name="assignments",
        null=True,
        blank=True,
    )
    curator = models.ForeignKey(
        'users.Curator',
        to_field="email",
        on_delete=models.CASCADE,
        db_column="mail",
        related_name="assignments",
        null=True,
        blank=True,
    )
    author = models.ForeignKey(
        'users.Curator',
        to_field="email",
        on_delete=models.CASCADE,
        db_column="mail_author",
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
        'users.Curator',
        to_field="email",
        on_delete=models.CASCADE,
        db_column="mail",
        related_name="reports",
    )
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, db_column="id_task", related_name="reports"
    )
    status = models.ForeignKey(
        'catalogs.Status',
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
        return f"Report #{self.id_report} (curator mail: {self.curator_id} -> task {self.task_id})"
