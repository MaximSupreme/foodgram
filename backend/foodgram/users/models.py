from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import (
    MAX_LENGTH_USER_BIO_INFO,
    MAX_STRING_CHAR, ROLE_ADMIN, ROLE_USER,
    MAX_ROLE_LENGTH, ROLES
)


class CustomUser(AbstractUser):
    username = models.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO, unique=True,
    )
    email = models.EmailField(
        max_length=MAX_STRING_CHAR, unique=True,
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO,
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_USER_BIO_INFO,
    )
    bi0 = models.CharField(
        max_length = MAX_STRING_CHAR,
    )
    role = models.CharField(
        max_length=MAX_ROLE_LENGTH, choices=ROLES, default=ROLE_USER,
    )
    confirmation_code = models.CharField(
        max_length=MAX_STRING_CHAR, blank=True, null=True
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True, null=True,
    )

    REQUIRED_FIELDS = ('email',)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN or self.is_superuser
