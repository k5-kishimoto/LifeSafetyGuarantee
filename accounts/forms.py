# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordResetForm,SetPasswordForm
from django.forms import PasswordInput
from django.contrib.auth import get_user_model
from .salesforce import get_all_agencies_for_choices 

User = get_user_model() 

# 🚨 CONTRACTOR_CHOICES の定義は不要なので削除 🚨



class CustomUserCreationForm(UserCreationForm):
    # ユーザー名とパスワード
    username = forms.EmailField(
        label='ユーザー名（メールアドレス）', 
        help_text='メールアドレスを入力してください。',
        max_length=150, 
        required=True,
        # HTML5のメール入力フォームを使用（スマホで入力しやすくなります）
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com'}),
        error_messages={
            'required': 'メールアドレスは必須です。',
            'invalid': '正しいメールアドレスの形式で入力してください。', # 👈 形式エラー時の日本語メッセージ
            'unique': 'このメールアドレスは既に登録されています。',
            'max_length': 'メールアドレスは150文字以内で入力してください。',
        }
    )
    last_name = forms.CharField(label='姓', max_length=50, required=True, error_messages={'required': '姓は必須です。',})
    first_name = forms.CharField(label='名', max_length=50, required=True, error_messages={'required': '名は必須です。',})
    password1 = forms.CharField(label='パスワード', widget=PasswordInput, strip=False)
    password2 = forms.CharField(label='パスワード（確認用）', widget=PasswordInput, strip=False, help_text='パスワードを再入力してください。')
    
    # 💡 選択リスト 💡
    # 💡 選択リストのフィールドはそのまま定義 💡
    contractor_name = forms.ChoiceField(
        label='不動産管理会社',
        # choices は __init__ で設定するため、ここでは空欄でOK
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Salesforceから選択肢を取得
        agency_choices = get_all_agencies_for_choices()
        
        # 2. フィールドに選択肢を設定
        self.fields['contractor_name'].choices = agency_choices

    # 💡 日付型 💡
    birthday = forms.DateField(
        label='生年月日',
        required=False,
        error_messages={'required': '生年月日は必須です。',},
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d') 
    )

    # 💡 カスタム項目 💡
    property_name = forms.CharField(label='物件名', max_length=100, required=True, error_messages={'required': '物件名は必須です。',})
    room_name = forms.CharField(label='部屋番号', max_length=50, required=True, error_messages={'required': '部屋番号は必須です。',})
    telephone = forms.CharField(label='電話番号', max_length=15, help_text='ハイフンなしで入力してください', required=True, error_messages={'required': '電話番号は必須です。',})
    address = forms.CharField(label='住所', widget=forms.Textarea(attrs={'rows': 3}), required=True, error_messages={'required': '住所は必須です。',})

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
        labels = {'username': 'ユーザー名（メールアドレス）'}

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
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm # 💡 両方インポート 💡

# ログイン中のユーザーのパスワード変更に使用するフォーム。
# SetPasswordFormは新しいパスワードとその確認のみを要求し、
# 古いパスワード（old_password）フィールドを持ちません。
class NoOldPasswordValidationForm(SetPasswordForm):
    """
    ログイン中のユーザーのパスワードを変更する際に、
    古いパスワードの検証をスキップするために使用するフォーム。
    (SetPasswordFormをそのまま利用し、必要に応じてカスタマイズ可能)
    """
    # 現状、SetPasswordFormにカスタムなフィールドやバリデーションを追加する必要がないため、
    # シンプルに pass します。
    pass

# 💡 修正箇所: パスワードリセット用のカスタムフォームを追加 💡
class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        """
        パスワードが使用不可(unusable)なユーザーもリセット対象に含めるようにオーバーライド
        """
        UserModel = get_user_model()
        email_field_name = UserModel.get_email_field_name()
        
        # 入力されたメールアドレス(またはユーザー名)に一致するアクティブなユーザーを検索
        active_users = UserModel._default_manager.filter(**{
            '%s__iexact' % email_field_name: email,
            'is_active': True,
        })
        
        # 親クラスのチェック(has_usable_password)をスキップして、ユーザーリストをそのまま返す
        return active_users