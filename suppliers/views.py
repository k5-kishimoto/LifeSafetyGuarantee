# suppliers/views.py (修正)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .salesforce import get_contractors_for_agency # 💡 新しくインポート

from django.views.generic.edit import FormView # CreateViewではなくFormViewを使用
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate as auth_authenticate
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from .forms import AgencySignUpForm # 💡 新規フォーム
from .salesforce import register_salesforce_agency # 💡 新規SF関数

@login_required(login_url='suppliers:login')
def home_view(request):
    """業者専用のホーム画面"""
    
    agency_username = request.user.username
    
    # 💡 Salesforceから紐づく契約者情報を取得 💡
    contractors = get_contractors_for_agency(agency_username)
    
    context = {
        'user': request.user,
        'contractors': contractors, # 取得したリストをテンプレートに渡す
    }
    
    return render(request, 'suppliers/home.html', context)

# 💡 業者サインアップビュー 💡
class AgencySignUpView(FormView):
    form_class = AgencySignUpForm
    template_name = 'suppliers/signup.html'
    
    def get_success_url(self):
        return reverse_lazy('suppliers:home')

    def form_valid(self, form):
        user_data = form.cleaned_data
        
        # 1. Salesforceに業者アカウントを登録
        success, message = register_salesforce_agency(user_data)
        
        if success:
            # 2. 登録成功: 認証フローを通じてローカルプロキシユーザーを作成し、ログイン
            
            user = auth_authenticate(
                self.request, 
                username=user_data['username'], 
                password=user_data['password1'], # Plaintext password for authentication check
                backend='suppliers.backends.AgencySalesforceBackend' # 💡 業者認証バックエンドを指定 💡
            )
            
            if user is not None:
                login(self.request, user, backend='suppliers.backends.AgencySalesforceBackend')
                messages.success(self.request, "業者アカウントの作成とログインが完了しました。")
                return redirect(self.get_success_url())
            else:
                # 認証バックエンドがユーザーを作成できなかった場合 (通常は発生しないはず)
                messages.error(self.request, "認証に失敗しました。アカウントがロックされている可能性があります。")
                return redirect('suppliers:login')
        
        else:
            # 登録失敗: エラーメッセージを表示
            messages.error(self.request, f"Salesforce登録失敗: {message}")
            return self.form_invalid(form)