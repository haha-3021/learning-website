from django.db import models
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Chapter(models.Model):
    """学習チャプター"""
    title = models.CharField(max_length=200, verbose_name="チャプタータイトル")
    description = models.TextField(verbose_name="チャプター説明")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = "学習チャプター"
        verbose_name_plural = "学習チャプター"

    def __str__(self):
        return self.title

    def get_question_count(self):
        return self.question_set.filter(is_active=True).count()

class ChapterStudyTime(models.Model):
    """ユーザーのチャプター学習時間を記録"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="チャプター")
    start_time = models.DateTimeField(verbose_name="学習開始時間")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="学習終了時間")
    total_seconds = models.IntegerField(default=0, verbose_name="総学習時間（秒）")
    
    class Meta:
        verbose_name = "学習時間記録"
        verbose_name_plural = "学習時間記録"
        ordering = ['-start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'chapter'], 
                condition=models.Q(end_time__isnull=True),
                name='unique_active_session_per_user_chapter'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.chapter.title} - {self.get_duration_display()}"

    def save(self, *args, **kwargs):
        # 修复时间计算逻辑
        if self.start_time and self.end_time:
            try:
                # 确保时区一致
                if timezone.is_naive(self.start_time):
                    self.start_time = timezone.make_aware(self.start_time)
                if timezone.is_naive(self.end_time):
                    self.end_time = timezone.make_aware(self.end_time)
                
                time_diff = self.end_time - self.start_time
                calculated_seconds = int(time_diff.total_seconds())
                
                # 如果计算出的时间不合理，使用前端提供的时间
                if calculated_seconds <= 0 and hasattr(self, '_frontend_seconds'):
                    self.total_seconds = max(self._frontend_seconds, 1)
                else:
                    self.total_seconds = max(calculated_seconds, 1)
                    
            except Exception as e:
                logger.error(f"学习时间计算错误: {e}")
                # 如果计算失败，至少记录1秒
                self.total_seconds = 1
        else:
            # 如果没有结束时间，保持为0
            self.total_seconds = self.total_seconds or 0
            
        super().save(*args, **kwargs)

    def set_frontend_seconds(self, seconds):
        """设置前端计时秒数"""
        self._frontend_seconds = seconds

    def get_duration_display(self):
        """フォーマットされた学習時間を表示"""
        if self.total_seconds < 60:
            return f"{self.total_seconds}秒"
        elif self.total_seconds < 3600:
            minutes = self.total_seconds // 60
            seconds = self.total_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = self.total_seconds // 3600
            minutes = (self.total_seconds % 3600) // 60
            return f"{hours}時間{minutes}分"

    def is_active_session(self):
        """アクティブな学習セッションかどうかをチェック（終了時間がない）"""
        return self.end_time is None

class StudyGuide(models.Model):
    """学習ガイド"""
    chapter = models.OneToOneField(Chapter, on_delete=models.CASCADE, verbose_name="所属チャプター")
    content = HTMLField(verbose_name="学習内容")

    is_published = models.BooleanField(default=True, verbose_name="公開状態")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "学習ガイド"
        verbose_name_plural = "学習ガイド"

    def __str__(self):
        return f"{self.chapter.title} - 学習ガイド"
    
class StudyGuideAttachment(models.Model):
    """学習ガイドに紐づくZIPファイル等の添付"""
    study_guide = models.ForeignKey(
        StudyGuide,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="対象学習ガイド"
    )

    key = models.CharField(max_length=50, verbose_name="プレースホルダキー（例：ZIP1）")
    
    file = models.FileField(
        upload_to='study_guide_zips/',
        verbose_name="添付ファイル（ZIPなど）"
    )
    
    display_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="リンク表示名（例：サンプルコードZIP）"
    )

    class Meta:
        verbose_name = "学習ガイド添付"
        verbose_name_plural = "学習ガイド添付"

    def __str__(self):
        return f"{self.study_guide} - {self.key}"

class Question(models.Model):
    """問題モデル"""
    QUESTION_TYPES = [
        ('fill', '穴埋め問題（単一空）'),
        ('multi_fill', '穴埋め問題（複数空）'),
        ('choice', '選択問題'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', '簡単'),
        ('medium', '普通'),
        ('hard', '難しい'),
    ]
    
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="所属チャプター")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, verbose_name="問題タイプ")
    question_text = models.TextField(verbose_name="問題文")
    code_snippet = models.TextField(blank=True, null=True, verbose_name="コードスニペット")
    order = models.IntegerField(default=0, verbose_name="表示順")
    explanation = models.TextField(blank=True, verbose_name="解説")
    hint = models.TextField(blank=True, verbose_name="ヒント")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium', verbose_name="難易度")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "問題"
        verbose_name_plural = "問題"

    def __str__(self):
        return f"{self.chapter.title} - {self.question_text[:50]}"

    def get_blank_count(self):
        """获取填空题的空格数量"""
        try:
            if self.question_type == 'multi_fill':
                # 对于多空填空题，计算不同的blank_index数量
                blank_indices = self.choice_set.filter(
                    is_correct=True
                ).values_list('blank_index', flat=True).distinct()
                count = len(blank_indices)
                print(f"[DEBUG] 问题 {self.id} 多空填空题空格数量: {count}")
                return max(count, 1)  # 至少返回1
            elif self.question_type == 'fill':
                # 对于单空填空题，返回1
                print(f"[DEBUG] 问题 {self.id} 单空填空题，空格数量: 1")
                return 1
            else:
                # 对于选择题，返回0
                print(f"[DEBUG] 问题 {self.id} 选择题，空格数量: 0")
                return 0
        except Exception as e:
            print(f"[ERROR] 获取问题 {self.id} 空格数量失败: {e}")
            # 出错时返回默认值
            if self.question_type in ['fill', 'multi_fill']:
                return 1
            return 0
        
    def get_blank_range(self):
        return range(self.get_blank_count())

    def get_correct_answers_by_blank(self):
        """空白インデックスごとに正解を取得"""
        correct_answers = {}
        try:
            choices = self.choice_set.filter(is_correct=True).order_by('blank_index')
            
            for choice in choices:
                if choice.blank_index not in correct_answers:
                    correct_answers[choice.blank_index] = []
                correct_answers[choice.blank_index].append(choice.choice_text)
            
            print(f"[DEBUG] 问题 {self.id} 各空位正确答案: {correct_answers}")
        except Exception as e:
            print(f"[ERROR] 获取问题 {self.id} 各空位正确答案失败: {e}")
        
        return correct_answers

    def get_question_type_display_name(self):
        type_map = {
            'fill': '単一空欄問題',
            'multi_fill': '複数空欄問題', 
            'choice': '選択問題'
        }
        return type_map.get(self.question_type, self.question_type)

    def get_difficulty_color(self):
        color_map = {
            'easy': '#27ae60',    
            'medium': '#f39c12',   
            'hard': '#e74c3c'     
        }
        return color_map.get(self.difficulty, '#95a5a6')

    def get_choices_for_blank(self, blank_index=0):
        if self.question_type == 'choice':
            return self.choice_set.all().order_by('order')
        elif self.question_type in ['fill', 'multi_fill']:
            return self.choice_set.filter(blank_index=blank_index, is_correct=True)
        return []

    def validate_answer(self, user_answer, question_type):
        """验证用户答案（通用方法）"""
        if question_type == 'choice':
            # 选择题验证逻辑
            try:
                selected_choice = Choice.objects.get(id=user_answer, question=self)
                return selected_choice.is_correct
            except Choice.DoesNotExist:
                return False
        
        elif question_type == 'fill':
            # 单空填空题验证逻辑
            correct_choices = self.choice_set.filter(is_correct=True, blank_index=0)
            user_answer_clean = user_answer.strip().lower()
            
            for choice in correct_choices:
                if user_answer_clean == choice.choice_text.strip().lower():
                    return True
            return False
        
        elif question_type == 'multi_fill':
            # 多空填空题验证逻辑
            user_answers = [ans.strip().lower() for ans in user_answer.split(',')]
            correct_answers_by_blank = self.get_correct_answers_by_blank()
            
            for i, user_ans in enumerate(user_answers):
                if i in correct_answers_by_blank:
                    correct_options = [ans.strip().lower() for ans in correct_answers_by_blank[i]]
                    if user_ans not in correct_options:
                        return False
                else:
                    return False
            return True
        
        return False

    def get_correct_answer_display(self):
        """获取正确答案的显示文本"""
        if self.question_type == 'choice':
            correct_choices = self.choice_set.filter(is_correct=True)
            return ", ".join([choice.choice_text for choice in correct_choices])
        
        elif self.question_type == 'fill':
            correct_choices = self.choice_set.filter(is_correct=True, blank_index=0)
            return ", ".join([choice.choice_text for choice in correct_choices])
        
        elif self.question_type == 'multi_fill':
            correct_answers_by_blank = self.get_correct_answers_by_blank()
            parts = []
            for i in sorted(correct_answers_by_blank.keys()):
                correct_options = correct_answers_by_blank[i]
                if correct_options:
                    parts.append(f"空{i+1}: {', '.join(correct_options)}")
            return "; ".join(parts)
        
        return ""

    def get_statistics(self):
        """获取问题的统计信息"""
        from .models import WrongAnswer
        wrong_count = WrongAnswer.objects.filter(question=self).count()
        
        return {
            'wrong_count': wrong_count,
            'difficulty': self.get_difficulty_display(),
            'type': self.get_question_type_display_name(),
            'has_hint': bool(self.hint.strip()),
            'has_explanation': bool(self.explanation.strip()),
        }

    def is_answered_correctly_by_user(self, user):
        """检查用户是否曾经正确回答过这个问题"""
        from .models import WrongAnswer
        return not WrongAnswer.objects.filter(user=user, question=self).exists()

    @classmethod
    def get_questions_by_chapter_and_type(cls, chapter_id, question_type=None):
        """根据章节和问题类型获取问题"""
        queryset = cls.objects.filter(chapter_id=chapter_id, is_active=True)
        if question_type:
            queryset = queryset.filter(question_type=question_type)
        return queryset.order_by('order')

    @classmethod
    def get_questions_by_difficulty(cls, difficulty):
        """根据难度获取问题"""
        return cls.objects.filter(difficulty=difficulty, is_active=True).order_by('chapter__order', 'order')

class Choice(models.Model):
    """選択肢／解答"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="関連する問題")
    choice_text = models.CharField(max_length=200, verbose_name="選択肢／答え")
    is_correct = models.BooleanField(default=False, verbose_name="正解かどうか")
    order = models.IntegerField(default=0, verbose_name="表示順")
    blank_index = models.IntegerField(default=0, verbose_name="空欄番号")
    
    class Meta:
        ordering = ['blank_index', 'order']
        verbose_name = "選択肢／解答"
        verbose_name_plural = "選択肢／解答"

    def __str__(self):
        return f"{self.choice_text} ({'正解' if self.is_correct else '不正解'})"

