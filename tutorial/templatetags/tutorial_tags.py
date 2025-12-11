from django import template

register = template.Library()

@register.filter
def get_range(value):
    """
    创建一个范围，用于模板中的for循环
    用法: {{ 5|get_range }} → [0, 1, 2, 3, 4]
    """
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def multiply(value, arg):
    """
    乘法过滤器
    用法: {{ 5|multiply:3 }} → 15
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    除法过滤器
    用法: {{ 15|divide:3 }} → 5
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def add_str(value, arg):
    """
    字符串连接过滤器
    用法: {{ "hello"|add_str:" world" }} → "hello world"
    """
    return str(value) + str(arg)