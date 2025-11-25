# accounts/utils.py

from pywebpush import webpush, WebPushException
from django.conf import settings
import json
# 💡 新しい関数をインポート 💡
from .salesforce import get_all_webpush_subscriptions, delete_webpush_subscription

def send_push_notification_to_user(user, title, body):
    """ユーザーの全デバイスに通知を送信"""
    
    # 💡 全デバイスの購読情報を取得 💡
    subscriptions = get_all_webpush_subscriptions(user.username)
    
    if not subscriptions:
        return False, "No subscriptions found."

    data = json.dumps({'title': title, 'body': body})
    vapid_claims = {"sub": settings.VAPID_ADMIN_EMAIL}

    success_count = 0
    
    for sub in subscriptions:
        sub_info = sub['info']
        sf_id = sub['sf_id']
        
        try:
            webpush(
                subscription_info=sub_info,
                data=data,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_public_key=settings.VAPID_PUBLIC_KEY,
                vapid_claims=vapid_claims
            )
            success_count += 1
            
        except WebPushException as e:
            # 💡 エラーコード 410 (Gone) や 404 は、購読が無効になっているため削除 💡
            if e.response is not None and e.response.status_code in [404, 410]:
                print(f"Subscription expired. Deleting: {sf_id}")
                delete_webpush_subscription(sf_id)
            else:
                print(f"Push failed for {sf_id}: {e}")
            
    return True, f"Sent to {success_count}/{len(subscriptions)} devices"