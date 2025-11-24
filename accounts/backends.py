# accounts/backends.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings
import requests
from .salesforce import get_auth_token, hash_password

User = get_user_model()

class SalesforceBackend(BaseBackend):
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """LeavingGuaranteeContractor__c のレコードとパスワードを検証する"""
        
        token, instance_url = get_auth_token()
        if not token:
            return None 

        api_version = 'v58.0'
        
        # ユーザーが入力したパスワードをハッシュ化
        # hashed_password = hash_password(password)
        hashed_password = password
        
        # SOQLでユーザー名とハッシュ化されたパスワードを検索
        soql_query = (
            f"SELECT Id FROM LeavingGuaranteeContractor__c "
            f"WHERE Name = '{username}' AND Password__c = '{hashed_password}' LIMIT 1"
        )
        
        query_url = f"{instance_url}/services/data/{api_version}/query"
        headers = {'Authorization': f'Bearer {token}'}
        params = {'q': soql_query}

        try:
            response = requests.get(query_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data['totalSize'] == 1:
                # 認証成功の場合
                
                # 2. Djangoのローカルユーザーを作成/取得 (プロキシとして)
                try:
                    user = User.objects.get(username=username)
                    # 💡 ユーザーが存在する場合でもメールアドレスを更新 💡
                    if user.email != username:
                        user.email = username
                        user.save()
                        
                except User.DoesNotExist:
                    # ローカルDBに存在しない場合、プロキシユーザーを作成
                    user = User.objects.create_user(
                        username=username, 
                        email=username # 💡 ここでメールアドレスを設定 💡
                    )
                    user.set_unusable_password() 
                    user.is_active = True
                    user.save()
                    
                return user # 認証に成功したDjangoユーザーを返す

        except requests.exceptions.RequestException:
            pass

        return None 
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None