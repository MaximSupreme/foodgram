from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import MAX_STRING_CHAR


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=MAX_STRING_CHAR,
        unique=True,
        verbose_name='Адрес электронной почты.'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар.'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username