class UserProgress(models.Model):
    """ユーザーの学習進捗"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="チャプター")
    completed = models.BooleanField(default=False, verbose_name="完了済みかどうか")
    score = models.IntegerField(default=0, verbose_name="スコア")
    studied_guide = models.BooleanField(default=False, verbose_name="学習ガイドを学習済み")
    experience_awarded = models.BooleanField(default=False, verbose_name="経験値獲得済みかどうか")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'chapter']
        verbose_name = "ユーザー進捗"
        verbose_name_plural = "ユーザー進捗"

    def __str__(self):
        status = "完了" if self.completed else "未完了"
        return f"{self.user.username} - {self.chapter.title} - {status}"

    def save(self, *args, **kwargs):
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.completed and self.completed_at:
            self.completed_at = None
        super().save(*args, **kwargs)

class WrongAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="問題")
    wrong_answer = models.TextField(verbose_name="間違った回答")
    correct_answer = models.TextField(verbose_name="正しい回答")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="記録時間")
    
    class Meta:
        verbose_name = "間違い記録"
        verbose_name_plural = "間違い記録"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.question.chapter.title}"

class UserQuestionAnswer(models.Model):
    """ユーザーごとの各問題の最新回答（途中退出＆再開用）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="問題")
    answer_text = models.TextField(verbose_name="回答内容")
    is_correct = models.BooleanField(default=False, verbose_name="正解かどうか")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最終更新日時")

    class Meta:
        verbose_name = "ユーザー回答"
        verbose_name_plural = "ユーザー回答"
        unique_together = ('user', 'question')

    def __str__(self):
        status = "正解" if self.is_correct else "未正解"
        return f"{self.user.username} - Q{self.question.id} ({status})"

