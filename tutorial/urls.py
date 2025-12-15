# urls.py - 优化版
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==================== 基本页面 ====================
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='tutorial/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # ==================== 学习相关 ====================
    path('chapter/<int:chapter_id>/', views.chapter_detail, name='chapter_detail'),
    path('chapter/<int:chapter_id>/reset/', views.reset_chapter_progress, name='reset_chapter_progress'),
    path('chapter/<int:chapter_id>/mark_guide_studied/', views.mark_guide_studied, name='mark_guide_studied'),
    path('chapter/<int:chapter_id>/complete/', views.complete_chapter, name='complete_chapter'),
    path('question/<int:question_id>/submit/', views.submit_answer, name='submit_answer'),
    path('question/<int:question_id>/hint/', views.get_question_hint, name='get_question_hint'),
    path('chapters/<int:chapter_id>/record_result/',views.record_chapter_result,name='record_chapter_result'),

    # ==================== 错题管理 ====================
    path('wrong-answers/', views.wrong_answers_book, name='wrong_answers_book'),
    path('wrong-answer/<int:wrong_answer_id>/delete/', views.delete_wrong_answer, name='delete_wrong_answer'),
    path('wrong-answers/chapter/<int:chapter_id>/clear/', views.clear_chapter_wrong_answers, name='clear_chapter_wrong_answers'),

    # ==================== 学習時間管理 ====================
    path('chapter/<int:chapter_id>/start-study/', views.start_chapter_study, name='start_chapter_study'),
    path('chapter/<int:chapter_id>/end-study/', views.end_chapter_study, name='end_chapter_study'),
    path('chapter/<int:chapter_id>/update-study-time/', views.update_study_time, name='update_study_time'),
    path('cleanup-study-sessions/', views.cleanup_study_sessions, name='cleanup_study_sessions'),

    # ==================== 进度和统计 ====================
    path('profile/levels/', views.level_profile, name='level_profile'),
    path('experience-stats/', views.experience_stats, name='experience_stats'),
    path('check-badges/', views.check_badges, name='check_badges'),
    path('force_check_badges/', views.force_check_badges, name='force_check_badges'),

    # ==================== 积木和架构图 ====================
    path('blocks/', views.building_blocks, name='building_blocks'),
    path('blocks/home/', views.building_blocks_home, name='building_blocks_home'),
    path('blocks/library/', views.block_library, name='block_library'),
    path('block-detail/<int:block_id>/', views.block_detail, name='block_detail'),
    path('architecture/documentation/', views.architecture_documentation, name='architecture_documentation'),

    # ==================== API 端点 ====================
    # 积木分配相关API
    path('api/assign-block-to-slot/', views.assign_block_to_slot, name='api_assign_block_to_slot'),
    path('api/remove-block-from-slot/<int:slot_id>/', views.remove_block_from_slot, name='api_remove_block_from_slot'),
    path('api/reset-architecture/', views.reset_architecture, name='api_reset_architecture'),
    path('api/generate-architecture-code/', views.generate_architecture_code, name='api_generate_architecture_code'),
    path('api/block-detail/<int:block_id>/', views.block_detail_api, name='api_block_detail'),
    
    # 架构图管理API
    path('api/save-architecture/', views.save_architecture, name='api_save_architecture'),
    path('api/save-architecture-state/', views.save_architecture_state, name='api_save_architecture_state'),
    path('api/user-architectures/', views.get_user_architectures, name='api_user_architectures'),
    path('api/load-architecture/<int:architecture_id>/', views.load_architecture, name='api_load_architecture'),
    path('api/delete-architecture/<int:architecture_id>/', views.delete_architecture, name='api_delete_architecture'),
    path('api/get-architecture-data/', views.get_architecture_data, name='api_get_architecture_data'),
    path('api/save-layer-layout/', views.save_layer_layout, name='save_layer_layout'),

    # 积木分类和预览API
    path('api/block-categories/', views.get_block_categories, name='api_block_categories'),
    path('api/architecture-preview/', views.get_architecture_preview, name='api_architecture_preview'),
]

