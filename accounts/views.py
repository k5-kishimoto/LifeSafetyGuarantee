# accounts/views.py

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login') # 成功したらログインページへリダイレクト
    template_name = 'accounts/signup.html' # 使用するテンプレート名

# accounts/views.py (追記)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# ログインが必須なホームビュー
@login_required 
def home_view(request):
    return render(request, 'accounts/home.html')