# accounts/views.py

import json
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import FormView,PasswordResetConfirmView,PasswordResetView # FormViewをベースにカスタマイズ
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

import requests
from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect 
from django.conf import settings  
import stripe 
from django.utils.html import strip_tags # 💡 HTMLタグ除去用関数をインポート
from django.views.decorators.http import require_POST
from .forms import SendMessageForm
from .utils import send_push_notification_to_user
# 💡 Salesforce連携関数をインポート 💡
from .salesforce import create_salesforce_message, get_all_contractors, create_message_by_sf_id, update_contractor_payment_status,update_salesforce_stripe_info, get_contractor_info_by_username, get_auth_token, register_salesforce_contractor, add_salesforce_webpush_subscription, get_contractor_messages, update_salesforce_password, hash_password # インポート追加

# 管理者(スーパーユーザー)のみアクセス可能にする
from django.contrib.admin.views.decorators import staff_member_required
from .forms import SendMessageForm, BulkSendMessageForm # BulkSendMessageFormを追加
from .stripe_utils import create_subscription_checkout_session, cancel_stripe_subscription, create_customer_portal_session, get_stripe_info_by_email # 新しい関数をインポート
from django.contrib.sites.models import Site

@staff_member_required
def send_bulk_message_view(request):
    if request.method == 'POST':
        form = BulkSendMessageForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            html_body = form.cleaned_data['body'] # HTML
            
            # 💡 Web Push用にHTMLタグを除去 💡
            plain_body = strip_tags(html_body)
            
            # 1. 全ユーザーをSalesforceから取得
            contractors = get_all_contractors()
            
            if not contractors:
                messages.error(request, "送信対象のユーザーが見つかりません。")
                return redirect('send_bulk_message')

            success_count = 0
            User = get_user_model()

            # 2. ループ処理で送信
            for contractor in contractors:
                sf_id = contractor['Id']
                username = contractor['Name']
                
                # 1. SalesforceにはHTML保存
                if create_message_by_sf_id(sf_id, subject, html_body):
                    success_count += 1
                    
                    try:
                        target_user = User.objects.get(username=username)
                        # 2. Web Pushにはプレーンテキスト送信
                        send_push_notification_to_user(
                            target_user, 
                            title=f"【一斉連絡】{subject}", 
                            body=plain_body[:50]
                        )
                    except User.DoesNotExist:
                        pass # ローカルにいないユーザーはスキップ
            
            messages.success(request, f"{len(contractors)}名中、{success_count}名へのメッセージ保存に成功しました。")
            return redirect('home') # または完了画面へ
            
    else:
        form = BulkSendMessageForm()
        
    return render(request, 'accounts/send_bulk_message.html', {'form': form})

# ----------------------------------------------------
# 個別送信ビュー (send_message_view)
# ----------------------------------------------------
@staff_member_required
def send_message_view(request):
    if request.method == 'POST':
        form = SendMessageForm(request.POST)
        if form.is_valid():
            target_username = form.cleaned_data['target_username']
            subject = form.cleaned_data['subject']
            html_body = form.cleaned_data['body'] # これはHTML
            
            # 💡 1. SalesforceにはHTMLのまま保存 💡
            sf_success = create_salesforce_message(target_username, subject, html_body)
            
            if sf_success:
                try:
                    User = get_user_model()
                    target_user = User.objects.get(username=target_username)
                    
                    # 💡 2. Web Push用にHTMLタグを除去 💡
                    plain_body = strip_tags(html_body)
                    
                    # 改行コード等が詰まってしまう場合があるため、少し整形しても良い
                    # plain_body = plain_body.replace('&nbsp;', ' ') 
                    
                    push_success, push_msg = send_push_notification_to_user(
                        target_user, 
                        title=f"新着メッセージ: {subject}", 
                        body=plain_body[:50] + "..." # プレーンテキストの一部を表示
                    )
                    messages.success(request, f"送信＆通知成功: {push_msg}")
                    
                except User.DoesNotExist:
                    messages.warning(request, "Web Push用のローカルユーザーが見つかりません。")
            else:
                messages.error(request, "Salesforceへの保存に失敗しました。")
                
            return redirect('send_message')
    else:
        form = SendMessageForm()
        
    return render(request, 'accounts/send_message.html', {'form': form})

