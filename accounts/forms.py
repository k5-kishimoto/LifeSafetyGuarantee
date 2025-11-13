# accounts/forms.py (カスタムユーザーモデルを使う場合)

from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser # 作成したカスタムユーザーモデルをインポート

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        # モデルに CustomUser を指定
        model = CustomUser
        
        # CustomUser モデルのフィールドをすべて指定
        fields = (
            'username', 
            'email', 
            'first_name', 
            'last_name',
            'birthday', # <<< 追加したカスタムフィールド
        ) 
        # パスワードフィールドは UserCreationForm が自動で扱います。