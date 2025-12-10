# suppliers/salesforce.py

import requests
import json
from django.conf import settings

# 💡 Client Credentials Flow認証トークンを取得する関数 (既存ロジックを流用)
def get_auth_token():
    """API接続用のアクセストークンを取得する"""
    url = f"{settings.SF_INSTANCE_URL}/services/oauth2/token"
    
    if not all([settings.SF_CLIENT_ID, settings.SF_CLIENT_SECRET, settings.SF_INSTANCE_URL]):
        return None, None, "Salesforce Client credentials missing."

    payload = {
        'grant_type': 'client_credentials',
        'client_id': settings.SF_CLIENT_ID,
        'client_secret': settings.SF_CLIENT_SECRET,
    }

    try:
        response = requests.post(url, data=payload)
        # ネットワークエラーや4xx, 5xxエラーをキャッチするためにraise_for_status()を使用
        response.raise_for_status() 
        data = response.json()
        return data.get('access_token'), data.get('instance_url'), ""
    except requests.exceptions.RequestException as e:
        return None, None, str(e)


def authenticate_salesforce_agency(username, password):
    """
    EvictionGuaranteeAgency__cオブジェクトのNameとPassword__cで認証を行う。
    """
    auth_result = get_auth_token()
    token, instance_url, auth_error = auth_result
        
    if not token: 
        print(f"Agency Auth Token Failed: {auth_error}")
        return False
    
    api_version = 'v58.0'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        # 💡 SOQLでNameとPassword__cを検索 💡
        # 🚨 パスワードはSalesforce側で平文保存・比較が前提
        soql_query = (
            f"SELECT Name FROM EvictionGuaranteeAgency__c "
            f"WHERE Username__c = '{username}' AND Password__c = '{password}' LIMIT 1"
        )
        query_url = f"{instance_url}/services/data/{api_version}/query"
        
        response = requests.get(query_url, headers=headers, params={'q': soql_query})
        data = response.json()

        if response.status_code == 200 and data.get('totalSize') == 1:
            return True
        
        print(f"Agency user {username} not found or password incorrect.")
        return False

    except Exception as e:
        print(f"Agency Authentication Error: {e}")
        return False
    
def get_contractors_for_agency(agency_username):
    """
    AgencyのName (username) を元に、紐づくLeavingGuaranteeContractor__cのリストを取得する。
    """
    auth_result = get_auth_token()
    token, instance_url, auth_error = auth_result[:3] if len(auth_result) >= 3 else (auth_result[0], auth_result[1], "Unknown Error")
    
    if not token: 
        print(f"Contractor Fetch Error (Auth): {auth_error}")
        return []

    api_version = 'v58.0'
    headers = {'Authorization': f'Bearer {token}'}
    query_url = f"{instance_url}/services/data/{api_version}/query"

    try:
        print(f"業者名:{agency_username}")
        # 1. AgencyのNameからSalesforce IDを取得
        soql_agency = f"SELECT Id FROM EvictionGuaranteeAgency__c WHERE Username__c = '{agency_username}' LIMIT 1"
        response_agency = requests.get(query_url, headers=headers, params={'q': soql_agency})
        response_agency.raise_for_status()
        data_agency = response_agency.json()
        
        if data_agency.get('totalSize') == 0:
            print(f"Agency '{agency_username}' not found in Salesforce.")
            return []
        
        agency_id = data_agency['records'][0]['Id']

        print(f"業者ID:{agency_id}")
        # 2. 取得したAgency IDを使って、紐づくContractorを取得 (Supplier__cでフィルタ)
        # 💡 表示したいフィールドを SOQL で指定します 💡
        soql_contractors = (
            f"SELECT Name, Fullname__c, PropertyName__c, RoomName__c, Telephone__c, MoveInDate__c, PaymentStart__c, IsMovedOut__c, MovedOutDate__c, IsCancel__c, AssurancePrice__c, CumulativeOccupancyMonths__c "
            f"FROM LeavingGuaranteeContractor__c "
            f"WHERE Supplier__c = '{agency_id}' AND IsAssurancePaying__c = False "
            f"ORDER BY PropertyName__c DESC"
        )
        
        response_contractors = requests.get(query_url, headers=headers, params={'q': soql_contractors})
        response_contractors.raise_for_status()
        data_contractors = response_contractors.json()
        
        contractors = []
        for record in data_contractors.get('records', []):
            contractors.append({
                # Nameは契約者のユーザー名として使用されることが多いため、IDとして利用
                'id': record['Name'], 
                'full_name': record.get('Fullname__c', 'N/A'),
                'property_name': record.get('PropertyName__c', 'N/A'),
                'room_name': record.get('RoomName__c', 'N/A'),
                'telephone': record.get('Telephone__c', 'N/A'),
                'move_in_date': record.get('MoveInDate__c'),
                'paying': record.get('PaymentStart__c'),
                'is_moved_out': record.get('IsMovedOut__c'),
                'move_out_date': record.get('MovedOutDate__c'),
                'is_cancel': record.get('IsCancel__c'),
                'months': record.get('CumulativeOccupancyMonths__c'),
                'assurance_price': record.get('AssurancePrice__c'),
            })
            
        return contractors

    except requests.exceptions.RequestException as e:
        print(f"Salesforce Request Error: {e}")
        return []
    except Exception as e:
        print(f"Salesforce Contractor Fetch Error: {e}")
        return []
    
def register_salesforce_agency(agency_data):
    """EvictionGuaranteeAgency__c レコードを作成 (業者サインアップ)"""
    
    auth_result = get_auth_token()
    token, instance_url, error = auth_result
    if not token:
        return False, f"Salesforce認証に失敗しました。{error}"

    api_version = 'v58.0'
    sobject_url = f"{instance_url}/services/data/{api_version}/sobjects/EvictionGuaranteeAgency__c"

    # 💡 パスワードはPassword__cに平文で格納 💡
    payload = {
        "Username__c": agency_data['username'],
        "Password__c": agency_data['password1'], 
        "Name": agency_data['agency_name'],
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(sobject_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 201:
            return True, "業者アカウントの登録に成功しました。"
        else:
            error_data = response.json()
            errors = [err.get('message', '不明なエラー') for err in error_data]
            return False, f"Salesforce登録エラー: {', '.join(errors)}"

    except requests.exceptions.RequestException as e:
        return False, f"Salesforce API接続エラー: {e}"