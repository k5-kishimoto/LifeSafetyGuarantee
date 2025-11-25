# accounts/urls.py

from django.urls import path
from .views import SignUpView, home_view, create_checkout_session, send_message_view, send_bulk_message_view, subscribe_push

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', home_view, name='home'), 
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('manager/send-message/', send_message_view, name='send_message'),
    # 💡 一括送信用のURLを追加 💡
    path('manager/send-bulk-message/', send_bulk_message_view, name='send_bulk_message'),
    path('subscribe/', subscribe_push, name='subscribe_push'),
]