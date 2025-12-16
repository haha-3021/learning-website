from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    """ユーザー登録フォーム（日本語エラーメッセージ固定 + メール重複チェック）"""

    email = forms.EmailField(
        label="メールアドレス",
        required=True,
        error_messages={
            "required": "メールアドレスを入力してください。",
            "invalid": "正しいメールアドレス形式で入力してください。",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ラベルを日本語に統一（必要なら）
        self.fields["username"].label = "ユーザー名"
        self.fields["password1"].label = "パスワード"
        self.fields["password2"].label = "パスワード（確認）"

        # username のエラーも日本語で固定（「同じユーザー名…」はこれでOK）
        self.fields["username"].error_messages.update({
            "required": "ユーザー名を入力してください。",
            "unique": "同じユーザー名が既に登録済みです。",
        })

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("メールアドレスを入力してください。")
        if User.objects.filter(email__iexact=email).exists():
            # ★ 中国語の「该邮箱地址已被注册。」をここで完全に置き換える
            raise ValidationError("このメールアドレスは既に登録されています。")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip()
        if commit:
            user.save()
        return user