class ChapterResult(models.Model):
    """チャプターごとの回答結果（1回分の記録）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="チャプター")
    
    correct_count = models.IntegerField(verbose_name="正解数")
    total_count = models.IntegerField(verbose_name="問題総数")
    accuracy = models.FloatField(verbose_name="正答率（%）")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="記録日時")

    class Meta:
        verbose_name = "チャプター結果"
        verbose_name_plural = "チャプター結果"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.chapter.title} ({self.accuracy}%)"


class UserProfile(models.Model):
    """ユーザープロファイル - 経験値システムと学習時間管理"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    experience = models.IntegerField(default=0, verbose_name="経験値")
    level = models.IntegerField(default=1, verbose_name="レベル")
    total_chapters_completed = models.IntegerField(default=0, verbose_name="完了章数")
    chapters_with_experience = models.TextField(default="", blank=True, verbose_name="経験値獲得済み章")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ユーザープロファイル"
        verbose_name_plural = "ユーザープロファイル"

    def __str__(self):
        return f"{self.user.username} - Lv.{self.level} (EXP: {self.experience})"
    
    def add_experience(self, amount):
        """增加经验值并检查是否升级"""
        old_level = self.level
        self.experience += amount
        
        # 假设每100经验一级，或者使用你现有的等级公式
        new_level = (self.experience // 100) + 1
        
        is_leveled_up = False
        if new_level > old_level:
            self.level = new_level
            is_leveled_up = True
        
        self.save()
        return is_leveled_up, new_level

    # ==================== 学習時間関連メソッド ====================
    
    def get_total_study_time_seconds(self):
        """ユーザーの総学習時間を取得（秒）"""
        total_seconds = ChapterStudyTime.objects.filter(
            user=self.user, 
            end_time__isnull=False
        ).aggregate(total=models.Sum('total_seconds'))['total']
        return total_seconds or 0

    def get_total_study_time_display(self):
        """フォーマットされた総学習時間を表示"""
        total_seconds = self.get_total_study_time_seconds()
        return self._format_study_time(total_seconds)

    def get_chapter_study_time_seconds(self, chapter):
        """特定のチャプターでのユーザーの学習時間を取得（秒）"""
        study_times = ChapterStudyTime.objects.filter(
            user=self.user, 
            chapter=chapter,
            end_time__isnull=False
        )
        total_seconds = study_times.aggregate(total=models.Sum('total_seconds'))['total']
        return total_seconds or 0

    def get_chapter_study_time_display(self, chapter):
        """フォーマットされたチャプター学習時間を表示"""
        total_seconds = self.get_chapter_study_time_seconds(chapter)
        return self._format_study_time(total_seconds)

    def _format_study_time(self, total_seconds):
        """秒数をフォーマットされた時間文字列に変換"""
        if total_seconds < 60:
            return f"{total_seconds}秒"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}時間{minutes}分"

    def get_study_time_statistics(self):
        """学習時間の統計情報を取得"""
        total_study_seconds = self.get_total_study_time_seconds()
        
        # 平均学習時間（完了チャプターあたり）
        avg_study_per_chapter = 0
        if self.total_chapters_completed > 0:
            avg_study_per_chapter = total_study_seconds // self.total_chapters_completed
        
        # チャプター別学習時間
        chapter_times = []
        completed_chapters = UserProgress.objects.filter(
            user=self.user, 
            completed=True
        ).select_related('chapter')
        
        for progress in completed_chapters:
            chapter_seconds = self.get_chapter_study_time_seconds(progress.chapter)
            chapter_times.append({
                'chapter': progress.chapter,
                'study_seconds': chapter_seconds,
                'study_time_display': self._format_study_time(chapter_seconds)
            })
        
        return {
            'total_study_seconds': total_study_seconds,
            'total_study_time_display': self._format_study_time(total_study_seconds),
            'avg_study_per_chapter': self._format_study_time(avg_study_per_chapter),
            'chapter_times': chapter_times,
            'total_chapters_studied': len(chapter_times)
        }

    # ==================== レベル・経験値関連メソッド ====================

    def calculate_level(self):
        """経験値からレベルを計算"""
        if self.experience <= 0:
            return 1
        
        # よりスムーズなレベル曲線を使用
        # レベル = floor(√(経験値 / 25)) + 1
        import math
        calculated_level = math.floor(math.sqrt(self.experience / 25)) + 1
        
        return min(max(calculated_level, 1), 100)  # 1-100レベルに制限
    
    def award_bonus_experience(self, activity_type, **kwargs):
        """ボーナス経験値を授与"""
        bonus_map = {
            'daily_login': 10,           # 毎日ログイン
            'perfect_score': 25,         # 満点完了
            'fast_completion': 15,       # 高速完了
            'first_try': 20,             # 一回合格
            'week_streak': 50,           # 毎週連続学習
        }
        
        amount = bonus_map.get(activity_type, 0)
        if amount > 0:
            result = self.award_experience(amount, f"ボーナス: {activity_type}")
            return result
        
        return None

    def get_exp_for_next_level(self):
        """次のレベルに必要な経験値を計算"""
        # 次のレベルに必要な経験値 = 現在のレベル^2 * 25
        return (self.level ** 2) * 25

    def get_exp_progress(self):
        """現在のレベルでの経験値進捗率を取得"""
        exp_required = self.get_exp_for_next_level()
        current_exp_in_level = self.experience - ((self.level - 1) * 100)
        
        if exp_required == 0:
            return 100
        
        progress = (current_exp_in_level / exp_required) * 100
        return min(100, max(0, progress))
    
    def award_experience(self, amount, reason=""):
        """経験値を授与しレベルアップ情報を返す"""
        old_level = self.level
        self.experience += amount
        
        # 新しいレベルを計算
        new_level = self.calculate_level()
        level_up = new_level > old_level
        self.level = new_level
        
        self.save()
        
        return {
            'level_up': level_up,
            'old_level': old_level,
            'new_level': new_level,
            'experience_gained': amount,
            'reason': reason
        }
    
    def get_level_info(self):
        """詳細なレベル情報を取得"""
        exp_for_current_level = (self.level - 1) * 100
        exp_for_next_level = self.level * 100
        current_exp_in_level = self.experience - exp_for_current_level
        exp_required_for_next = exp_for_next_level - exp_for_current_level
        
        progress_percentage = (current_exp_in_level / exp_required_for_next) * 100 if exp_required_for_next > 0 else 100
        
        return {
            'current_level': self.level,
            'current_experience': self.experience,
            'experience_in_level': current_exp_in_level,
            'experience_required_for_next': exp_required_for_next,
            'progress_percentage': min(progress_percentage, 100),
            'exp_for_next_level': exp_for_next_level,
        }
    
    def get_recent_achievements(self, limit=5):
        """最近の実績を取得"""
        completed_chapters = UserProgress.objects.filter(
            user=self.user, 
            completed=True
        ).order_by('-completed_at')[:limit]
        
        achievements = []
        for progress in completed_chapters:
            achievements.append({
                'type': 'chapter_completion',
                'title': f'{progress.chapter.title} 完了',
                'experience': 50,  # チャプターに応じて調整可能
                'date': progress.completed_at
            })
        
        return achievements

    def add_chapter_experience(self, chapter_id):
        """チャプター経験値を追加"""
        chapters = [ch for ch in self.chapters_with_experience.split(",") if ch]
        if str(chapter_id) not in chapters:
            chapters.append(str(chapter_id))
            self.chapters_with_experience = ",".join(chapters)
            self.total_chapters_completed = len(chapters)
            return True
        return False

    def has_experience_for_chapter(self, chapter_id):
        """チャプター経験値獲得済みかチェック"""
        chapters = [ch for ch in self.chapters_with_experience.split(",") if ch]
        return str(chapter_id) in chapters

