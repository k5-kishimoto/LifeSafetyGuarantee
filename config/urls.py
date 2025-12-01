"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf.urls.static import static
from django.views.generic import TemplateView # 💡 追加
from django.views.generic.base import RedirectView # 💡 RedirectViewをインポート

urlpatterns = [
    # 💡 修正箇所: ルートURL ('') を 'home' へリダイレクト 💡
    path('', RedirectView.as_view(url=reverse_lazy('home'), permanent=False), name='index'),
    path('admin/', admin.site.urls),
    # 認証関連のURLを '/accounts/' 以下に含める
    path('accounts/', include('django.contrib.auth.urls')),
    # 今後作成するカスタムビューやアプリのURLもここに追加
    # accountsアプリのカスタムURL (サインアップなど)
    path('accounts/', include('accounts.urls')),
    path('summernote/', include('django_summernote.urls')),# 💡 Service Worker をルートURLで配信するための設定 💡
    path('service_worker.js', TemplateView.as_view(
        template_name='service_worker.js', 
        content_type='application/javascript'
    ), name='service_worker'),

]

# 開発環境でのメディアファイル配信設定
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)