# accounts/salesforce.py

import requests
import json
from django.conf import settings
from datetime import datetime
from hashlib import sha256
import html # 💡 これを追加

# 簡易的なSHA256ハッシュ関数
def hash_password(password):
    return sha256(password.encode('utf-8')).hexdigest()
#----------------------------------------
# Salesforce OAuth トークンを取得する関数
#----------------------------------------
def get_auth_token():
    """API接続用のアクセストークンを取得 (APIユーザー認証)"""
    url = f"{settings.SF_INSTANCE_URL}/services/oauth2/token"
    error = ""
    if not all([settings.SF_CLIENT_ID, settings.SF_CLIENT_SECRET]):
        # 環境変数不足の場合はログ出力
        return None, None ,error

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
        return data.get('access_token'), data.get('instance_url'), error
    except requests.exceptions.RequestException as e:
        error = f"Exception: {e}"
        return None, None, error

# Salesforceにカスタムオブジェクトのレコードを登録する関数
def register_salesforce_contractor(contractor_data):
    """LeavingGuaranteeContractor__c レコードを作成"""
    token, instance_url, error = get_auth_token()
    if not token:
        return False, f"Salesforce認証に失敗しました。{error}"

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
        "Supplier__c": contractor_data['contractor_name'], # フォームからはIDが渡される
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
    
    token, instance_url, error = get_auth_token()
    if not token:
        return None 

    api_version = 'v58.0'
    
    # ユーザー名でレコードを検索し、必要なフィールドを取得するSOQL
    soql_query = (
        f"SELECT Id, Name, LastName__c, FirstName__c, PropertyName__c, RoomName__c, PaymentStart__c "
        f"FROM LeavingGuaranteeContractor__c "
        f"WHERE Name = '{username}' and IsMovedOut__c = False LIMIT 1"
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
                'payment_start': record.get('PaymentStart__c'),
            }
        
    except requests.exceptions.RequestException as e:
        print(f"Salesforce Data Fetch Error: {e}")
        pass

    return None

# ---------------------------------------
# 💡 Web Push購読情報を「追加」する関数 
# ---------------------------------------💡
def get_salesforce_webpush_subscriptions(username):
    """
    指定ユーザー(username)に紐づく GuaranteeWebNotification__c のレコードを取得する
    """
    token, instance_url, _ = get_auth_token() # 簡易アンパック
    if not token: return []

    api_version = 'v58.0'
    headers = {'Authorization': f'Bearer {token}'}
    query_url = f"{instance_url}/services/data/{api_version}/query"

    try:
        # 1. まずユーザー(Contractor)のIDを取得
        soql_user = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
        res_user = requests.get(query_url, headers=headers, params={'q': soql_user})
        data_user = res_user.json()
        
        if data_user['totalSize'] == 0:
            return []
            
        user_id = data_user['records'][0]['Id']

        # 2. そのユーザーに紐づくサブスクリプションを取得
        # (Contractor__c が参照項目である前提)
        soql_sub = (
            f"SELECT EndpointUrl__c, P256dh__c, Auth__c "
            f"FROM GuaranteeWebNotification__c "
            f"WHERE Contractor__c = '{user_id}'"
        )
        
        res_sub = requests.get(query_url, headers=headers, params={'q': soql_sub})
        data_sub = res_sub.json()
        
        return data_sub.get('records', [])

    except Exception as e:
        print(f"Salesforce Subscription Fetch Error: {e}")
        return []
    
# accounts/salesforce.py

import requests
import json
from django.conf import settings

# ... (get_auth_token 関数はそのまま) ...