# accounts/views.py

@require_POST
@login_required
def subscribe_push(request):
    try:
        subscription_data = json.loads(request.body)
        
        # HTTPヘッダーからUserAgentを取得
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        # 保存関数を呼び出し
        success = add_salesforce_webpush_subscription(
            request.user.username, 
            subscription_data,
            user_agent
        )
        
        if success:
            return JsonResponse({'status': 'ok'})
        else:
            # ここでエラーになってもJS側はコンソールエラーのみ
            print("Salesforce save returned False")
            return JsonResponse({'status': 'error', 'message': 'Salesforce save failed'}, status=500)

    except Exception as e:
        print(f"Subscribe View Error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
# -----------------------------------------------------------
# サインアップビュー (CreateView)
# -----------------------------------------------------------

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    
    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('home')

    def form_valid(self, form):
        user_data = form.cleaned_data
        
        # 1. Salesforce APIに契約者として登録
        success, message = register_salesforce_contractor(user_data)
        
        if success:
            # 2. 登録成功: ローカルDBにプロキシユーザーを作成し、ログイン
            User = get_user_model()
            
            # ローカルプロキシユーザーを作成 (usernameとメールアドレスを設定)
            user, created = User.objects.get_or_create(username=user_data['username'],
                                                       defaults={'email': user_data['username']}
            )
            if created:
                user.set_unusable_password()
                user.save()
            
            # 💡 修正箇所: ログイン処理に backend を明示的に指定 💡
            login(
                self.request, 
                user, 
                backend='accounts.backends.SalesforceBackend'
            )
            messages.success(self.request, "契約者情報の登録とログインが完了しました。")
            
            return redirect(self.get_success_url())
        
        else:
            # 登録失敗: エラーメッセージをフォームに追加
            messages.error(self.request, f"ユーザー登録に失敗しました: {message}")
            return self.form_invalid(form)
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next')
        context['bukken_name'] = self.request.GET.get('bukkenName')
        context['gyousya_id'] = self.request.GET.get('gyousyaId')
        return context

# -----------------------------------------------------------
# Stripe 関連
# -----------------------------------------------------------
@login_required
def create_checkout_session_view(request):
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripeキーが設定されていません。")
        return redirect('home')

    # Fly.ioデプロイ時の絶対URL生成をサポート (ロジックはビューに残す)
    HOST_URL = 'https://' + settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '127.0.0.1' else 'http://127.0.0.1:8000'
    
    # 💡 ユーティリティ関数を呼び出す 💡
    success, result = create_subscription_checkout_session(request.user, HOST_URL)
    
    if success:
        # 成功した場合、result には決済URLが入っている
        return redirect(result, code=303)
    else:
        # 失敗した場合、result にはエラーメッセージが入っている
        messages.error(request, result)
        return redirect('home')

@login_required
@require_POST
def cancel_subscription_view(request):
    """
    StripeサブスクリプションとSalesforceレコードを解約し、
    成功した場合はローカルユーザーを削除する
    """
    user = request.user # 削除する前にユーザーオブジェクトを取得
    username = user.username
    
    # 1. Stripe解約 & Salesforce更新 (既存のロジック)
    success, message = cancel_stripe_subscription(username)
    
    if success:
        # 2. 成功した場合: ローカルユーザーを削除
        try:
            # ユーザーを削除 (これにより関連するセッションなども無効化されます)
            user.delete()
            
            # メッセージを残してログイン画面へ
            # (ユーザー削除直後でも、リダイレクト直後の1回だけメッセージが表示される場合があります)
            messages.success(request, "退去処理が完了しました。ご利用ありがとうございました。")
            
            # ユーザーが存在しなくなったため、ホームではなくログイン画面へ飛ばす
            return redirect('login')
            
        except Exception as e:
            # 万が一削除に失敗した場合
            messages.error(request, f"解約は完了しましたが、アカウント削除に失敗しました: {e}")
            return redirect('home')
    else:
        # 3. 失敗した場合: エラーを表示してホームに戻る
        messages.error(request, f"解約処理中にエラーが発生しました: {message}")
        return redirect('home')

@login_required
def manage_payment_method_view(request):
    """
    Stripe Customer Portalへユーザーをリダイレクトするビュー
    """
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripeキーが設定されていません。")
        return redirect('home')
    
    # Fly.ioデプロイ時の絶対URL生成をサポート (HOST_URLは既存のものを再利用)
    HOST_URL = 'https://' + settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '127.0.0.1' else 'http://127.0.0.1:8000'
    
    success, url_or_message = create_customer_portal_session(request.user, HOST_URL)
    
    if success:
        # 成功: StripeのポータルURLへリダイレクト
        return redirect(url_or_message)
    else:
        # 失敗: エラーメッセージを表示してホームに戻る
        messages.error(request, url_or_message)
        return redirect('home')
# -----------------------------------------------------------

# -----------------------------------------------------------
# 会員ホームビュー (home_view)
# -----------------------------------------------------------

@login_required 
def home_view(request):
    context = {}
    
    # ... (既存の処理: 契約者情報取得など) ...
    contractor_info = get_contractor_info_by_username(request.user.username)
    if contractor_info:
        context['contractor_info'] = contractor_info

    # 💡 3. メッセージ一覧を取得してコンテキストに追加 💡
    messages_list = get_contractor_messages(request.user.username)
    context['messages_list'] = messages_list
    
    # GETパラメータから決済結果を取得しメッセージを準備
    # GETパラメータから決済結果を取得
    payment_status = request.GET.get('payment')
    
    if payment_status == 'success':
        username = request.user.username # メールアドレスとして使用
        
        # 💡 1. Stripeから顧客IDとサブスクIDを検索 💡
        customer_id, subscription_id = get_stripe_info_by_email(username)
        
        if customer_id and subscription_id:
            # 💡 2. Salesforceを更新 (顧客ID, サブスクID, 支払いフラグ) 💡
            sf_updated = update_salesforce_stripe_info(username, customer_id, subscription_id)
            
            if sf_updated:
                messages.success(request, '決済が完了し、Salesforceへの連携が完了しました！')
            else:
                messages.warning(request, '決済は完了しましたが、Salesforceの更新に失敗しました。')
        else:
            # Stripe上でデータが見つからなかった場合（タイムラグ等の可能性）
            messages.warning(request, '決済情報は確認中ですが、Stripe情報の取得に時間がかかっています。')

    elif payment_status == 'cancelled':
        messages.warning(request, '決済がキャンセルされました。')

    return render(request, 'accounts/home.html', context)

class NoOldPasswordChangeView(LoginRequiredMixin, FormView):
    # 古いパスワードを要求しない SetPasswordForm を使用
    form_class = SetPasswordForm 
    template_name = 'registration/password_change_form.html'
    # 成功時のリダイレクト先
    success_url = reverse_lazy('password_change_done') 

    def get_form_kwargs(self):
        """フォームに現在のユーザーオブジェクトを渡し、バリデーションを可能にする"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user # 👈 ログイン中のユーザーを渡す
        return kwargs

    def form_valid(self, form):
        username = self.request.user.username
        new_password = form.cleaned_data['new_password1']
        # new_hashed_password = hash_password(new_password)
        new_hashed_password = new_password
        
        # 2. Salesforceのパスワードを更新
        # 💡 修正箇所: エラーメッセージを受け取るように変更 💡
        sf_success, sf_error_msg = update_salesforce_password(username, new_hashed_password, return_error=True)
        
        if not sf_success:
            # 🚨 失敗した場合の処理 🚨
            messages.error(self.request, f"Salesforceのパスワード更新に失敗しました。詳細: {sf_error_msg}")
            
            # 💡 フォームにエラーを追加する（画面表示用）
            form.add_error(None, "パスワードの更新処理でエラーが発生しました。Salesforce側の問題を確認してください。") 
            
            # 💡 form_invalidを呼び出してフォーム画面に戻る 💡
            return self.form_invalid(form) 
            # ログはターミナルに出ているはずですが、これでも画面が切り替わらない場合は問題が別の場所にあります 
            
        # 3. Djangoのローカルユーザーのパスワードを更新 (成功した場合のみ)
        form.save() 
        
        messages.success(self.request, "パスワードが正常に変更されました。")
        return super().form_valid(form)

# 💡 パスワードリセット確認ビューをカスタマイズ 💡
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        # 1. Djangoの標準処理を実行（ローカルユーザーのパスワード変更）
        # このステップで form.save() が呼ばれ、新しいパスワードが設定されます。
        response = super().form_valid(form)

        # 2. Salesforceの更新処理
        
        # フォームのユーザーはリセット対象のユーザー
        target_user = form.user 
        username = target_user.username
        
        # 新しいパスワードの平文（SetPasswordFormの仕様により取得可能）
        new_password = form.cleaned_data['new_password1'] 
        # new_hashed_password = hash_password(new_password)
        new_hashed_password = new_password
        
        # Salesforceのパスワードを更新
        sf_success, sf_error_msg = update_salesforce_password(username, new_hashed_password, return_error=True)
        
        if not sf_success:
            # 🚨 Salesforce更新失敗時の処理 🚨
            # ここでエラーが発生した場合、すでにローカルユーザーのパスワードは変更されているため、
            # ログを出力し、管理者に対応を促すメッセージを表示するのみにとどめます。
            print(f"CRITICAL ERROR: Salesforce password update failed for user {username}. Detail: {sf_error_msg}")
            messages.warning(self.request, "パスワードの変更は完了しましたが、Salesforce側での同期に失敗しました。管理者に連絡してください。")

        return response
    
class DebugPasswordResetView(PasswordResetView):
    # 💡 修正箇所 1: domain_override をクラス属性として設定 💡
    domain_override = '127.0.0.1:8000'
    
    # 💡 修正箇所 2: テンプレート名もクラス属性として設定 (urls.pyから移動) 💡
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    # 💡 どのユーザーがリクエストしているかを確認するためのメソッド 💡
    def get_users(self, email):
        # フォームに入力された値 (ここでは email としていますが、実際はユーザー名)
        # に基づいてユーザーを検索します。
        
        # 標準のロジックを呼び出し、ユーザーが見つかったか確認
        users = super().get_users(email)
        
        found_users = list(users)
        if found_users:
            print("--- DEBUG: PasswordResetView ---")
            print(f"ユーザーが見つかりました: {found_users[0].username}")
            print(f"送信先メールアドレス: {found_users[0].email}")
            print("---------------------------------")
        else:
            print("--- DEBUG: PasswordResetView ---")
            print(f"ユーザーが見つかりませんでした: {email}")
            print("---------------------------------")
            
        return found_users

# 💡 form_valid もオーバーライドして、処理が最後まで進んでいるか確認
    def form_valid(self, form):
        print(f"--- DEBUG: form_valid が呼ばれました。メール送信ロジックに進みます。---{Site.objects.get(pk=settings.SITE_ID)}")
        return super().form_valid(form)
    

# ----------------
# Stripe Webhock(未使用)
#-----------------
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
# ユーザーモデルやメール送信機能をインポート
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
@csrf_exempt # StripeからのリクエストにはCSRFトークンがないため必須
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # 署名の検証（セキュリティ対策：本当にStripeからの通信か確認）
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # ペイロードが無効
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # 署名が無効
        return HttpResponse(status=400)

    # --- イベントごとの処理 ---
    if event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        customer_id = invoice['customer']
        
        # ここにビジネスロジックを記述します
        handle_payment_failure(customer_id, invoice)

    return HttpResponse(status=200)

def handle_payment_failure(stripe_customer_id, invoice):
    """
    決済失敗時の処理ロジック
    """
    User = get_user_model()
    try:
        # StripeのCustomer IDからDjangoのユーザーを特定
        # (事前にUserモデルにstripe_customer_idフィールドなどを持たせておく必要があります)
        user = User.objects.get(stripe_customer_id=stripe_customer_id)
        
        # 処理1: ユーザーへの通知（メール等）
        send_mail(
            'お支払いに失敗しました',
            f'{user.username} 様\nカード決済が失敗しました。会員ページよりカード情報を更新してください。',
            'noreply@yourdomain.com',
            [user.email],
        )

        # 処理2: 権限の変更（必要に応じて）
        # 例: ステータスを「支払い遅延」に変更するなど
        # user.subscription_status = 'past_due'
        # user.save()
        
        print(f"User {user.id}: Payment failed notification sent.")

    except User.DoesNotExist:
        print("User not found for this Stripe customer.")