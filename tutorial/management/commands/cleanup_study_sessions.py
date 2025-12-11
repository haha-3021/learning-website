from django.core.management.base import BaseCommand
from django.utils import timezone
from tutorial.models import ChapterStudyTime
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清理未结束的学习会话'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-age-hours',
            type=int,
            default=24,
            help='最大允许的未结束会话小时数（默认24小时）',
        )

    def handle(self, *args, **options):
        max_age_hours = options['max_age_hours']
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        
        # 找到超过最大年龄的未结束会话
        stale_sessions = ChapterStudyTime.objects.filter(
            end_time__isnull=True,
            start_time__lt=cutoff_time
        )
        
        count = stale_sessions.count()
        
        if count > 0:
            self.stdout.write(f'找到 {count} 个过期的未结束会话')
            
            for session in stale_sessions:
                # 计算持续时间
                duration = timezone.now() - session.start_time
                session.total_seconds = max(int(duration.total_seconds()), 1)
                session.end_time = timezone.now()
                session.save()
                
                self.stdout.write(
                    f'已结束会话: 用户 {session.user.username}, '
                    f'章节 {session.chapter.title}, '
                    f'持续时间 {session.get_duration_display()}'
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'成功清理 {count} 个过期的学习会话')
            )
        else:
            self.stdout.write('没有找到过期的学习会话')