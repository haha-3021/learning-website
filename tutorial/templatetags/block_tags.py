# 在您的Django应用中的templatetags/block_tags.py文件中

from django import template

register = template.Library()

# 积木类型到颜色的映射
BLOCK_COLORS = {
    'Django_basic': '#4C56B3',
    'python_basic': '#059669',
    'data_model': '#dc2626',
    'database': '#7c3aed',
    'admin': '#ea580c',
    'list_display': '#0891b2',
    'url': '#0891b2',
    'template': '#db2777',
    'calculation': '#65a30d',
    'add_function': '#0d9488',
    'delete_function': '#991b1b',
}

# 积木类型到图标的映射
BLOCK_ICONS = {
    'Django_basic': '🔷',
    'python_basic': '🐍',
    'data_model': '📊',
    'database': '🗃️',
    'admin': '⚙️',
    'list_display': '📋',
    'url': '🔗',
    'template': '📄',
    'calculation': '🧮',
    'add_function': '➕',
    'delete_function': '➖',
}

@register.filter
def get_block_color(block_type):
    """根据积木类型返回对应的颜色"""
    return BLOCK_COLORS.get(block_type, '#64748b')  # 默认颜色

@register.filter
def get_block_icon(block_type):
    """根据积木类型返回对应的图标"""
    return BLOCK_ICONS.get(block_type, '🧩')  # 默认图标