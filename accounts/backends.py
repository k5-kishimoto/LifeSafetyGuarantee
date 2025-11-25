# accounts/backends.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings
import requests
from .salesforce import get_auth_token, hash_password

User = get_user_model()

class SalesforceBackend(BaseBackend):
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """LeavingGuaranteeContractor__c のレコードとパスワードを検証し、権限を同期する"""
        
        token, instance_url = get_auth_token()
        if not token:
            return None 

        api_version = 'v58.0'
        
        # hashed_password = hash_password(password)
        hashed_password = password

        # 💡 1. SOQLクエリに IsAdmin__c を追加 💡
        soql_query = (
            f"SELECT Id, IsAdmin__c FROM LeavingGuaranteeContractor__c "
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
                # Salesforce上のレコード情報
                record = data['records'][0]
                is_admin_in_sf = record.get('IsAdmin__c', False)

                # 2. Djangoのローカルユーザーを作成/取得
                user, created = User.objects.get_or_create(username=username)
                
                # メールアドレスの同期 (以前の実装)
                if user.email != username:
                    user.email = username

                # 💡 3. 管理者権限の同期 (Salesforce → Django) 💡
                # 毎回ログイン時にSalesforceの状態に合わせて権限を上書きします
                user.is_staff = is_admin_in_sf
                user.is_superuser = is_admin_in_sf
                
                # ユーザーをアクティブ化し、パスワード管理を無効化
                user.set_unusable_password() 
                user.is_active = True
                
                user.save()
                    
                return user 

        except requests.exceptions.RequestException as e:
            print(f"Salesforce Auth Error: {e}")
            pass

        return None 
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None