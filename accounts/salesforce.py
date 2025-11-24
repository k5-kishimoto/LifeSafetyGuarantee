# accounts/salesforce.py

import requests
import json
from django.conf import settings
from datetime import datetime
from hashlib import sha256

# 簡易的なSHA256ハッシュ関数
def hash_password(password):
    return sha256(password.encode('utf-8')).hexdigest()

# Salesforce OAuth トークンを取得する関数
def get_auth_token():
    """API接続用のアクセストークンを取得 (APIユーザー認証)"""
    url = f"{settings.SF_INSTANCE_URL}/services/oauth2/token"
    
    if not all([settings.SF_USERNAME, settings.SF_PASSWORD, settings.SF_CLIENT_ID, settings.SF_CLIENT_SECRET]):
        # 環境変数不足の場合はログ出力
        return None, None 

    # payload = {
    #     'grant_type': 'password',
    #     'client_id': settings.SF_CLIENT_ID,
    #     'client_secret': settings.SF_CLIENT_SECRET,
    #     'username': settings.SF_USERNAME,
    #     'password': settings.SF_PASSWORD
    # }
    payload = {
        'grant_type': 'client_credentials', # 💡 ここを変更 💡
        'client_id': settings.SF_CLIENT_ID,
        'client_secret': settings.SF_CLIENT_SECRET,
        # 'scope': 'api' # スコープを指定したい場合は追加 (通常は接続アプリの設定に従う)
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('access_token'), data.get('instance_url')
    except requests.exceptions.RequestException:
        return None, None

# Salesforceにカスタムオブジェクトのレコードを登録する関数
def register_salesforce_contractor(contractor_data):
    """LeavingGuaranteeContractor__c レコードを作成"""
    token, instance_url = get_auth_token()
    if not token:
        return False, "Salesforce認証に失敗しました。"

    api_version = 'v58.0'
    sobject_url = f"{instance_url}/services/data/{api_version}/sobjects/LeavingGuaranteeContractor__c"

    # 日付型フィールドを YYYY-MM-DD 形式の文字列に変換
    birthday_str = contractor_data.get('birthday').strftime('%Y-%m-%d') if contractor_data.get('birthday') else None

    # Salesforceカスタムオブジェクト用のペイロードを構築
    payload = {
        "Name": contractor_data['username'],
        "Password__c": contractor_data['password1'],
        # "Password__c": hash_password(contractor_data['password']), # ハッシュ化されたパスワード
        "LastName__c": contractor_data['last_name'],
        "FirstName__c": contractor_data['first_name'],
        "BusinessName__c": contractor_data['contractor_name'], 
        "Birthday__c": birthday_str, 
        "PropertyName__c": contractor_data['property_name'],
        "RoomName__c": contractor_data['room_name'],
        "Telephone__c": contractor_data['telephone'],
        "Address__c": contractor_data['address'],
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(sobject_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 201:
            return True, "契約者情報の登録に成功しました。"
        else:
            error_data = response.json()
            errors = [err.get('message', '不明なエラー') for err in error_data]
            return False, f"Salesforce登録エラー: {', '.join(errors)}"

    except requests.exceptions.RequestException as e:
        return False, f"Salesforce API接続エラー: {e}"
    
# 💡 Salesforceから契約者情報を取得する関数 💡
def get_contractor_info_by_username(username):
    """ユーザー名に基づいてLeavingGuaranteeContractor__cの情報を取得する"""
    
    token, instance_url = get_auth_token()
    if not token:
        return None 

    api_version = 'v58.0'
    
    # ユーザー名でレコードを検索し、必要なフィールドを取得するSOQL
    soql_query = (
        f"SELECT Id, Name, LastName__c, FirstName__c, BusinessName__c, PropertyName__c, RoomName__c "
        f"FROM LeavingGuaranteeContractor__c "
        f"WHERE Name = '{username}' LIMIT 1"
    )
    
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}'}
    params = {'q': soql_query}

    try:
        response = requests.get(query_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data['totalSize'] == 1:
            # 取得したレコードデータを返す
            record = data['records'][0]
            return {
                'username': record.get('Name'),
                'last_name': record.get('LastName__c'),
                'first_name': record.get('FirstName__c'),
                'contractor_name': record.get('BusinessName__c'),
                'property_name': record.get('PropertyName__c'),
                'room_name': record.get('RoomName__c'),
            }
        
    except requests.exceptions.RequestException as e:
        print(f"Salesforce Data Fetch Error: {e}")
        pass

    return None

# 💡 決済ステータスを更新する関数を追加 💡
def update_contractor_payment_status(username):
    """
    ユーザー名に基づいてLeavingGuaranteeContractor__cの
    PaymentStart__c 項目を True に更新する
    """
    token, instance_url = get_auth_token()
    if not token:
        return False

    api_version = 'v58.0'
    
    # 1. まずユーザー名でレコードID (Id) を取得する
    soql_query = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'q': soql_query}
    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    try:
        # レコード検索
        response = requests.get(query_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data['totalSize'] == 1:
            record_id = data['records'][0]['Id']
            
            # 2. 特定したレコードIDに対して更新 (PATCH) を実行
            update_url = f"{instance_url}/services/data/{api_version}/sobjects/LeavingGuaranteeContractor__c/{record_id}"
            
            payload = {
                "PaymentStart__c": True  # Boolean項目を更新
            }
            
            update_response = requests.patch(update_url, headers=headers, data=json.dumps(payload))
            
            # 204 No Content が返ってくれば成功
            if update_response.status_code == 204:
                return True
            else:
                print(f"Salesforce Update Failed: {update_response.text}")
                return False
        else:
            print(f"User not found in Salesforce: {username}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Salesforce API Error: {e}")
        return False