import json
from django.conf import settings
from pywebpush import webpush, WebPushException

# Salesforce連携関数をインポート
# (salesforce.py に get_salesforce_webpush_subscriptions 関数が必要です。後述します)
from .salesforce import get_salesforce_webpush_subscriptions

def send_push_notification_to_user(user, title, body, message_id=None):
    """
    指定されたユーザーの登録済みデバイスすべてにWeb Push通知を送信する。
    
    Args:
        user: Djangoのユーザーオブジェクト
        title: 通知のタイトル
        body: 通知の本文
        message_id: (Optional) モーダル表示用にSalesforceのメッセージIDを含める
    """
    username = user.username
    
    # 1. Salesforceから有効な購読情報を取得
    # (WebPushSubscription__c オブジェクトのレコードリスト)
    subscriptions = get_salesforce_webpush_subscriptions(username)
    
    if not subscriptions:
        # 購読情報がない場合はログを出して終了（エラーにはしない）
        print(f"No push subscriptions found for user: {username}")
        return False, "有効なプッシュ通知購読が見つかりません。"

    # VAPID設定の読み込み
    vapid_private_key = settings.VAPID_PRIVATE_KEY
    vapid_claims = {
        "sub": settings.VAPID_ADMIN_EMAIL
    }

    # 2. 通知ペイロードの作成
    # dataフィールドに message_id を含めることで、通知タップ時にJSで取得可能にします
    payload = {
        "head": title,
        "body": body,
        "icon": "/static/images/icon-192.png", # 必要に応じてアイコン画像のパスを指定
        "data": {
            "url": "/", # デフォルトの遷移先URL（ServiceWorkerで制御可能）
            "message_id": message_id # 💡 モーダル表示用のID
        }
    }

    success_count = 0
    failure_count = 0

    # 3. 各デバイス（サブスクリプション）へ送信
    for sub in subscriptions:
        # Salesforceの WebPushSubscription__c オブジェクトのフィールド名を使用
        endpoint = sub.get('Endpoint__c')
        p256dh = sub.get('P256dh__c')
        auth = sub.get('Auth__c')
        
        # 必須情報が欠けている場合はスキップ
        if not all([endpoint, p256dh, auth]):
            continue

        # pywebpush 用の形式に整形
        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": p256dh,
                "auth": auth
            }
        }

        try:
            # 送信実行
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            success_count += 1
            
        except WebPushException as ex:
            print(f"WebPush Error for {username}: {ex}")
            # 例: 410 Gone (購読が無効) の場合は、将来的にSalesforceから削除する処理を入れても良い
            failure_count += 1
            
    if success_count > 0:
        return True, f"{success_count}台のデバイスに通知を送信しました。"
    else:
        return False, "通知の送信に失敗しました（有効な送信先がありません）。"