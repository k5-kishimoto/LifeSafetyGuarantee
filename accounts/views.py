# accounts/views.py

from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm
# from django.http import HttpResponseRedirect # 今回は不要
from django.contrib.auth.decorators import login_required
from django.shortcuts import render # 必要に応じてインポート

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    
    def get_success_url(self):
        """サインアップ成功後のリダイレクト先を決定"""
        # GETとPOSTの両方から 'next' パラメータを取得
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('login')

    def get_context_data(self, **kwargs):
        """GETパラメータを読み込み、テンプレートコンテキストに追加"""
        context = super().get_context_data(**kwargs)
        
        # hidden field 用に 'next' パラメータを渡す
        context['next_url'] = self.request.GET.get('next')
        
        # 💡 bukkenName と gyousyaId を取得してテンプレートに渡す
        context['bukken_name'] = self.request.GET.get('bukkenName')
        context['gyousya_id'] = self.request.GET.get('gyousyaId')
        
        return context

# 必要に応じて他のビューもここに定義
# def home_view(request):
#     return render(request, 'base.html') # 適切なテンプレートに変更してください
@login_required 
def home_view(request):
    return render(request, 'accounts/home.html')