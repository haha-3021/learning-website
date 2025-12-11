from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tutorial.models import (
    ArchitectureTemplate, TemplateSlot, 
    UserArchitecture, BlockProject
)

class Command(BaseCommand):
    help = '创建默认的架构图模板和插槽'

    def handle(self, *args, **options):
        self.stdout.write('开始创建默认架构图模板...')
        
        # 创建或获取默认模板
        template, created = ArchitectureTemplate.objects.get_or_create(
            name='记物本系统标准架构',
            defaults={
                'description': '标准的Django Web应用程序分层架构，包含前端、后端和数据库层',
                'layout_type': 'hierarchical',
                'width': 900,
                'height': 500,
                'background_color': '#f8f9fa',
                'is_default': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ 创建了默认架构图模板: {template.name}')
            )
            
            # 创建分层架构的插槽
            layers = [
                {
                    'name': '用户界面层',
                    'description': '前端界面，用户交互，使用HTML/CSS/JavaScript',
                    'x_position': 100, 'y_position': 50,
                    'width': 180, 'height': 80,
                    'background_color': '#e3f2fd', 
                    'border_color': '#2196f3',
                    'text_color': '#1565c0',
                    'allowed_block_types': ['template'],
                    'required': True, 
                    'order': 1
                },
                {
                    'name': 'URL路由层', 
                    'description': '请求路由和分发，URL映射到视图',
                    'x_position': 100, 'y_position': 180,
                    'width': 180, 'height': 80,
                    'background_color': '#e8f5e8', 
                    'border_color': '#4caf50',
                    'text_color': '#2e7d32',
                    'allowed_block_types': ['url'],
                    'required': True, 
                    'order': 2
                },
                {
                    'name': '业务逻辑层',
                    'description': '视图处理和业务逻辑，接收请求并返回响应',
                    'x_position': 100, 'y_position': 310,
                    'width': 180, 'height': 80,
                    'background_color': '#fff3e0', 
                    'border_color': '#ff9800',
                    'text_color': '#ef6c00',
                    'allowed_block_types': ['Django_basic', 'calculation', 'add_function', 'delete_function'],
                    'required': True, 
                    'order': 3
                },
                {
                    'name': '数据模型层',
                    'description': '数据结构和关系，定义数据模型',
                    'x_position': 400, 'y_position': 180,
                    'width': 180, 'height': 80,
                    'background_color': '#f3e5f5', 
                    'border_color': '#9c27b0',
                    'text_color': '#7b1fa2',
                    'allowed_block_types': ['data_model'],
                    'required': True, 
                    'order': 4
                },
                {
                    'name': '数据存储层',
                    'description': '数据库和存储，SQLite/PostgreSQL等',
                    'x_position': 400, 'y_position': 310,
                    'width': 180, 'height': 80,
                    'background_color': '#e0f2f1', 
                    'border_color': '#009688',
                    'text_color': '#00695c',
                    'allowed_block_types': ['database'],
                    'required': True, 
                    'order': 5
                },
                {
                    'name': '管理后台',
                    'description': '系统管理界面，方便数据管理',
                    'x_position': 650, 'y_position': 180,
                    'width': 180, 'height': 80,
                    'background_color': '#ffebee', 
                    'border_color': '#f44336',
                    'text_color': '#c62828',
                    'allowed_block_types': ['admin', 'list_display'],
                    'required': False, 
                    'order': 6
                }
            ]
            
            slots = []
            for layer_data in layers:
                slot = TemplateSlot.objects.create(template=template, **layer_data)
                slots.append(slot)
                self.stdout.write(f'  创建插槽: {slot.name}')
            
            # 设置连线关系
            # 用户界面 -> URL路由 -> 业务逻辑 -> 数据模型 -> 数据存储
            slots[0].connected_to.add(slots[1])  # 界面 -> URL
            slots[1].connected_to.add(slots[2])  # URL -> 业务逻辑  
            slots[2].connected_to.add(slots[3])  # 业务逻辑 -> 数据模型
            slots[3].connected_to.add(slots[4])  # 数据模型 -> 数据存储
            slots[3].connected_to.add(slots[5])  # 数据模型 -> 管理后台
            
            self.stdout.write(
                self.style.SUCCESS('✅ 创建了架构图插槽和连线关系')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ 默认模板已存在，跳过创建')
            )
        
        # 为现有用户创建架构图实例
        self.create_architecture_for_existing_users(template)
        
        self.stdout.write(
            self.style.SUCCESS('🎉 默认架构图模板创建完成！')
        )
    
    def create_architecture_for_existing_users(self, template):
        """为现有用户创建架构图实例"""
        self.stdout.write('开始为用户创建架构图实例...')
        
        users = User.objects.all()
        created_count = 0
        
        for user in users:
            # 检查是否已有架构图
            if not UserArchitecture.objects.filter(user=user).exists():
                try:
                    # 创建项目
                    project = BlockProject.objects.create(
                        user=user,
                        name='我的记物本系统',
                        description='基于架构图模板构建的记物本系统'
                    )
                    # 创建用户架构图
                    UserArchitecture.objects.create(
                        user=user,
                        template=template,
                        project=project
                    )
                    created_count += 1
                    self.stdout.write(f'  为用户 {user.username} 创建了架构图')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ 为用户 {user.username} 创建架构图失败: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ 为 {created_count} 个用户创建了架构图实例')
        )