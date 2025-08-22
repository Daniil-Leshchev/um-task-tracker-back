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
        "catalogs.Subject", on_delete=models.PROTECT, db_column="id_subject", related_name="curators"
    )
    department = models.ForeignKey(
        "catalogs.Department", on_delete=models.PROTECT, db_column="id_department", related_name="curators"
    )
    role = models.ForeignKey(
        "catalogs.Role", on_delete=models.PROTECT, db_column="id_role", related_name="curators"
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
