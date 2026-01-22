# suppliers/forms.py

from django import forms
from django.forms import PasswordInput

class AgencySignUpForm(forms.Form):
    # Name is used as Username in Salesforce
    username = forms.CharField(label='会社メールアドレス(以後ログインIDとなります)', max_length=150, required=True)
    password1 = forms.CharField(label='新規パスワードを設定いたします', widget=PasswordInput, required=True)
    password2 = forms.CharField(label='上記パスワードをご登録ください（確認用）', widget=PasswordInput, required=True)
    
    # 💡 業者名表示用フィールド (SalesforceのAgencyName__cに相当する情報など)
    agency_name = forms.CharField(label='不動産管理会社名', max_length=100, required=True) 

    def clean(self):
        """パスワードの一致チェック"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "パスワードが一致しません。"
            )
        return cleaned_data