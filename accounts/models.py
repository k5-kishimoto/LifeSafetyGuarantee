from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # 既存のフィールド (username, password, email, first_name, last_nameなど) は継承されます
    
    # 新しく追加したいフィールドを定義
    birthday = models.DateField(
        max_length=100,
        verbose_name='誕生日',
        blank=True, # データベースで必須にしない場合
        null=True
    )