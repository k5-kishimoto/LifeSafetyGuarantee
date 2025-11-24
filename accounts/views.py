# accounts/views.py

from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm
from django.contrib.auth import login, get_user_model
from django.shortcuts import render, redirect 
from django.contrib import messages 
from django.conf import settings 
from django.contrib.auth.decorators import login_required 
import stripe 

# 💡 Salesforce連携関数をインポート 💡
from .salesforce import register_salesforce_contractor
from .salesforce import get_contractor_info_by_username #
from .salesforce import update_contractor_payment_status

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
# Stripe Checkout Session 生成ビュー
# -----------------------------------------------------------

@login_required
def create_checkout_session(request):
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripeキーが設定されていません。")
        return redirect('home')

    # Fly.ioデプロイ時の絶対URL生成をサポート
    HOST_URL = 'https://' + settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '127.0.0.1' else 'http://127.0.0.1:8000'

    success_url = HOST_URL + reverse('home') + '?payment=success'
    cancel_url = HOST_URL + reverse('home') + '?payment=cancelled'

    STRIPE_PRICE_ID = settings.STRIPE_SUBSCRIPTION_PRICE_ID # settingsから読み込み # ← ここに取得したIDを入れる
    # 💡 デバッグ用に出力 💡
    print(f"Stripe Price ID to use: [{STRIPE_PRICE_ID}]") 
    print(f"Type: {type(STRIPE_PRICE_ID)}") # 必ず <class 'str'> であること
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # 💡 Ad-hocな price_data ではなく、既存の price ID を指定 💡
                    'price': STRIPE_PRICE_ID,
                    'quantity': 1,
                }
            ],
            # 💡 モードを 'subscription' に変更 💡
            mode='subscription', 
            
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.user.email if request.user.email else None,
            metadata={'user_id': request.user.id},
            # 必要に応じて、サブスクリプション固有の設定を追加
            # subscription_data={
            #    'trial_period_days': 30, # トライアル期間など
            # }
        )
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f"決済セッションの作成に失敗しました: {e}")
        return redirect('home')
    
# -----------------------------------------------------------
# 会員ホームビュー (home_view)
# -----------------------------------------------------------

@login_required 
def home_view(request):
    context = {}
    
    # 1. Salesforceから契約者情報を取得
    contractor_info = get_contractor_info_by_username(request.user.username)
    
    if contractor_info:
        # 取得した情報をコンテキストに追加
        context['contractor_info'] = contractor_info
    
    # GETパラメータから決済結果を取得しメッセージを準備
    payment_status = request.GET.get('payment')
    
    if payment_status == 'success':
        # 💡 Salesforceのステータスを更新する処理を追加 💡
        sf_updated = update_contractor_payment_status(request.user.username)
        
        if sf_updated:
            messages.success(request, '決済が完了し、入居サービスの利用が開始されました！')
        else:
            # 決済はできたがSF更新に失敗した場合
            messages.warning(request, '決済は完了しましたが、システム連携に遅延が発生しています。管理者に連絡してください。')
    elif payment_status == 'cancelled':
        messages.warning(request, '決済がキャンセルされました。')

    # Django Messagesがコンテキストにメッセージを自動で含めるため、ここではメッセージ表示ロジックは不要
    return render(request, 'accounts/home.html', context)