class Badge(models.Model):
    """バッジモデル"""
    BADGE_TYPES = [
        ('level', 'レベルバッジ'),
        ('achievement', '実績バッジ'),
        ('special', '特殊バッジ'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="バッジ名称")
    description = models.TextField(verbose_name="バッジ説明")
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES, default='achievement', verbose_name="バッジタイプ")
    icon = models.CharField(max_length=50, default='🏆', verbose_name="アイコン")
    color = models.CharField(max_length=20, default='#4CAF50', verbose_name="バッジカラー")
    
    # アンロック条件
    required_experience = models.IntegerField(default=0, verbose_name="必要経験値")
    required_level = models.IntegerField(default=0, verbose_name="必要レベル")
    required_chapters = models.IntegerField(default=0, verbose_name="必要完了チャプター数")
    required_score = models.IntegerField(
        default=0,
        verbose_name="必要スコア",
        help_text="任意のチャプターでこの点数以上を獲得すると条件達成とみなす"
    )
    
    # 表示設定
    order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "バッジ"
        verbose_name_plural = "バッジ"
    
    def __str__(self):
        return self.name
    
    def is_unlocked_by_user(self, user):
        """ユーザーがこのバッジをアンロックしているかチェック"""
        if not user.is_authenticated:
            return False
        
        try:
            profile = user.userprofile
            print(f"  バッジ '{self.name}' アンロック条件チェック:")
            print(f"    - ユーザー経験値: {profile.experience}, 必要: {self.required_experience}")
            print(f"    - ユーザーレベル: {profile.level}, 必要: {self.required_level}")
            print(f"    - ユーザーチャプター: {profile.total_chapters_completed}, 必要: {self.required_chapters}")
            
            # 経験値条件チェック
            if self.required_experience > 0:
                if profile.experience < self.required_experience:
                    print(f"    - ❌ 経験値不足")
                    return False
                else:
                    print(f"    - ✅ 経験値条件達成")
            
            # レベル条件チェック
            if self.required_level > 0:
                if profile.level < self.required_level:
                    print(f"    - ❌ レベル不足")
                    return False
                else:
                    print(f"    - ✅ レベル条件達成")
            
            # チャプター条件チェック
            if self.required_chapters > 0:
                if profile.total_chapters_completed < self.required_chapters:
                    print(f"    - ❌ チャプター不足")
                    return False
                else:
                    print(f"    - ✅ チャプター条件達成")

            if self.required_score > 0:
                # このユーザーのチャプターごとのスコアの最大値を取得
                max_score = UserProgress.objects.filter(
                    user=user
                ).aggregate(max=models.Max('score'))['max'] or 0

                print(f"    - ユーザー最高スコア: {max_score}, 必要スコア: {self.required_score}")

                if max_score < self.required_score:
                    print(f"    - ❌ スコア不足")
                    return False
                else:
                    print(f"    - ✅ スコア条件達成")
            
            print(f"    - 🎉 すべての条件達成、バッジアンロック！")
            return True
            
        except Exception as e:
            print(f"❌ バッジアンロック状態チェック失敗: {e}")
            return False

