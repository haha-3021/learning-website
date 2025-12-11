# admin.py - 修复版
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    Chapter, StudyGuide, StudyGuideAttachment, Question, Choice, UserProgress, 
    ChapterStudyTime, UserProfile, WrongAnswer, BuildingBlock, 
    ArchitectureSlot, UserArchitecture, UserBadge, Badge
)

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1
    fields = ['choice_text', 'is_correct', 'order', 'blank_index']
    verbose_name = _('選択肢')
    verbose_name_plural = _('選択肢')

class StudyGuideAttachmentInline(admin.TabularInline):
    model = StudyGuideAttachment
    extra = 1
    fields = ('key', 'file', 'display_name')

@admin.register(ChapterStudyTime)
class ChapterStudyTimeAdmin(admin.ModelAdmin):
    list_display = ['user', 'chapter', 'start_time', 'end_time', 'total_seconds', 'get_duration_display']
    list_filter = ['chapter', 'start_time']
    search_fields = ['user__username', 'chapter__title']
    readonly_fields = ['total_seconds']
    date_hierarchy = 'start_time'
    
    def get_duration_display(self, obj):
        return obj.get_duration_display()
    get_duration_display.short_description = _('学習時間')

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'created_at', 'get_question_count']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['order']

    def get_question_count(self, obj):
        return obj.get_question_count()
    get_question_count.short_description = _('問題数')

@admin.register(StudyGuide)
class StudyGuideAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'is_published', 'created_at', 'updated_at']
    list_editable = ['is_published']
    list_filter = ['is_published', 'created_at']
    search_fields = ['chapter__title', 'content']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'chapter', 'question_type', 'difficulty', 'question_text_short', 
        'order', 'is_active'
    ]
    list_editable = ['order', 'is_active', 'difficulty']
    list_filter = ['chapter', 'question_type', 'difficulty', 'is_active']
    search_fields = ['question_text', 'explanation', 'hint']
    ordering = ['chapter__order', 'order']
    inlines = [ChoiceInline]
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = _('問題内容')

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['choice_text_short', 'question', 'is_correct', 'blank_index', 'order']
    list_editable = ['is_correct', 'order', 'blank_index']
    list_filter = ['is_correct', 'question__chapter', 'question__question_type']
    search_fields = ['choice_text', 'question__question_text']
    list_select_related = ['question__chapter']
    
    def choice_text_short(self, obj):
        return obj.choice_text[:50] + '...' if len(obj.choice_text) > 50 else obj.choice_text
    choice_text_short.short_description = _('選択肢')

@admin.register(WrongAnswer)
class WrongAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_chapter', 'get_question_preview', 'created_at']
    list_filter = ['question__chapter', 'created_at']  # 修复：使用 question__chapter
    search_fields = ['user__username', 'question__question_text', 'wrong_answer', 'correct_answer']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_chapter(self, obj):
        return obj.question.chapter.title  # 通过 question 获取 chapter
    get_chapter.short_description = _('チャプター')
    
    def get_question_preview(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    get_question_preview.short_description = _('問題プレビュー')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'chapter', 'completed', 'score', 'studied_guide', 'experience_awarded', 'updated_at']
    list_editable = ['completed', 'score', 'studied_guide', 'experience_awarded']
    list_filter = ['completed', 'experience_awarded', 'chapter', 'studied_guide']
    search_fields = ['user__username', 'chapter__title']
    readonly_fields = ['updated_at']
    list_select_related = ['user', 'chapter']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'level', 'experience', 'get_exp_progress', 
        'total_chapters_completed', 'updated_at'
    ]
    list_filter = ['level', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_exp_progress(self, obj):
        return f"{obj.get_exp_progress():.1f}%"
    get_exp_progress.short_description = _('次のレベルまで')

@admin.register(BuildingBlock)
class BuildingBlockAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'block_type', 'order', 'is_active', 'get_related_chapters_count'
    ]
    list_editable = ['order', 'is_active']
    list_filter = ['block_type', 'is_active']
    search_fields = ['name', 'description', 'code_snippet']
    filter_horizontal = ['chapters']
    
    # 添加字段集以便更好地组织表单
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'block_type', 'description', 'color')
        }),
        ('代码和知识', {
            'fields': ('code_snippet', 'expand_knowledge', 'usage_examples')
        }),
        ('解锁设置', {
            'fields': ('manually_unlocked', 'chapters'),
            'description': '手动解锁：勾选后用户无需完成章节即可使用此积木'
        }),
        ('其他设置', {
            'fields': ('order', 'is_active')
        }),
    )
    
    def get_related_chapters_count(self, obj):
        return obj.chapters.count()
    get_related_chapters_count.short_description = _('関連チャプター数')

@admin.register(ArchitectureSlot)
class ArchitectureSlotAdmin(admin.ModelAdmin):
    list_display = ['name', 'x_position', 'y_position', 'required', 'order']
    list_editable = ['x_position', 'y_position', 'required', 'order']
    list_filter = ['required']
    search_fields = ['name', 'description']

@admin.register(UserArchitecture)
class UserArchitectureAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_public', 'created_at', 'get_assigned_blocks_count']
    list_editable = ['is_public']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username', 'description']
    list_select_related = ['user']
    
    def get_assigned_blocks_count(self, obj):
        return len(obj.slot_assignments)
    get_assigned_blocks_count.short_description = _('割り当て済み積木数')

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'badge_type', 'required_experience', 'required_level',
        'required_chapters', 'required_score',  # ★ 添加 required_score 到列表
        'order', 'is_active'
    ]
    list_editable = ['order', 'is_active']
    list_filter = ['badge_type', 'is_active']
    search_fields = ['name', 'description']

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'badge_type', 'icon', 'color')
        }),
        ('解锁条件', {
            'fields': (
                'required_experience',
                'required_level',
                'required_chapters',
                'required_score',  # ★★ 关键：把 score 放进后台编辑表单
            ),
            'description': '设置至少一个解锁条件'
        }),
        ('显示设置', {
            'fields': ('order', 'is_active')
        }),
    )

@admin.register(StudyGuideAttachment)
class StudyGuideAttachmentAdmin(admin.ModelAdmin):
    list_display = ('study_guide', 'key', 'display_name', 'file')
    list_filter = ('study_guide',)
    search_fields = ('study_guide__chapter__title', 'key', 'display_name')

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'unlocked_at']
    list_filter = ['badge', 'unlocked_at']
    search_fields = ['user__username', 'badge__name']
    readonly_fields = ['unlocked_at']
    date_hierarchy = 'unlocked_at'

# 管理サイトの設定
admin.site.site_header = _('学習管理システム')
admin.site.site_title = _('学習管理システム')
admin.site.index_title = _('管理ダッシュボード')