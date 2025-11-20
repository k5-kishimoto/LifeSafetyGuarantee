# accounts/views.py

from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm
# from django.http import HttpResponseRedirect # 今回は不要
from django.contrib.auth.decorators import login_required
from django.shortcuts import render # 必要に応じてインポート
from django.contrib.auth import login # 💡 login 関数をインポート 💡

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    
    def get_success_url(self):
        """ログイン成功後にリダイレクトされるURLを決定"""
        # GETとPOSTの両方から 'next' パラメータを取得
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        
        # next パラメータがある場合はそのURLへリダイレクト
        if next_url:
            return next_url
            
        # next パラメータがない場合は、デフォルトのホームURLへリダイレクト
        return reverse_lazy('home') # settings.py で定義した LOGIN_REDIRECT_URL と同じでOK

    # 💡 フォームが有効な場合に自動ログイン処理を追加 💡
    def form_valid(self, form):
        # 1. ユーザーをデータベースに保存 (これが親クラスの処理)
        response = super().form_valid(form)
        
        # 2. 保存されたユーザーオブジェクトを取得
        user = self.object
        
        # 3. ユーザーをログインさせる
        # self.request にユーザーのセッション情報をセット
        login(self.request, user)
        
        # 4. get_success_url で指定された場所にリダイレクト
        return response
    
    def get_context_data(self, **kwargs):
        # ... (既存の GET パラメータ処理はそのまま残します) ...
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next')
        context['bukken_name'] = self.request.GET.get('bukkenName')
        context['gyousya_id'] = self.request.GET.get('gyousyaId')
        return context
    
# 必要に応じて他のビューもここに定義
# def home_view(request):
#     return render(request, 'base.html') # 適切なテンプレートに変更してください
@login_required 
def home_view(request):
    return render(request, 'accounts/home.html')