class UserBadge(models.Model):
    """ユーザーが獲得したバッジ"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, verbose_name="バッジ")
    unlocked_at = models.DateTimeField(auto_now_add=True, verbose_name="獲得時間")
    
    class Meta:
        unique_together = ['user', 'badge']
        verbose_name = "ユーザーバッジ"
        verbose_name_plural = "ユーザーバッジ"
        ordering = ['-unlocked_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class BuildingBlock(models.Model):
    """積木ブロック"""
    BLOCK_TYPES = [
        ('data_model', 'データモデル積木'),
        ('view', 'ビュー積木'),
        ('template', 'テンプレート積木'),
        ('url', 'URL設定積木'),
        ('admin', '管理画面積木'),
        ('form', 'フォーム積木'),  # 新しいタイプを追加
        ('database', 'データベース積木'),  # ★ 追加
    ]
    
    BLOCK_COLORS = [
        ("#4C56B3", '青色 - ビュー'), 
        ('#FF6B6B', '赤色 - テンプレート'), 
        ('#4CAF50', '緑色 - URL設定'),
        ('#2196F3', '青色 - 管理画面'),
        ('#FF9800', '橙色 - フォーム'),
        ("#9ED877", '橙色 - データモデル'),
        ("#795548", '茶色 - データベース'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="積木名称")
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES, verbose_name="積木タイプ")
    description = models.TextField(verbose_name="積木説明")
    code_snippet = models.TextField(verbose_name="コードスニペット")
    color = models.CharField(max_length=20, choices=BLOCK_COLORS, default='#4CAF50', verbose_name="積木カラー")
    chapters = models.ManyToManyField(Chapter, verbose_name="所属チャプター", related_name='building_blocks', blank=True)
    order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    
    # 知識拡張フィールド
    expand_knowledge = models.TextField(verbose_name="知識拡張", blank=True)
    usage_examples = models.TextField(verbose_name="使用例", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    manually_unlocked = models.BooleanField(
        default=False, 
        verbose_name="手動アンロック（チャプター要求を無視）"
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "積木モジュール"
        verbose_name_plural = "積木モジュール"

    def __str__(self):
        return f"{self.name} ({self.get_block_type_display()})"

    def is_unlocked_for_user(self, user):
        """ユーザーがこの積木をアンロックしているかチェック"""
        if not user.is_authenticated:
            return False
        
        # 手動アンロックが設定されている場合、直接 True を返す
        if self.manually_unlocked:
            return True
        
        try:
            # ユーザーが関連チャプターを完了しているかチェック
            completed_chapters = UserProgress.objects.filter(
                user=user, 
                completed=True
            ).values_list('chapter_id', flat=True)
            
            # この積木が完了したチャプターに属しているか
            is_unlocked = self.chapters.filter(id__in=completed_chapters).exists()
            
            return is_unlocked
            
        except Exception as e:
            print(f"積木アンロック状態チェック失敗: {e}")
            return False

class ArchitectureSlot(models.Model):
    """アーキテクチャ図スロット"""
    name = models.CharField(max_length=100, verbose_name="位置名称")
    description = models.TextField(verbose_name="位置説明")
    x_position = models.IntegerField(default=0, verbose_name="X座標")
    y_position = models.IntegerField(default=0, verbose_name="Y座標")
    width = models.IntegerField(default=200, verbose_name="幅")
    height = models.IntegerField(default=120, verbose_name="高さ")
    background_color = models.CharField(max_length=20, default='#ffffff', verbose_name="背景色")
    border_color = models.CharField(max_length=20, default='#dee2e6', verbose_name="枠色")
    allowed_block_types = models.JSONField(default=list, verbose_name="許可される積木タイプ")
    required = models.BooleanField(default=False, verbose_name="必須")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    layer_type = models.CharField(
        max_length=20, 
        choices=[
            ('http', 'HTTP層'),
            ('url', 'URLルーティング層'),
            ('view', 'ビューレイヤー'),
            ('form', 'フォーム層'),
            ('model', 'モデル層'),
            ('template', 'テンプレート層'),
        ],
        default='view',
        verbose_name="レイヤータイプ"
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "アーキテクチャスロット"
        verbose_name_plural = "アーキテクチャスロット"

    def __str__(self):
        return self.name
    
class ArchitectureDiagramTemplate(models.Model):
    """架构图模板"""
    name = models.CharField(max_length=100, verbose_name="模板名称")
    description = models.TextField(verbose_name="模板描述", blank=True)
    layers = models.JSONField(default=list, verbose_name="层级配置")
    connections = models.JSONField(default=list, verbose_name="连接配置")
    is_default = models.BooleanField(default=False, verbose_name="默认模板")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "架构图模板"
        verbose_name_plural = "架构图模板"
    
    def __str__(self):
        return self.name

class ArchitectureDiagram(models.Model):
    """架构图主模型"""
    name = models.CharField(max_length=100, verbose_name="架构图名称")
    description = models.TextField(verbose_name="架构图描述", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", null=True, blank=True)
    is_template = models.BooleanField(default=False, verbose_name="是否为模板")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "架构图"
        verbose_name_plural = "架构图"
    
    def __str__(self):
        return self.name

class DiagramLayer(models.Model):
    """アーキテクチャ図レイヤー"""
    LAYER_TYPES = [
        ('url', 'URLルーティング層'),
        ('view', 'ビューレイヤー'),
        ('form', 'フォーム層'),
        ('model', 'モデル層'),
        ('template', 'テンプレート層'),
    ]
    
    # 修正：将外键指向 ArchitectureDiagram
    diagram = models.ForeignKey(ArchitectureDiagram, on_delete=models.CASCADE, verbose_name="所属アーキテクチャ図")
    layer_type = models.CharField(max_length=20, choices=LAYER_TYPES, verbose_name="レイヤータイプ")
    name = models.CharField(max_length=100, verbose_name="レイヤー名")
    description = models.TextField(verbose_name="レイヤー説明")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    
    class Meta:
        ordering = ['order']
        verbose_name = "アーキテクチャレイヤー"
        verbose_name_plural = "アーキテクチャレイヤー"
    
    def __str__(self):
        return f"{self.diagram.name} - {self.name}"
    
class DiagramComponent(models.Model):
    """架构图组件"""
    diagram = models.ForeignKey(ArchitectureDiagramTemplate, on_delete=models.CASCADE, verbose_name="所属架构图")
    name = models.CharField(max_length=100, verbose_name="组件名称")
    component_type = models.CharField(max_length=50, verbose_name="组件类型")
    position_x = models.IntegerField(default=0, verbose_name="X坐标")
    position_y = models.IntegerField(default=0, verbose_name="Y坐标")
    width = models.IntegerField(default=200, verbose_name="宽度")
    height = models.IntegerField(default=80, verbose_name="高度")
    color = models.CharField(max_length=20, default="#4C56B3", verbose_name="颜色")
    allowed_block_types = models.JSONField(default=list, verbose_name="允许的积木类型")
    layer = models.CharField(max_length=50, verbose_name="所属层级")
    order = models.IntegerField(default=0, verbose_name="排序")
    
    class Meta:
        ordering = ['layer', 'order']
        verbose_name = "架构图组件"
        verbose_name_plural = "架构图组件"
    
    def __str__(self):
        return f"{self.diagram.name} - {self.name}"

class UserArchitecture(models.Model):
    """ユーザーのアーキテクチャ図"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    name = models.CharField(max_length=100, default="マイアーキテクチャ図", verbose_name="アーキテクチャ図名")
    description = models.TextField(blank=True, verbose_name="説明")
    
    # JSONフィールドを使用してスロット割り当てを保存
    slot_assignments = models.JSONField(default=dict, verbose_name="スロット割り当て")
    
    generated_code = models.TextField(blank=True, verbose_name="生成コード")
    is_public = models.BooleanField(default=False, verbose_name="公開")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ユーザーアーキテクチャ図"
        verbose_name_plural = "ユーザーアーキテクチャ図"

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def assign_block_to_slot(self, slot_id, block_id):
        """積木をスロットに割り当て"""
        if not self.slot_assignments:
            self.slot_assignments = {}
        
        self.slot_assignments[str(slot_id)] = block_id
        self.save()

    def remove_block_from_slot(self, slot_id):
        """スロットから積木を削除"""
        if self.slot_assignments and str(slot_id) in self.slot_assignments:
            del self.slot_assignments[str(slot_id)]
            self.save()

    def get_assigned_blocks(self):
        """割り当てられた積木を取得"""
        assigned_blocks = {}
        for slot_id, block_id in self.slot_assignments.items():
            try:
                block = BuildingBlock.objects.get(id=block_id)
                assigned_blocks[slot_id] = block
            except BuildingBlock.DoesNotExist:
                continue
        return assigned_blocks

