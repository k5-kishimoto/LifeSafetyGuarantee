# suppliers/backends.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from .salesforce import authenticate_salesforce_agency # 💡 suppliersアプリ内からインポート

class AgencySalesforceBackend(BaseBackend):
    """
    SalesforceのEvictionGuaranteeAgency__cオブジェクトで業者を認証するカスタムバックエンド。
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Salesforce APIで認証
        sf_success = authenticate_salesforce_agency(username, password)

        if sf_success:
            # 2. ローカルにプロキシユーザーを Get または Create
            User = get_user_model()
            
            # is_staff=True をデフォルトに設定
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': username, 'is_staff': True}
            )
            
            # ローカルDBのパスワードは使用不可に設定（Djangoのログイン認証では使用されない）
            if created or not user.has_usable_password():
                user.set_unusable_password()
                user.is_active = True
                user.save()
                
            return user
        
        return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None