def add_salesforce_webpush_subscription(username, subscription_data, user_agent):
    """
    WebPushの購読情報をSalesforceに保存する。
    長すぎるEndpoint対策として、ユーザーIDで検索してからPython側で判定を行う。
    """
    auth_result = get_auth_token()
    
    # トークン取得チェック
    if not auth_result or auth_result[0] is None:
        print("SF Save Error: Authentication failed.")
        return False

    if len(auth_result) == 3:
        token, instance_url, _ = auth_result
    else:
        token, instance_url = auth_result

    api_version = 'v58.0'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        # 1. ユーザー(Contractor)のIDを取得
        soql_user = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
        query_url = f"{instance_url}/services/data/{api_version}/query"
        
        res_user = requests.get(query_url, headers=headers, params={'q': soql_user})
        res_user.raise_for_status() # エラーならここで停止
        data_user = res_user.json()

        if data_user['totalSize'] == 0:
            print(f"Save Subscription Error: User {username} not found.")
            return False

        user_id = data_user['records'][0]['Id']

        # 送信されたデータ
        new_endpoint = subscription_data.get('endpoint')
        keys = subscription_data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        # 2. ユーザーに紐づく既存の購読をすべて取得 (EndpointUrl__cで絞り込まない)
        # 💡 ここで長いEndpointをWHERE句に使わないのがポイント 💡
        soql_check = f"SELECT Id, EndpointUrl__c FROM GuaranteeWebNotification__c WHERE Contractor__c = '{user_id}'"
        
        res_check = requests.get(query_url, headers=headers, params={'q': soql_check})
        res_check.raise_for_status() # エラーチェック
        data_check = res_check.json()

        # 3. Python側でEndpointの一致を確認
        existing_record_id = None
        
        if data_check['totalSize'] > 0:
            for record in data_check['records']:
                # DBの値と、今回送られてきた値を比較
                if record.get('EndpointUrl__c') == new_endpoint:
                    existing_record_id = record['Id']
                    break

        # 保存用ペイロード
        payload = {
            "Contractor__c": user_id,
            "EndpointUrl__c": new_endpoint,
            "P256dh__c": p256dh,
            "Auth__c": auth,
            "UserAgent__c": user_agent[:255] if user_agent else "Unknown"
        }

        if existing_record_id:
            # 4A. 更新 (Update)
            print(f"Existing subscription found (ID: {existing_record_id}). Updating...")
            update_url = f"{instance_url}/services/data/{api_version}/sobjects/GuaranteeWebNotification__c/{existing_record_id}"
            res_update = requests.patch(update_url, headers=headers, data=json.dumps(payload))
            res_update.raise_for_status()
            print(f"WebPush Subscription Updated for {username}")
        else:
            # 4B. 新規作成 (Create)
            print("No matching subscription found. Creating new...")
            create_url = f"{instance_url}/services/data/{api_version}/sobjects/GuaranteeWebNotification__c"
            res_create = requests.post(create_url, headers=headers, data=json.dumps(payload))
            
            if res_create.status_code == 201:
                print(f"WebPush Subscription Created for {username}")
            else:
                print(f"SF Create Error: {res_create.text}")
                return False

        return True

    except Exception as e:
        print(f"Add Subscription Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
#-----------------------------------------
# 💡 全てのWeb Push購読情報を取得する関数 💡
#-----------------------------------------
def get_all_webpush_subscriptions(username):
    """
    ユーザーに紐づく全ての GuaranteeWebNotification__c を取得する
    戻り値: [{'sf_id': '...', 'info': {...}}, ...] のリスト
    """
    token, instance_url, error = get_auth_token()
    if not token:
        return []

    api_version = 'v58.0'
    
    # 子リレーションを使って一括取得するか、Contractor__r.Name でフィルタする
    soql_query = (
        f"SELECT Id, SubscriptionJson__c FROM GuaranteeWebNotification__c "
        f"WHERE Contractor__r.Name = '{username}'"
    )
    
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(query_url, headers=headers, params={'q': soql_query})
        data = response.json()
        
        subscriptions = []
        for record in data.get('records', []):
            json_str = record.get('SubscriptionJson__c')
            if json_str:
                try:
                    # 💡 修正箇所: json.loads() の前に HTML デコードを追加 💡
                    decoded_json_str = html.unescape(json_str) 

                    subscriptions.append({
                        'sf_id': record['Id'], 
                        'info': json.loads(decoded_json_str) # デコード後の文字列を使用
                    })
                except json.JSONDecodeError as e:
                    # (デバッグ出力はそのまま)
                    print("--------------------------------------------------")
                    print(f"JSON Decode Error: {e}")
                    print(f"FAULTY JSON STRING (Subscription): {json_str[:200]}...")
                    print("--------------------------------------------------")
                    pass  
        return subscriptions

    except Exception as e:
        print(f"Salesforce WebPush Fetch Error: {e}")
        return []

#--------------------------------------------------------
# 💡 無効な購読情報を削除する関数 (通知送信エラー時に使用) 💡
#--------------------------------------------------------
def delete_webpush_subscription(sf_id):
    token, instance_url, error = get_auth_token()
    if not token: return
    
    api_version = 'v58.0'
    delete_url = f"{instance_url}/services/data/{api_version}/sobjects/GuaranteeWebNotification__c/{sf_id}"
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        requests.delete(delete_url, headers=headers)
        print(f"Deleted invalid subscription: {sf_id}")
    except Exception as e:
        print(f"Delete Error: {e}")

#-------------Web push End ------------------------------

# 💡 1. メッセージを送信（Salesforceに保存）する関数 💡
def create_salesforce_message(username, subject, body):
    """
    Contractorに対してメッセージレコードを作成する
    """
    token, instance_url, error = get_auth_token()
    if not token: return False

    api_version = 'v58.0'
    
    # 親レコード(Contractor)のIDを取得
    soql_query = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    try:
        # ID検索
        res = requests.get(query_url, headers=headers, params={'q': soql_query})
        data = res.json()
        
        if data['totalSize'] == 1:
            contractor_id = data['records'][0]['Id']
            
            # メッセージレコード作成
            create_url = f"{instance_url}/services/data/{api_version}/sobjects/GuaranteeMessage__c"
            payload = {
                "Contractor__c": contractor_id,
                "Subject__c": subject,
                "Body__c": body,
                "IsRead__c": False
            }
            res_create = requests.post(create_url, headers=headers, data=json.dumps(payload))
            return res_create.status_code == 201
            
    except Exception as e:
        print(f"Message Create Error: {e}")
        return False
    
    return False

# 💡 2. メッセージ一覧を取得する関数 💡
def get_contractor_messages(username):
    """
    ユーザー宛のメッセージを新しい順に取得する
    """
    token, instance_url, error = get_auth_token()
    if not token: return []

    api_version = 'v58.0'
    
    # 子リレーションを使うか、Contractor__r.Nameで検索
    # CreatedDate (作成日) も取得
    soql_query = (
        f"SELECT Id, Subject__c, Body__c, CreatedDate, IsRead__c "
        f"FROM GuaranteeMessage__c "
        f"WHERE Contractor__r.Name = '{username}' "
        f"ORDER BY CreatedDate DESC LIMIT 50"
    )
    
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        res = requests.get(query_url, headers=headers, params={'q': soql_query})
        data = res.json()
        return data.get('records', [])
    except Exception as e:
        print(f"Message Fetch Error: {e}")
        return []
    
    # 💡 全ユーザー（契約者）を取得する関数 💡
def get_all_contractors():
    """
    LeavingGuaranteeContractor__c から全レコードのIDとユーザー名を取得する
    """
    token, instance_url, error = get_auth_token()
    if not token: return []

    api_version = 'v58.0'
    
    # IDとName(ユーザー名)を取得
    soql_query = "SELECT Id, Name FROM LeavingGuaranteeContractor__c WHERE isAdmin__c = FALSE"
    
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        # ※ レコード数が多い場合、本来はnextRecordsUrlを使ったページング処理が必要ですが
        # ここでは簡易的に1回のリクエストで取得できる範囲(最大2000件)とします。
        response = requests.get(query_url, headers=headers, params={'q': soql_query})
        data = response.json()
        return data.get('records', [])
        
    except Exception as e:
        print(f"Fetch All Contractors Error: {e}")
        return []

# 💡 ID指定でメッセージを作成する関数 (高速化のため) 💡
# 既存の create_salesforce_message はユーザー名からIDを検索してしまうため、
# すでにIDがわかっている一括送信では、直接IDを指定する関数があるとAPI消費を減らせます。
def create_message_by_sf_id(contractor_id, subject, body):
    token, instance_url, error = get_auth_token()
    if not token: return False
    api_version = 'v58.0'

    create_url = f"{instance_url}/services/data/{api_version}/sobjects/GuaranteeMessage__c"
    payload = {
        "Contractor__c": contractor_id,
        "Subject__c": subject,
        "Body__c": body,
        "IsRead__c": False
    }
    
    try:
        res = requests.post(create_url, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, data=json.dumps(payload))
        return res.status_code == 201
    except:
        return False
    
# 💡 パスワード更新関数 (修正版) 💡
def update_salesforce_password(username, new_hashed_password, return_error=False):
    """
    SalesforceのLeavingGuaranteeContractor__cのPassword__cを更新する
    """
    # get_auth_tokenの戻り値に合わせて展開
    auth_result = get_auth_token()
    if len(auth_result) == 3:
        token, instance_url, auth_error = auth_result
    else:
        token, instance_url = auth_result
        auth_error = "Unknown Auth Error"

    if not token: 
        return (False, auth_error) if return_error else False

    api_version = 'v58.0'
    
    # 💡 修正箇所: 必ずコロン (:) を使って辞書として定義する 💡
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        # 1. ID取得
        soql_query = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
        query_url = f"{instance_url}/services/data/{api_version}/query"
        
        response = requests.get(query_url, headers=headers, params={'q': soql_query})
        
        # エラーチェック
        if response.status_code != 200:
             msg = f"Search Query Failed: {response.text}"
             print(msg)
             return (False, msg) if return_error else False

        data = response.json()

        if data['totalSize'] == 1:
            record_id = data['records'][0]['Id']
            
            # 2. パスワード更新実行 (PATCH)
            update_url = f"{instance_url}/services/data/{api_version}/sobjects/LeavingGuaranteeContractor__c/{record_id}"
            
            payload = {
                "Password__c": new_hashed_password 
            }
            
            update_res = requests.patch(update_url, headers=headers, data=json.dumps(payload))
            
            if update_res.status_code == 204: # 204 No Content が成功
                return (True, "") if return_error else True
            else:
                error_detail = update_res.text
                print(f"Salesforce Password PATCH Failed: {error_detail}")
                return (False, error_detail) if return_error else False
        
        else:
            msg = f"User '{username}' not found in Salesforce."
            print(msg)
            return (False, msg) if return_error else False

    except Exception as e:
        print(f"Salesforce Password Update Error: {e}")
        return (False, str(e)) if return_error else False
    
def get_all_agencies_for_choices():
    """EvictionGuaranteeAgency__c の全レコードを取得し、フォームの選択肢として返す"""
    
    token, instance_url, auth_error = get_auth_token()
    if not token: 
        print(f"Agency Choice Fetch Error: {auth_error}")
        return []

    api_version = 'v58.0'
    
    # 💡 SOQL: Name (表示名) と Id を取得 💡
    soql_query = "SELECT Id, Name FROM EvictionGuaranteeAgency__c ORDER BY Name"
    query_url = f"{instance_url}/services/data/{api_version}/query"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(query_url, headers=headers, params={'q': soql_query})
        response.raise_for_status()
        data = response.json()
        
        choices = [('', '--- 業者名を選択してください ---')]
        
        for record in data.get('records', []):
            # フォームの選択肢形式 (値, 表示ラベル)
            # 値には Salesforce ID (Id) を使い、表示ラベルに Name を使います
            choices.append((record['Id'], record['Name']))
            
        return choices

    except Exception as e:
        print(f"Salesforce Agency Fetch Error: {e}")
        # API接続失敗時も空の選択肢を返せるよう、初期値の選択肢を返します
        return [('', '--- 業者名を取得できませんでした ---')]
    

# 💡 決済ステータスを更新する関数を追加 💡
def update_contractor_payment_status(username, is_paying, isend):
    """
    ユーザー名に基づいてLeavingGuaranteeContractor__cの
    PaymentStart__c 項目を True に更新する
    """
    token, instance_url, error = get_auth_token()
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
    now_str = datetime.now().strftime('%Y-%m-%d')
    try:
        # レコード検索
        response = requests.get(query_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data['totalSize'] == 1:
            record_id = data['records'][0]['Id']
            
            # 2. 特定したレコードIDに対して更新 (PATCH) を実行
            update_url = f"{instance_url}/services/data/{api_version}/sobjects/LeavingGuaranteeContractor__c/{record_id}"
            
            if is_paying:
                payload = {
                    "PaymentStart__c": True,
                    "Paying__c": is_paying,  # Boolean項目を更新
                    "MoveInDate__c" : now_str
                }

            else:
                if isend:
                    payload = {
                        "Paying__c": is_paying,
                        "IsMovedOut__c": isend,
                        "MovedOutDate__c" : now_str
                    }
                else:
                    payload = {
                        "Paying__c": is_paying,
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


def update_salesforce_stripe_info(username, customer_id, subscription_id):
    """
    Stripeの顧客IDとサブスクリプションIDをSalesforceに保存し、
    支払い開始フラグ(PaymentStart__c)をTrueにする
    """
    auth_result = get_auth_token()
    # トークン取得処理... (省略)
    token, instance_url = auth_result[:2] # 簡易記述

    if not token: return False

    api_version = 'v58.0'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    try:
        now_str = datetime.now().strftime('%Y-%m-%d')
        # ID取得
        soql = f"SELECT Id FROM LeavingGuaranteeContractor__c WHERE Name = '{username}' LIMIT 1"
        query_url = f"{instance_url}/services/data/{api_version}/query"
        res = requests.get(query_url, headers=headers, params={'q': soql})
        data = res.json()

        if data['totalSize'] == 1:
            record_id = data['records'][0]['Id']
            
            # 更新
            update_url = f"{instance_url}/services/data/{api_version}/sobjects/LeavingGuaranteeContractor__c/{record_id}"
            payload = {
                "StripeCustomerId__c": customer_id,
                "StripeSubscriptionId__c": subscription_id,
                "PaymentStart__c": True,
                "Paying__c": True,
                "MoveInDate__c" : now_str
            }
            requests.patch(update_url, headers=headers, data=json.dumps(payload))
            return True
            
        return False
    except Exception as e:
        print(f"SF Update Error: {e}")
        return False