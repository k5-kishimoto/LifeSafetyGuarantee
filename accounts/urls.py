# accounts/urls.py

from django.urls import path
from .views import SignUpView, home_view, create_checkout_session

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', home_view, name='home'), 
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
]