class ArchitectureTemplate(models.Model):
    """アーキテクチャテンプレート"""
    name = models.CharField(max_length=100, verbose_name="テンプレート名称")
    description = models.TextField(verbose_name="テンプレート説明", blank=True)
    
    # テンプレート設定
    slot_configurations = models.JSONField(default=dict, verbose_name="スロット設定")
    recommended_blocks = models.ManyToManyField(
        BuildingBlock, 
        blank=True, 
        verbose_name="推奨積木"
    )
    
    # 新規フィールド
    is_default = models.BooleanField(default=False, verbose_name="デフォルトテンプレートかどうか")
    
    # メタデータ
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order = models.IntegerField(default=0, verbose_name="順序")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "アーキテクチャテンプレート"
        verbose_name_plural = "アーキテクチャテンプレート"
        ordering = ['order']
    
    def __str__(self):
        return self.name

# ==================== シグナルハンドラー ====================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """ユーザープロファイルを作成"""
    if created:
        try:
            UserProfile.objects.create(user=instance)
            # デフォルトアーキテクチャ図を作成
            UserArchitecture.objects.create(user=instance)
        except Exception as e:
            logger.error(f"ユーザープロファイル作成失敗: {e}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """ユーザープロファイルを保存"""
    try:
        if hasattr(instance, 'userprofile'):
            instance.userprofile.save()
        else:
            UserProfile.objects.create(user=instance)
    except Exception as e:
        logger.error(f"ユーザープロファイル保存失敗: {e}")

@receiver(post_save, sender=UserProgress)
def update_user_profile_on_progress(sender, instance, created, **kwargs):
    """進捗更新時にユーザープロファイルを更新 - 修正版"""
    try:
        # チャプターが完了し、経験値がまだ授与されていない場合のみ処理
        if instance.completed and not instance.experience_awarded:
            # ユーザープロファイルを取得または作成
            profile, _ = UserProfile.objects.get_or_create(user=instance.user)
            
            # このチャプターですでに経験値を獲得したかチェック
            if not profile.has_experience_for_chapter(instance.chapter.id):
                # 難易度に応じて異なる経験値を授与
                experience_points = calculate_experience_for_chapter(instance.chapter)
                
                # 経験値を追加
                profile.experience += experience_points
                profile.add_chapter_experience(instance.chapter.id)
                
                # レベルを再計算
                old_level = profile.level
                profile.level = profile.calculate_level()
                
                # 経験値授与済みとしてマーク
                instance.experience_awarded = True
                instance.save(update_fields=['experience_awarded'])
                
                # ユーザープロファイルを保存
                profile.save()
                
                # 条件を満たすバッジをチェックして授与
                new_badges = profile.check_and_award_badges()
                
                # ログ記録
                level_up_message = ""
                if profile.level > old_level:
                    level_up_message = f" レベルが Lv.{profile.level} にアップ！"
                
                badge_message = ""
                if new_badges:
                    badge_names = [badge.name for badge in new_badges]
                    badge_message = f" 新しいバッジ獲得: {', '.join(badge_names)}"
                
                logger.info(
                    f"ユーザー {instance.user.username} チャプター {instance.chapter.title} 完了 "
                    f"{experience_points} EXP 獲得{level_up_message}{badge_message}"
                )
    
    except Exception as e:
        logger.error(f"ユーザープロファイル更新失敗: {e}")

def calculate_experience_for_chapter(chapter):
    """チャプターに基づいて経験値を計算"""
    # 基本経験値
    base_exp = 50
    
    # チャプター内の問題数と難易度に基づいて経験値を調整
    questions = chapter.question_set.filter(is_active=True)
    
    if questions.exists():
        # 難易度ボーナス
        difficulty_bonus = {
            'easy': 0,
            'medium': 10,
            'hard': 25
        }
        
        total_bonus = sum(
            difficulty_bonus.get(q.difficulty, 0) 
            for q in questions
        )
        
        # 問題数ボーナス（問題ごとに+5経験値）
        count_bonus = min(questions.count() * 5, 50)
        
        return base_exp + total_bonus + count_bonus
    
    return base_exp

# ==================== UserProfile 追加メソッド ====================

def check_and_award_badges(self):
    """条件を満たすバッジをチェックして授与"""
    try:
        # ユーザーがアンロックしたバッジIDリストを取得
        unlocked_badge_ids = set(
            UserBadge.objects.filter(user=self.user).values_list('badge_id', flat=True)
        )
    
        # すべてのアクティブなバッジを取得
        all_badges = Badge.objects.filter(is_active=True)
    
        new_badges = []
        for badge in all_badges:
        # ユーザーがまだこのバッジを持っておらず、アンロック条件を満たす場合
            if badge.id not in unlocked_badge_ids and badge.is_unlocked_by_user(self.user):
                # ユーザーバッジレコードを作成
                user_badge = UserBadge.objects.create(user=self.user, badge=badge)
                new_badges.append(badge)
                print(f"🎉 バッジ授与: {badge.name} ユーザー {self.user.username}")
    
        return new_badges
    
    except Exception as e:
        logger.error(f"バッジチェック失敗: {e}")
        print(f"❌ バッジチェックエラー: {e}")
        return []

def get_badge_progress(self, badge):
    """バッジアンロック進捗を取得"""
    try:
        # バッジが既にアンロックされている場合、100%進捗を返す
        if badge.is_unlocked_by_user(self.user):
            return 100
    
        progress_data = {}
    
        # 経験値条件進捗チェック
        if badge.required_experience > 0:
            progress_percent = min((self.experience / badge.required_experience) * 100, 100) if badge.required_experience > 0 else 0
            progress_data['experience'] = {
                'current': self.experience,
                'required': badge.required_experience,
                'progress': progress_percent
            }
    
        # レベル条件進捗チェック
        if badge.required_level > 0:
            progress_percent = min((self.level / badge.required_level) * 100, 100) if badge.required_level > 0 else 0
            progress_data['level'] = {
                'current': self.level,
                'required': badge.required_level,
                'progress': progress_percent
            }
    
        # チャプター条件進捗チェック
        if badge.required_chapters > 0:
            progress_percent = min((self.total_chapters_completed / badge.required_chapters) * 100, 100) if badge.required_chapters > 0 else 0
            progress_data['chapters'] = {
                'current': self.total_chapters_completed,
                'required': badge.required_chapters,
                'progress': progress_percent
            }
    
        return progress_data
    
    except Exception as e:
        print(f"❌ バッジ進捗取得失敗: {e}")
        return {}

def get_unlocked_badges(self):
    """ユーザーがアンロックしたバッジを取得"""
    return UserBadge.objects.filter(user=self.user).select_related('badge')

# UserProfile にメソッドを追加
UserProfile.check_and_award_badges = check_and_award_badges
UserProfile.get_badge_progress = get_badge_progress
UserProfile.get_unlocked_badges = get_unlocked_badges

# ==================== ユーティリティ関数 ====================

def get_user_statistics(user):
    """ユーザー統計情報を取得"""
    return {
        'total_chapters': Chapter.objects.filter(is_active=True).count(),
        'completed_chapters': UserProgress.objects.filter(user=user, completed=True).count(),
        'total_questions': Question.objects.filter(is_active=True).count(),
        'wrong_answers': WrongAnswer.objects.filter(user=user).count(),
        'total_blocks': BuildingBlock.objects.filter(is_active=True).count(),
    }

# シグナル接続を確実にする
post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)
post_save.connect(update_user_profile_on_progress, sender=UserProgress)