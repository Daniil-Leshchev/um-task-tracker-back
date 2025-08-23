from django.db import models


class Role(models.Model):
    id_role = models.AutoField(primary_key=True, db_column="id_role")
    role = models.CharField(max_length=100, db_column="role")

    class Meta:
        db_table = "role"
        managed = False
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ('id_role',)

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
        ordering = ('id_department',)

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
        ordering = ('id_subject',)

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
        ordering = ('id_status',)

    def __str__(self):
        return self.status
