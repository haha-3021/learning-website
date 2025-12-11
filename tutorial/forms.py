# tutorial/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    """
    用户注册表单
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': '请输入邮箱地址'
        })
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '请输入用户名'
        }),
        help_text='必填。150个字符或者更少。包含字母，数字和仅有的@/./+/-/_符号。'
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '请输入密码'
        }),
        help_text='''
            <ul>
                <li>你的密码不能与其他个人信息太相似。</li>
                <li>你的密码必须包含至少 8 个字符。</li>
                <li>你的密码不能是大家都爱用的常见密码。</li>
                <li>你的密码不能全部为数字。</li>
            </ul>
        '''
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '请确认密码'
        }),
        help_text='请输入与之前相同的密码进行验证。'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        """
        验证邮箱是否唯一
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱地址已被注册。')
        return email

class LoginForm(forms.Form):
    """
    用户登录表单
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '用户名',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '密码'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )

class QuestionAnswerForm(forms.Form):
    """
    问题答案提交表单
    """
    answer = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '请输入答案'
        })
    )

    def __init__(self, *args, **kwargs):
        question_type = kwargs.pop('question_type', None)
        super().__init__(*args, **kwargs)
        
        # 根据问题类型调整字段
        if question_type == 'choice':
            self.fields['answer'] = forms.ChoiceField(
                choices=[],
                widget=forms.RadioSelect(attrs={'class': 'form-radio'})
            )
        elif question_type in ['fill', 'multi_fill']:
            self.fields['answer'] = forms.CharField(
                widget=forms.TextInput(attrs={
                    'class': 'form-input',
                    'placeholder': '填空答案'
                })
            )

class SearchForm(forms.Form):
    """
    搜索表单
    """
    query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '搜索积木、章节或问题...'
        })
    )
    search_type = forms.ChoiceField(
        choices=[
            ('all', '全部'),
            ('blocks', '积木'),
            ('chapters', '章节'),
            ('questions', '问题')
        ],
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class ContactForm(forms.Form):
    """
    联系表单
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '您的姓名'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': '您的邮箱'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '主题'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 5,
            'placeholder': '请输入您的消息...'
        })
    )

class FeedbackForm(forms.Form):
    """
    反馈表单
    """
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ 非常好'),
        (4, '⭐⭐⭐⭐ 好'),
        (3, '⭐⭐⭐ 一般'),
        (2, '⭐⭐ 需要改进'),
        (1, '⭐ 很差')
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        label='请评价本系统'
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': '请提供您的宝贵建议...'
        }),
        label='意见建议'
    )
    contact_back = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='希望收到回复'
    )