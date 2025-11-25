# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import PasswordInput
from django.contrib.auth import get_user_model
User = get_user_model() 

# 💡 業者名の選択肢 💡
CONTRACTOR_CHOICES = [
    ('', '--- 業者名を選択してください ---'), 
    ('A社', 'A社 (ID: 100)'),
    ('B社', 'B社 (ID: 200)'),
    ('C社', 'C社 (ID: 300)'),
]

class CustomUserCreationForm(UserCreationForm):
    # ユーザー名とパスワード
    username = forms.CharField(label='ユーザー名', max_length=150, required=True)
    last_name = forms.CharField(label='姓', max_length=50, required=True)
    first_name = forms.CharField(label='名', max_length=50, required=True)
    password1 = forms.CharField(label='パスワード', widget=PasswordInput, strip=False)
    password2 = forms.CharField(label='パスワード（確認用）', widget=PasswordInput, strip=False, help_text='パスワードを再入力してください。')
    
    # 💡 選択リスト 💡
    contractor_name = forms.ChoiceField(
        label='業者名',
        choices=CONTRACTOR_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 💡 日付型 💡
    birthday = forms.DateField(
        label='生年月日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d') 
    )

    # 💡 カスタム項目 💡
    property_name = forms.CharField(label='物件名', max_length=100, required=True)
    room_name = forms.CharField(label='部屋名', max_length=50, required=True)
    telephone = forms.CharField(label='電話番号', max_length=15, help_text='ハイフンなしで入力してください', required=True)
    address = forms.CharField(label='住所', widget=forms.Textarea(attrs={'rows': 3}), required=True)

    class Meta:
        model = User
        fields = (
            'username', 
            'last_name',
            'first_name',
            'birthday',
            'contractor_name',  
            'property_name', 
            'room_name', 
            'telephone', 
            'address'
        ) 
        labels = {'username': 'ユーザー名'}

from django import forms
from django_summernote.widgets import SummernoteWidget # インポート

# 個別送信フォーム
class SendMessageForm(forms.Form):
    target_username = forms.CharField(label='送信先ユーザー名', max_length=150)
    subject = forms.CharField(label='件名', max_length=100)
    # 💡 ウィジェットを SummernoteWidget に変更 💡
    body = forms.CharField(label='本文', widget=SummernoteWidget())

# 一括送信フォーム
class BulkSendMessageForm(forms.Form):
    subject = forms.CharField(label='件名', max_length=100)
    # 💡 ウィジェットを SummernoteWidget に変更 💡
    body = forms.CharField(
        label='本文', 
        widget=SummernoteWidget()
    )