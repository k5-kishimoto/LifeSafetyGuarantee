# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import PasswordInput # 正しいインポート元に修正済み
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    # 💡 パスワードフィールドを明示的に再定義し、日本語ラベルを設定
    password1 = forms.CharField(
        label='パスワード',
        widget=PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label='パスワード（確認用）',
        widget=PasswordInput,
        strip=False,
        help_text='パスワードを再入力してください。',
    )
    
    # 💡 氏名フィールドに日本語ラベルを設定
    first_name = forms.CharField(label='名', max_length=150, required=False)
    last_name = forms.CharField(label='姓', max_length=150, required=False)
    
    # 💡 生年月日フィールドをカレンダー入力に設定
    birthday = forms.DateField(
        label='生年月日',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date'}, 
            format='%Y-%m-%d' 
        )
    )
    
    class Meta:
        model = CustomUser
        # フォームクラスで再定義した password/password2 以外のフィールドを含める
        fields = (
            'username', 
            'first_name', 
            'last_name', 
            'email',
            'birthday', 
        )
        
        # 💡 username のラベルを日本語に設定
        labels = {
            'username': 'ユーザー名',
        }