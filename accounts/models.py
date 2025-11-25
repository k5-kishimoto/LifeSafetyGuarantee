from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import models
from django.conf import settings

class WebPushSubscription(models.Model):
    """
    Web Push通知用の購読情報を管理するモデル
    1人のユーザーが複数のデバイス（PC, スマホなど）で購読する可能性があるため、
    Userモデルとは 1対多 (ForeignKey) の関係にします。
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webpush_subscriptions'
    )

    # 💡 重要: ブラウザから送られてくる {endpoint, keys: {p256dh, auth}} をそのまま格納
    # SQLite, PostgreSQL, MySQL(5.7+) で使用可能です
    subscription_info = models.JSONField(verbose_name='購読情報')

    # (オプション) どのブラウザ/デバイスか識別しやすくするためのフィールド
    user_agent = models.CharField(
        verbose_name='ブラウザ情報',
        max_length=500,
        blank=True, 
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    def __str__(self):
        return f"{self.user} ({self.created_at.strftime('%Y-%m-%d')})"

class CustomUser(AbstractUser):
    # 既存のフィールド (username, password, email, first_name, last_nameなど) は継承されます
    
    # 新しく追加したいフィールドを定義
    birthday = models.DateField(
        max_length=100,
        verbose_name='誕生日',
        blank=True, # データベースで必須にしない場合
        null=True
    )