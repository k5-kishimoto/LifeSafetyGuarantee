# suppliers/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST # 💡 POST限定にするデコレータ
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate as auth_authenticate
from django.contrib import messages
from .forms import AgencySignUpForm

# 💡 インポートを追加
from .salesforce import (
    get_contractors_for_agency, 
    register_salesforce_agency, 
    update_move_out_status
)

@login_required(login_url='suppliers:login')
def home_view(request):
    """業者専用のホーム画面"""
    agency_username = request.user.username
    contractors = get_contractors_for_agency(agency_username)
    
    context = {
        'user': request.user,
        'contractors': contractors,
    }
    return render(request, 'suppliers/home.html', context)

# 💡 新規追加: 退去確認更新ビュー 💡
@login_required(login_url='suppliers:login')
@require_POST # ブラウザからの直接アクセスなどを防ぐ
def update_move_out(request):
    """
    ホーム画面の「退去」ボタンから呼ばれる処理。
    Salesforceのフラグを更新する。
    """
    # フォームの隠しフィールドからIDを取得
    contractor_id = request.POST.get('contractor_id')

    if contractor_id:
        # Salesforce更新処理を実行
        success, message = update_move_out_status(contractor_id)
        
        if success:
            messages.success(request, '退去確認を完了しました。')
        else:
            messages.error(request, f'更新に失敗しました: {message}')
    else:
        messages.error(request, '不正なリクエストです。IDが見つかりません。')

    # ホーム画面にリダイレクト
    return redirect('suppliers:home')


class AgencySignUpView(FormView):
    # ... (既存のコードと同じ) ...
    form_class = AgencySignUpForm
    template_name = 'suppliers/signup.html'
    
    def get_success_url(self):
        return reverse_lazy('suppliers:home')

    def form_valid(self, form):
        user_data = form.cleaned_data
        success, message = register_salesforce_agency(user_data)
        
        if success:
            user = auth_authenticate(
                self.request, 
                username=user_data['username'], 
                password=user_data['password1'],
                backend='suppliers.backends.AgencySalesforceBackend'
            )
            
            if user is not None:
                login(self.request, user, backend='suppliers.backends.AgencySalesforceBackend')
                messages.success(self.request, "業者アカウントの作成とログインが完了しました。")
                return redirect(self.get_success_url())
            else:
                messages.error(self.request, "認証に失敗しました。")
                return redirect('suppliers:login')
        else:
            messages.error(self.request, f"Salesforce登録失敗: {message}")
            return self.form_invalid(form)