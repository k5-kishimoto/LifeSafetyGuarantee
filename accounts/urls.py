# accounts/urls.py (追記)

from django.urls import path
from .views import SignUpView, home_view # home_viewをインポート

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', home_view, name='home'), # 追加: ログイン後のホーム画面
]