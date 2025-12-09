# accounts/stripe_utils.py (新規作成)

import stripe
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
import json # JSONFieldの処理のために必要かもしれません
from django.contrib.auth import get_user_model

# 💡 新規追加: Checkout Session作成関数 💡
def create_subscription_checkout_session(user, request_host_url):
    """
    指定されたユーザーに対してStripe Checkout Sessionを作成する。
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # settingsから価格IDを取得
    stripe_price_id = settings.STRIPE_SUBSCRIPTION_PRICE_ID 

    # リダイレクトURLの生成 (views.pyから移動)
    success_url = request_host_url + reverse('home') + '?payment=success'
    cancel_url = request_host_url + reverse('home') + '?payment=cancelled'

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': stripe_price_id,
                    'quantity': 1,
                }
            ],
            mode='subscription', 
            
            success_url=success_url,
            cancel_url=cancel_url,
            # user.emailが username (メール形式) である前提
            customer_email=user.email if user.email else None, 
            metadata={'user_id': user.id},
        )
        
        # 成功した場合、Stripeの決済URLを返す
        return True, checkout_session.url
        
    except Exception as e:
        # 失敗した場合、エラーメッセージを返す
        return False, f"決済セッションの作成に失敗しました: {e}"

# Djangoユーザーに関連づけられた Stripe Subscription ID を取得する関数を定義
# (ここでは、ユーザー名から Salesforce を経由して Subscription ID を取得すると仮定)
# 🚨 実際のプロジェクトでは、ローカルDBのユーザーに直接 Stripe Customer ID と Subscription ID を保存することを推奨します。

def get_latest_subscription_id(username):
    """
    ユーザーの最新の有効なサブスクリプションIDをStripeから取得（簡易版）
    注：ローカルDBに顧客ID(cus_...)を保存していないため、この関数は複雑になる
    """
    # 実際には、ローカルDBの user.stripe_customer_id を使用すべきですが、
    # 今はローカルDBに情報がないため、デモとして適当なSubscription IDを返すか、
    # ユーザーのメールアドレス/ユーザー名からCustomer IDを検索するロジックが必要です。
    
    # 💡 ユーザーのメールアドレス（ユーザー名）でStripe顧客を検索するロジックを実装 💡
    try:
        customers = stripe.Customer.list(email=username, limit=1)
        if not customers or not customers.data:
            return None, "Customer not found on Stripe."
            
        customer_id = customers.data[0].id
        
        subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1)
        if not subscriptions or not subscriptions.data:
            return None, "Active subscription not found."
            
        return subscriptions.data[0].id, "" # Subscription IDを返す
        
    except Exception as e:
        return None, f"Stripe Search Error: {e}"

def cancel_stripe_subscription(username):
    """
    ユーザー名に紐づくアクティブなサブスクリプションをキャンセルし、Salesforceを更新する。
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    subscription_id, error = get_latest_subscription_id(username)
    
    if not subscription_id:
        return False, f"Stripe: {error}"
    
    try:
        # サブスクリプションのキャンセル実行 (at_period_end=Trueで期間末に解約)
        stripe.Subscription.cancel(
            subscription_id,
            # at_period_end=True # 期間末にキャンセルする場合はこれを設定
        )
        
        # サービス解約フラグを立てるためにSalesforce連携関数を呼び出す
        # 💡 SalesforceのPaymentStart__cをFalseにする関数を呼び出す 💡
        from .salesforce import update_contractor_payment_status 
        sf_success = update_contractor_payment_status(username, status=False, isend=True)
        
        if sf_success:
            return True, "StripeとSalesforceでの解約が完了しました。"
        else:
            return True, "Stripeでは解約しましたが、Salesforceの更新に失敗しました。"

    except stripe.error.StripeError as e:
        return False, f"Stripe API Error: {e.user_message or e.code}"
    except Exception as e:
        return False, f"予期せぬエラー: {e}"
    
def create_customer_portal_session(user, request_host_url):
    """
    Stripe Customer Portalへのリダイレクトセッションを作成する。
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # ユーザー名から顧客IDを取得（get_latest_subscription_id 関数の一部ロジックを流用）
    try:
        # ユーザーのメールアドレス（ユーザー名）でStripe顧客を検索
        customers = stripe.Customer.list(email=user.username, limit=1)
        if not customers or not customers.data:
            return False, "Stripe顧客情報が見つかりません。再ログインしてください。"
            
        customer_id = customers.data[0].id
        
        # ユーザーがポータルから戻るためのURL
        return_url = request_host_url + reverse('home')
        
        # ポータルセッションの作成
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return True, session.url
        
    except stripe.error.StripeError as e:
        return False, f"Stripe APIエラー: {e.user_message or e.code}"
    except Exception as e:
        return False, f"予期せぬエラー: {e}"
    
    # accounts/stripe_utils.py (追記)

def get_stripe_info_by_email(email):
    """
    メールアドレスからStripe顧客IDと、最新の有効なサブスクリプションIDを取得する
    戻り値: (customer_id, subscription_id)
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        # 1. メールアドレスで顧客を検索 (最新の1件)
        customers = stripe.Customer.list(email=email, limit=1)
        
        if not customers or not customers.data:
            return None, None
            
        customer = customers.data[0]
        customer_id = customer.id
        
        # 2. その顧客のアクティブなサブスクリプションを検索
        subscriptions = stripe.Subscription.list(
            customer=customer_id, 
            status='active', 
            limit=1
        )
        
        subscription_id = None
        if subscriptions and subscriptions.data:
            subscription_id = subscriptions.data[0].id
            
        return customer_id, subscription_id

    except Exception as e:
        print(f"Stripe Search Error: {e}")
        return None, None