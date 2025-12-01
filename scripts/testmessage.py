# testmessage.py

from django.contrib.auth import get_user_model
from accounts.utils import send_push_notification_to_user

# スクリプトのエントリポイントを定義
def run():
    User = get_user_model()
    
    # 💡 ユーザー名をここで設定してください 💡
    target_username = 'test1@test.com' 

    try:
        # 1. ユーザーの取得
        user = User.objects.get(username=target_username) 

        # 2. 通知を送信
        success, message = send_push_notification_to_user(
            user, 
            title="🎉 購読テスト成功 🎉", 
            body="Salesforce経由のWeb Pushが届きました！"
        )

        print(f"送信結果: {message}")
        
    except User.DoesNotExist:
        print(f"エラー: ローカルユーザー '{target_username}' が見つかりません。ユーザー名を確認してください。")
        
    except Exception as e:
        print(f"送信中に予期せぬエラーが発生しました: {e}")

if __name__ == '__main__':
    run()