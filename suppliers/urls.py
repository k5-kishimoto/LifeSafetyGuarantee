# suppliers/urls.py (修正)

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import AgencySignUpView # 💡 新しいビューをインポート

# 💡 修正箇所: この行を追加 💡
app_name = 'suppliers'

urlpatterns = [
    # 💡 ログイン画面: backend を明示的に指定 💡
    path('login/', auth_views.LoginView.as_view(
        template_name='suppliers/login.html',
        redirect_authenticated_user=True,
        next_page='suppliers:home',
        # 💡 extra_contextで認証バックエンドを指定 💡
        extra_context={'backend': 'suppliers.backends.AgencySalesforceBackend'},
    ), name='login'),
    
    # ログアウト: (変更なし)
    path('logout/', auth_views.LogoutView.as_view(
        next_page='suppliers:login'
    ), name='logout'),
    
    # 💡 サインアップパスの追加 💡
    path('signup/', AgencySignUpView.as_view(), name='signup'),

    # ホーム画面 (変更なし)
    path('', views.home_view, name='home'),

    # 💡 この行を追加してください
    path('update_move_out/', views.update_move_out, name='update_move_out'),
]