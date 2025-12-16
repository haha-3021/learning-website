# apps.py - 完整版本
from django.apps import AppConfig


class TutorialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tutorial'
    verbose_name = '学習管理システム'

    def ready(self):
        """
        应用启动时执行的初始化代码
        注册信号处理器和其他初始化逻辑
        """
        # 导入信号处理器
        try:
            import tutorial.signals
            print(" 信号处理器导入成功")
        except ImportError as e:
            print(f" 信号处理器导入失败: {e}")
        
        # 导入模型方法
        try:
            from .models import get_user_statistics
            # 动态添加方法到User模型
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if not hasattr(User, 'get_statistics'):
                User.add_to_class('get_statistics', get_user_statistics)
                print(" 用户统计方法添加成功")
        except Exception as e:
            print(f" 模型方法初始化失败: {e}")

def initialize_default_data(self):
    """
    初始化默认数据
    """
    try:
        from django.db import connection
        from django.core.management.color import no_style
        from django.db.backends.base.creation import BaseDatabaseCreation
        
        # 检查表是否存在
        tables = connection.introspection.table_names()
        needed_tables = [
            'tutorial_chapter',
            'tutorial_studyguide', 
            'tutorial_question',
            'tutorial_choice',
            'tutorial_userprogress'
        ]
        
        # 如果必要表不存在，跳过初始化
        if not all(table in tables for table in needed_tables):
            print(" 数据库表未就绪，跳过默认数据初始化")
            return
        
        # 检查是否已经有默认模板
        from .models import ArchitectureTemplate
        if not ArchitectureTemplate.objects.filter(is_default=True).exists():
            print(" 创建默认架构图模板...")
            # 移除不存在的 layout_type 参数
            default_template = ArchitectureTemplate.objects.create(
                name='記物本システム標準アーキテクチャ',
                description='标准的Django Web应用程序分层架构',
                is_default=True,
                is_active=True
            )
            print(f" 默认模板创建成功: {default_template.name}")
            
        print(" 默认数据初始化完成")
        
    except Exception as e:
        print(f" 默认数据初始化失败: {e}")
