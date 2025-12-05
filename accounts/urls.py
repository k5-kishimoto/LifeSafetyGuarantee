# accounts/urls.py

from django.urls import path
from .views import SignUpView, home_view, create_checkout_session_view, send_message_view, send_bulk_message_view, subscribe_push, cancel_subscription_view, manage_payment_method_view

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', home_view, name='home'), 
    path('create-checkout-session/', create_checkout_session_view, name='create_checkout_session'),
    path('manage-payment/', manage_payment_method_view, name='manage_payment'),
    path('manager/send-message/', send_message_view, name='send_message'),
    # 💡 一括送信用のURLを追加 💡
    path('manager/send-bulk-message/', send_bulk_message_view, name='send_bulk_message'),
    path('subscribe/', subscribe_push, name='subscribe_push'),
    # 💡 解約処理用URL (POST専用) 💡
    path('cancel-service/', cancel_subscription_view, name='cancel_service'),
]