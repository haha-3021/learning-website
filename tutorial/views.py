from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Max, Exists, OuterRef, Sum
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
import logging

from .models import (
    Chapter,StudyGuide,Question,Choice,UserProgress,UserProfile,WrongAnswer,BuildingBlock,ArchitectureSlot,
    UserArchitecture,ArchitectureTemplate,ChapterStudyTime,ArchitectureDiagramTemplate,DiagramComponent,
    ChapterResult,UserBadge,Badge,UserQuestionAnswer
)

from .forms import RegisterForm

logger = logging.getLogger(__name__)

# ==================== 基本ページビュー ====================

def home(request):
    """
    ホームページビュー
    """
    try:
        # すべてのアクティブなチャプターを取得
        chapters = Chapter.objects.filter(is_active=True).order_by('order')
        
        # --- 【追加】ガイド表示判定のロジック ---
        show_guide = False
        if request.user.is_authenticated:
            # セッションに 'guide_seen' が無い場合だけ、ガイドを表示対象にする
            if not request.session.get('guide_seen', False):
                show_guide = True
                # 一度表示対象になったら、セッションに記録して次からは出さない
                request.session['guide_seen'] = True
        # --------------------------------------

        # ユーザーがログインしている場合、進捗情報を取得
        chapters_with_progress = []
        if request.user.is_authenticated:
            for chapter in chapters:
                try:
                    progress = UserProgress.objects.get(user=request.user, chapter=chapter)
                    progress_width = 100 if progress.completed else (50 if progress.studied_guide else 0)
                except UserProgress.DoesNotExist:
                    progress_width = 0
                
                chapters_with_progress.append({
                    'chapter': chapter,
                    'progress_width': progress_width
                })
        else:
             # 未ログインユーザーにはデフォルトの進捗を表示
            chapters_with_progress = [{'chapter': chapter, 'progress_width': 0} for chapter in chapters]
        
        context = {
            'chapters_with_progress': chapters_with_progress,
            'show_guide': show_guide  # 【追加】テンプレートに伝える
        }
        return render(request, 'tutorial/home.html', context)
    
    except Exception as e:
        logger.error(f"ホームページ読み込みエラー: {e}")
        return render(request, 'home.html', {
            'chapters_with_progress': [],
            'error': '学習コンテンツの読み込み中にエラーが発生しました'
        })

def register(request):
    """
    ユーザー登録ビュー
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                # ユーザープロファイルが作成されていることを確認
                if not hasattr(user, 'userprofile'):
                    UserProfile.objects.create(user=user)

                messages.success(
                    request,
                    f'アカウント {username} が正常に作成されました！Python学習システムへようこそ！'
                )
                return redirect('home')
            else:
                messages.error(request, 'ログインに失敗しました。再試行してください。')
        else:
            messages.error(request, '登録情報に誤りがあります。確認して再送信してください。')
    else:
        form = RegisterForm()

    return render(request, 'tutorial/register.html', {'form': form})

# ==================== 学習関連ビュー  ====================
@login_required
def chapter_detail(request, chapter_id):
    # 1. 获取当前章节
    chapter = Chapter.objects.filter(id=chapter_id, is_active=True).first()
    if chapter is None:
        messages.error(request, "指定されたチャプターが見つかりません。")
        return redirect("home")

    logger.info(f"[chapter_detail] user={request.user} chapter={chapter.title}")

    # 2. 学习计时逻辑
    study_session = None
    try:
        study_session = ChapterStudyTime.objects.filter(
            user=request.user,
            chapter=chapter,
            end_time__isnull=True
        ).first()

        if study_session is None:
            try:
                ChapterStudyTime.objects.filter(
                    user=request.user,
                    end_time__isnull=True
                ).exclude(chapter=chapter).update(end_time=timezone.now())
            except Exception as inner_e:
                logger.error(f"[chapter_detail] 古いセッション終了エラー: {inner_e}", exc_info=True)

            study_session = ChapterStudyTime.objects.create(
                user=request.user,
                chapter=chapter,
                start_time=timezone.now(),
            )
    except Exception as e:
        logger.error(f"[chapter_detail] 学習セッション准备エラー: {e}", exc_info=True)
        study_session = None

    # 3. 获取学习指南
    try:
        study_guide = StudyGuide.objects.filter(chapter=chapter, is_published=True).first()
    except Exception as e:
        logger.error(f"[chapter_detail] 学習ガイド取得エラー: {e}", exc_info=True)
        study_guide = None

    # 4. 获取问题列表
    try:
        questions = Question.objects.filter(chapter=chapter, is_active=True).order_by("order")
    except Exception as e:
        logger.error(f"[chapter_detail] 问题取得エラー: {e}", exc_info=True)
        questions = Question.objects.none()

    # 4.5 读取用户之前的回答
    try:
        user_answers_qs = UserQuestionAnswer.objects.filter(
            user=request.user,
            question__chapter=chapter
        ).select_related("question")
        answers_by_qid = {ua.question_id: ua for ua in user_answers_qs}
        for q in questions:
            ua = answers_by_qid.get(q.id)
            if ua:
                q.user_answer = ua.answer_text
                q.user_is_correct = ua.is_correct
            else:
                q.user_answer = ""
                q.user_is_correct = None
    except Exception as e:
        logger.error(f"[chapter_detail] 用户回答取得エラー: {e}", exc_info=True)

    # 5. 获取进度
    try:
        user_progress, _ = UserProgress.objects.get_or_create(user=request.user, chapter=chapter)
    except Exception as e:
        logger.error(f"[chapter_detail] 进捗取得エラー: {e}", exc_info=True)
        user_progress = None

    all_chapters = list(Chapter.objects.filter(is_active=True).order_by('order', 'id'))
    next_chapter = None
    try:
        current_index = all_chapters.index(chapter)
        if current_index < len(all_chapters) - 1:
            next_chapter = all_chapters[current_index + 1]
    except (ValueError, IndexError):
        next_chapter = None

    # 6. 渲染
    context = {
        "chapter": chapter,
        "study_guide": study_guide,
        "questions": questions,
        "user_progress": user_progress,
        "current_session_id": study_session.id if study_session else None,
        "next_chapter": next_chapter,
    }

    try:
        return render(request, "tutorial/chapter_detail.html", context)
    except Exception as e:
        logger.error(f"[chapter_detail] テンプレートエラー: {e}", exc_info=True)
        return HttpResponse(f"Error: {e}")

@login_required
@require_http_methods(["POST"])
def update_study_time(request, chapter_id):
    """
    更新学习时间（用于自动保存）
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        data = json.loads(request.body)
        study_session_id = data.get('study_session_id')
        frontend_seconds = data.get('frontend_seconds', 0)
        is_auto_save = data.get('is_auto_save', False)
        
        logger.info(f"更新学习时间: 用户={request.user}, 章节={chapter_id}, 前端秒数={frontend_seconds}, 自动保存={is_auto_save}")
        
        if study_session_id:
            study_session = get_object_or_404(
                ChapterStudyTime, 
                id=study_session_id, 
                user=request.user,
                chapter=chapter
            )
            
            current_db_seconds = study_session.total_seconds or 0
            study_session.total_seconds = max(int(frontend_seconds), current_db_seconds, 1)
            study_session.save()
            
            return JsonResponse({
                'success': True,
                'message': '学習時間を更新しました',
                'study_time': study_session.get_duration_display()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '学習セッションが見つかりません'
            })
            
    except Exception as e:
        logger.error(f"学習時間更新失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'学習時間の更新に失敗しました: {str(e)}'
        })
    
@login_required
@require_http_methods(["POST"])
def cleanup_study_sessions(request):
    """
    清理用户的所有活跃学习会话
    """
    try:
        active_sessions = ChapterStudyTime.objects.filter(
            user=request.user,
            end_time__isnull=True
        )
        
        count = active_sessions.count()
        now = timezone.now()
        
        for session in active_sessions:
            if session.start_time:
                time_diff = now - session.start_time
                session.total_seconds = max(int(time_diff.total_seconds()), 1)
            session.end_time = now
            session.save()
        
        return JsonResponse({
            'success': True,
            'message': f'清理了 {count} 个活跃会话'
        })
        
    except Exception as e:
        logger.error(f"清理学习会话失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'清理失败: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def get_question_hint(request, question_id):
    """
    問題のヒントを取得
    """
    try:
        question = get_object_or_404(Question, id=question_id)
        
        if not question.hint:
            return JsonResponse({
                'success': False,
                'message': 'この問題にはヒントがありません'
            })
        
        return JsonResponse({
            'success': True,
            'hint': question.hint
        })
    
    except Exception as e:
        logger.error(f"ヒント取得エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'ヒントの取得中にエラーが発生しました: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def start_chapter_study(request, chapter_id):
    """
    チャプター学習開始時間を記録
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # このユーザーとチャプターの未完了の学習記録を終了
        ChapterStudyTime.objects.filter(
            user=request.user,
            chapter=chapter,
            end_time__isnull=True
        ).update(end_time=timezone.now())
        
        # 新しい学習記録を作成
        study_session = ChapterStudyTime.objects.create(
            user=request.user,
            chapter=chapter,
            start_time=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'study_session_id': study_session.id,
            'message': '学習時間記録を開始しました'
        })
        
    except Exception as e:
        logger.error(f"学習時間記録開始失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'学習時間記録の開始に失敗しました: {str(e)}'
        })
    
@login_required
@require_http_methods(["POST"])
def end_chapter_study(request, chapter_id):
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        data = json.loads(request.body or "{}")
        study_session_id = data.get('study_session_id')
        
        # 核心：前端传过来的绝对秒数
        frontend_seconds = int(data.get('frontend_seconds', 0))

        if study_session_id:
            study_session = get_object_or_404(
                ChapterStudyTime, id=study_session_id, user=request.user, chapter=chapter
            )
        else:
            study_session = ChapterStudyTime.objects.filter(
                user=request.user, chapter=chapter, end_time__isnull=True
            ).order_by('-start_time').first()

        if not study_session:
            return JsonResponse({'success': False, 'message': 'Session not found'}, status=400)

        now = timezone.now()
        study_session.end_time = now

        # 计算后端存活时间作为兜底
        backend_duration = int((now - study_session.start_time).total_seconds())
        
        # --- 修复逻辑 ---
        # 既然你遇到了 1 秒的问题，说明 frontend_seconds 传值可能在某次调用中被清零了
        # 我们取：已有值、前端传值、后端计算值 三者中的最大值，确保时间只能增加不能减少
        current_db_val = study_session.total_seconds or 0
        study_session.total_seconds = max(frontend_seconds, backend_duration, current_db_val)
        
        study_session.save()

        # 5. ★ここで「その時点の回答状況」からチャプター結果を自動記録する ★
        try:
            answers_qs = UserQuestionAnswer.objects.filter(
                user=request.user,
                question__chapter=chapter,
            )

            total = answers_qs.count()
            correct = answers_qs.filter(is_correct=True).count()

            if total > 0:
                accuracy = int(correct / total * 100)

                ChapterResult.objects.create(
                    user=request.user,
                    chapter=chapter,
                    correct_count=correct,
                    total_count=total,
                    accuracy=accuracy,
                )

                user_progress, _ = UserProgress.objects.get_or_create(
                    user=request.user,
                    chapter=chapter,
                )
                if accuracy > user_progress.score:
                    user_progress.score = accuracy
                    user_progress.save()

                logger.info(
                    f"[end_chapter_study] 自動記録成功: user={request.user}, chapter={chapter.id}"
                )
            else:
                logger.info(
                    f"[end_chapter_study] 自動記録スキップ: 回答数0 user={request.user}"
                )

        except Exception as e2:
            logger.error(f"[end_chapter_study] 結果記録エラー: {e2}", exc_info=True)

        # 6. レスポンス
        return JsonResponse({
            'success': True,
            'message': '学習時間記録を終了しました',
            'study_time': study_session.get_duration_display(),
            'recorded_seconds': study_session.total_seconds
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def clear_chapter_wrong_answers(request, chapter_id):
    """
    チャプターのすべての誤答記録を削除するビュー
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)

        deleted_count, _ = WrongAnswer.objects.filter(
            user=request.user,
            question__chapter=chapter
        ).delete()

        return JsonResponse({
            "success": True,
            "message": f"{deleted_count}件の誤答記録を削除しました"
        })

    except Exception as e:
        logger.error(f"誤答記録削除失敗: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "message": f"誤答記録の削除に失敗しました: {str(e)}"
        }, status=500)

@login_required
def wrong_answers_book(request):
    """
    間違いノート（学習時間と正答率の集計画面）
    """
    try:
        user = request.user

        # 1. 累计得分计算
        total_correct = UserQuestionAnswer.objects.filter(user=user, is_correct=True).count()
        total_score = total_correct * 10

        # 2. 全误答记录
        wrong_answers_qs = WrongAnswer.objects.filter(user=user).select_related(
            'question', 'question__chapter'
        ).order_by('-created_at')
        total_wrong = wrong_answers_qs.count()

        # 3. 【核心修改】日别学习时长统计 (最近7天)
        today = timezone.now().date()
        # 创建一个包含最近7天日期的列表 (用于补全没数据的日期)
        date_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
        
        # 从数据库聚合数据
        daily_stats = ChapterStudyTime.objects.filter(
            user=user, 
            start_time__date__gte=date_list[0],
            total_seconds__gt=0
        ).annotate(
            date=TruncDate('start_time')
        ).values('date').annotate(
            total_daily_seconds=Sum('total_seconds')
        ).order_by('date')

        # 映射数据 {datetime.date: seconds}
        stats_map = {stat['date']: stat['total_daily_seconds'] for stat in daily_stats}

        chart_labels = []
        chart_values = []
        daily_breakdown = []

        for d in date_list:
            sec = int(stats_map.get(d, 0))
            
            # --- 修改 1: 图表数值改用“秒”，解决 0.01 的尴尬 ---
            chart_labels.append(d.strftime('%m/%d'))
            chart_values.append(sec)  # 直接传入原始秒数
            
            # --- 修改 2: 列表文字显示优化 ---
            if sec == 0:
                display_time_str = "0秒"
            elif sec < 60:
                display_time_str = f"{sec}秒"
            else:
                m = sec // 60
                s = sec % 60
                display_time_str = f"{m}分{s}秒"

            daily_breakdown.append({
                'date_str': d.strftime('%Y/%m/%d'),
                'day_name': ['月','火','水','木','金','土','日'][d.weekday()],
                'display_time': display_time_str,  # 使用我们优化的格式
                'is_today': d == today,
                'has_data': sec > 0
            })

        # 4. 章节统计 (为了兼容你原来的章节列表显示)
        chapter_seconds_map = {}
        total_seconds = 0
        completed_sessions = ChapterStudyTime.objects.filter(user=user, total_seconds__gt=0)
        for session in completed_sessions:
            dur = session.total_seconds or 0
            total_seconds += dur
            chapter_seconds_map[session.chapter_id] = chapter_seconds_map.get(session.chapter_id, 0) + dur

        # 5. 组装章节误答数据 (维持原样)
        wrong_by_chapter = {}
        for wa in wrong_answers_qs:
            cid = wa.question.chapter_id
            wrong_by_chapter.setdefault(cid, []).append(wa)

        chapters_with_wrong_answers = []
        for cid, wa_list in wrong_by_chapter.items():
            chapter = wa_list[0].question.chapter
            total_questions = Question.objects.filter(chapter=chapter).count()
            unique_wrong = len({wa.question_id for wa in wa_list})
            accuracy = int((total_questions - unique_wrong) / total_questions * 100) if total_questions > 0 else 0
            
            chapters_with_wrong_answers.append({
                'chapter': chapter,
                'wrong_answers': wa_list,
                'study_time': str(timedelta(seconds=int(chapter_seconds_map.get(cid, 0)))),
                'accuracy': accuracy,
            })

        # 6. 其他汇总数据
        total_questions_all = Question.objects.filter(chapter_id__in=chapter_seconds_map.keys()).count()
        global_accuracy = None
        if total_questions_all > 0:
            unique_wrong_all = len({wa.question_id for wa in wrong_answers_qs})
            global_accuracy = int(max(total_questions_all - unique_wrong_all, 0) / total_questions_all * 100)

        context = {
            'chapters_with_wrong_answers': chapters_with_wrong_answers,
            'total_wrong_answers': total_wrong,
            'total_study_time': str(timedelta(seconds=int(total_seconds))),
            'global_accuracy': global_accuracy,
            'total_score': total_score,
            'daily_breakdown': daily_breakdown,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_values_json': json.dumps(chart_values),
        }
        return render(request, 'tutorial/wrong_answers_book.html', context)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return redirect('home')
@login_required
@require_http_methods(["POST"])
def mark_guide_studied(request, chapter_id):
    """
    学習ガイドを学習済みとしてマーク
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            chapter=chapter
        )
        user_progress.studied_guide = True
        user_progress.save()
        
        return JsonResponse({'success': True, 'message': '学習ガイドを学習済みとしてマークしました'})
    
    except Exception as e:
        logger.error(f"学習ガイドマークエラー: {e}")
        return JsonResponse({'success': False, 'message': '操作が失敗しました'})

@login_required
@require_http_methods(["POST"])
def submit_answer(request, question_id):
    """
    問題の回答を提出
    """
    try:
        question = get_object_or_404(Question, id=question_id)
        user_answer = request.POST.get('answer', '')
        
        is_correct = False
        correct_answer_text = ""
        error_message = ""
        
        # 問題タイプに基づいて回答を検証
        if question.question_type == 'choice':
            # 選択問題のロジック
            selected_choice = get_object_or_404(Choice, id=user_answer)
            is_correct = selected_choice.is_correct
            
            # 正解テキストを取得
            correct_choices = question.choice_set.filter(is_correct=True)
            correct_answer_text = ", ".join([choice.choice_text for choice in correct_choices])
            
            if not is_correct:
                error_message = "選択が間違っています"
                # 誤答を記録
                WrongAnswer.objects.create(
                    user=request.user,
                    question=question,
                    wrong_answer=selected_choice.choice_text,
                    correct_answer=correct_answer_text
                )
        
        elif question.question_type == 'fill':
            # 空欄問題のロジック
            correct_choices = question.choice_set.filter(
                is_correct=True, 
                blank_index=0
            )
            
            # ユーザー回答が正解と一致するかチェック
            user_answer_clean = user_answer.strip().lower()
            for choice in correct_choices:
                correct_answer_clean = choice.choice_text.strip().lower()
                if user_answer_clean == correct_answer_clean:
                    is_correct = True
                    correct_answer_text = choice.choice_text
                    break
            
            if not is_correct:
                error_message = "回答が正しくありません"
                # 记录错题
                correct_answer_display = ", ".join([choice.choice_text for choice in correct_choices])
                WrongAnswer.objects.create(
                    user=request.user,
                    question=question,
                    wrong_answer=user_answer,
                    correct_answer=correct_answer_display
                )
        
        elif question.question_type == 'multi_fill':
            # 複数空欄問題のロジック
            user_answers = user_answer.split(',')
            is_correct = True
            correct_answers_by_blank = {}
            
            # 各空欄の正解を取得
            for i in range(len(user_answers)):
                correct_choices = question.choice_set.filter(
                    is_correct=True, 
                    blank_index=i
                )
                correct_answers_by_blank[i] = [choice.choice_text.strip().lower() for choice in correct_choices]
            
            # 各回答を検証
            for i, user_ans in enumerate(user_answers):
                user_ans_clean = user_ans.strip().lower()
                if i in correct_answers_by_blank and user_ans_clean not in correct_answers_by_blank[i]:
                    is_correct = False
                    break
            
            # 正解テキストを構築
            correct_answer_parts = []
            for i in sorted(correct_answers_by_blank.keys()):
                correct_options = correct_answers_by_blank[i]
                if correct_options:
                    correct_answer_parts.append(f"空{i+1}: {', '.join(correct_options)}")
            correct_answer_text = "; ".join(correct_answer_parts)
            
            if not is_correct:
                error_message = "一部の回答が正しくありません"
                # 誤答を記録
                WrongAnswer.objects.create(
                    user=request.user,
                    question=question,
                    wrong_answer=user_answer,
                    correct_answer=correct_answer_text
                )

        try:
            UserQuestionAnswer.objects.update_or_create(
                user=request.user,
                question=question,
                defaults={
                    "answer_text": user_answer,
                    "is_correct": is_correct,
                }
            )
        except Exception as e:
            logger.error(f"ユーザー回答の保存に失敗しました: {e}")
        
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'explanation': question.explanation,
            'correct_answer': correct_answer_text,
            'message': error_message  # エラーメッセージを追加
        })
    
    except Exception as e:
        logger.error(f"回答提出エラー: {e}")
        return JsonResponse({'success': False, 'message': '回答の送信中にエラーが発生しました'})

@login_required
@require_http_methods(["POST"])
def record_chapter_result(request, chapter_id):
    """
    チャプター練習の結果（1回分）を記録するAPI
    フロントから「正解数」と「問題総数」を送ってもらう
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id, is_active=True)

        # フロントから送られてくる値（例：correct=8, total=10）
        correct = int(request.POST.get('correct', 0))
        total = int(request.POST.get('total', 0))

        if total <= 0:
            return JsonResponse({
                'success': False,
                'message': '問題数が0のため、結果を記録できません。'
            })

        # 正答率（%）を計算
        accuracy = int(correct / total * 100)

        # 1回分の結果を保存
        ChapterResult.objects.create(
            user=request.user,
            chapter=chapter,
            correct_count=correct,
            total_count=total,
            accuracy=accuracy,
        )

        # ついでに UserProgress.score も更新（ベストスコアとして使う想定）
        user_progress, _ = UserProgress.objects.get_or_create(
            user=request.user,
            chapter=chapter
        )
        if accuracy > user_progress.score:
            user_progress.score = accuracy
            user_progress.save()

        return JsonResponse({
            'success': True,
            'accuracy': accuracy,
            'message': 'チャプター結果を記録しました。'
        })

    except Exception as e:
        logger.error(f"チャプター結果記録エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': '結果の記録中にエラーが発生しました。'
        })

@login_required
@require_http_methods(["POST"])
def complete_chapter(request, chapter_id):
    """
    チャプターを完了
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            chapter=chapter
        )
        
        if user_progress.completed:
            return JsonResponse({
                'success': True, 
                'message': 'チャプターは既に完了しています',
                'already_completed': True
            })

        # --- 【追加】レベルアップ判定のための事前準備 ---
        profile = request.user.userprofile
        old_level = profile.level  # 更新前のレベルを保存
        # ------------------------------------------

        # 完了としてマーク
        user_progress.completed = True
        user_progress.score = 100
        user_progress.save()
        
        # ユーザープロファイル情報を取得
        # (models.pyのシグナル等で経験値が入る想定)
        profile.refresh_from_db() # データベースの最新状態（更新後の経験値・レベル）を反映
        level_info = profile.get_level_info()
        
        # --- 【追加】レベルアップの判定 ---
        new_level = profile.level
        is_level_up = new_level > old_level
        # -------------------------------

        response_data = {
            'success': True, 
            'message': f'おめでとうございます！第{chapter.order}章: {chapter.title}を完了しました',
            'level_info': level_info,
            'chapter_completed': True,
            'experience_gained': 50,
            'level_up': is_level_up, # 【変更】判定結果を反映
            'new_level': new_level    # 【追加】新しいレベルを渡す
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"チャプター完了エラー: {e}")
        return JsonResponse({'success': False, 'message': f'操作に失敗しました: {str(e)}'})

@login_required
def reset_chapter_progress(request, chapter_id):
    """
    チャプターの進捗をリセット（学習時間は保持）
    """
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # 1. 進捗（クリア状態）を削除
        UserProgress.objects.filter(user=request.user, chapter=chapter).delete()
        
        # 2. 関連する誤答記録を削除
        WrongAnswer.objects.filter(
            user=request.user,
            question__chapter=chapter
        ).delete()

        # 3. チャプターの途中回答も削除
        UserQuestionAnswer.objects.filter(
            user=request.user,
            question__chapter=chapter
        ).delete()
        
        # 【重要】ChapterStudyTime.objects.filter(...).delete() を「書かない」ことで
        # 学習時間はデータベースに残り続けます。

        # ユーザーに「時間は残っている」ことを伝えて安心させる
        success_msg = f'第{chapter.order}章の進捗をリセットしました。※累計学習時間は保持されます。'
        messages.info(request, success_msg)
        
        return JsonResponse({
            'success': True, 
            'message': success_msg
        })
    
    except Exception as e:
        logger.error(f"進捗リセットエラー: {e}")
        return JsonResponse({'success': False, 'message': 'リセットに失敗しました'})

    
@login_required
def experience_stats(request):
    """
    ユーザーの経験値統計を取得
    """
    try:
        profile = request.user.userprofile
        level_info = profile.get_level_info()
        
        # 完了チャプター統計を取得
        completed_chapters = UserProgress.objects.filter(
            user=request.user, 
            completed=True
        ).count()
        
        total_chapters = Chapter.objects.filter(is_active=True).count()
        
        # 最近の実績を取得
        recent_achievements = profile.get_recent_achievements()
        
        stats = {
            'level_info': level_info,
            'chapters_completed': completed_chapters,
            'total_chapters': total_chapters,
            'completion_rate': (completed_chapters / total_chapters * 100) if total_chapters > 0 else 0,
            'recent_achievements': recent_achievements,
            'rank': calculate_user_rank(request.user)  # 実装可能なランキング関数
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"経験値統計取得エラー: {e}")
        return JsonResponse({'success': False, 'message': '統計の取得に失敗しました'})

def calculate_user_rank(user):
    """ユーザーランキングを計算（簡易版）"""
    # ここにより複雑なランキングロジックを実装可能
    user_exp = user.userprofile.experience
    higher_rank_users = UserProfile.objects.filter(experience__gt=user_exp).count()
    return higher_rank_users + 1

# ==================== 進捗と誤答ビュー ====================

@login_required
def level_profile(request):
    """
    レベルプロファイルページ
    """
    try:
        profile = request.user.userprofile
        
        # レベル関連情報を計算
        exp_required_next = profile.get_exp_for_next_level()
        exp_current_level = profile.experience - ((profile.level - 1) * 100)
        exp_progress = profile.get_exp_progress()
        
        #  チャプター完了状況を取得
        completed_chapters = UserProgress.objects.filter(
            user=request.user, 
            completed=True
        ).count()
        total_chapters = Chapter.objects.filter(is_active=True).count()

        total_correct = UserQuestionAnswer.objects.filter(
            user=request.user,
            is_correct=True
        ).count()
        total_score = total_correct * 10
        
        # === バッジデータ取得の修正 ===
        print(f"=== バッジデータチェック開始 ===")
        
        try:
            from .models import Badge, UserBadge
            
            # すべてのアクティブなバッジを取得
            all_badges = Badge.objects.filter(is_active=True).order_by('order')
            print(f"✅ データベース内のアクティブバッジ総数: {all_badges.count()}")
            
            # ユーザーがアンロックしたバッジを取得
            user_badges = UserBadge.objects.filter(user=request.user)
            print(f"✅ ユーザーがアンロックしたバッジ数: {user_badges.count()}")
            
            # バッジ進捗データを構築
            badges_with_progress = []
            unlocked_count = 0
            
            for badge in all_badges:
                try:
                    # バッジのアンロック状態をチェック
                    is_unlocked = badge.is_unlocked_by_user(request.user)
                    
                    # 進捗データを取得 - エラーハンドリングを追加
                    progress_data = {}
                    try:
                        # メソッドが存在するかチェック
                        if hasattr(profile, 'get_badge_progress'):
                            progress_data = profile.get_badge_progress(badge)
                        else:
                            print(f"⚠️ get_badge_progress メソッドが存在しません、デフォルト進捗データを使用")
                            # デフォルト進捗データを提供
                            progress_data = get_default_badge_progress(profile, badge)
                    except Exception as progress_error:
                        print(f"⚠️ バッジ進捗取得失敗: {progress_error}")
                        progress_data = get_default_badge_progress(profile, badge)
                    
                    # アンロック時間を検索
                    unlocked_at = None
                    for user_badge in user_badges:
                        if user_badge.badge.id == badge.id:
                            unlocked_at = user_badge.unlocked_at
                            break
                    
                    badge_info = {
                        'badge': badge,
                        'is_unlocked': is_unlocked,
                        'progress_data': progress_data,
                        'unlocked_at': unlocked_at,
                    }
                    
                    badges_with_progress.append(badge_info)
                    
                    if is_unlocked:
                        unlocked_count += 1
                    
                    print(f"バッジ '{badge.name}': アンロック状態={is_unlocked}, 進捗データ={bool(progress_data)}")

                except Exception as badge_error:
                    print(f"❌ バッジ  {badge.name} の処理中にエラー: {badge_error}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"✅ 最終バッジデータ: {len(badges_with_progress)} 個, アンロック済み: {unlocked_count} 個")
            
        except Exception as badge_main_error:
            print(f"❌ バッジメインプロセス失敗: {badge_main_error}")
            import traceback
            traceback.print_exc()
            badges_with_progress = []
            unlocked_count = 0
        
        print(f"=== バッジデータチェック終了 ===")
        # === バッジデータチェック終了 ===
        
        level_info = {
            'experience': profile.experience,
            'exp_required_next': exp_required_next,
            'exp_current_level': exp_current_level,
            'exp_progress': exp_progress,
            'chapters_completed': completed_chapters,
            'total_chapters': total_chapters,
            'total_score': total_score,
        }
        
        context = {
            'profile': profile,
            'level_info': level_info,
            'badges_with_progress': badges_with_progress,
            'unlocked_count': unlocked_count,  #  アンロックカウントを追加
        }
        
        return render(request, 'tutorial/level_profile.html', context)
    
    except Exception as e:
        logger.error(f"レベルプロファイル読み込みエラー: {e}")
        print(f"❌ レベルプロファイルエラー: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'レベルプロファイルの読み込み中にエラーが発生しました')
        return redirect('home')

def get_default_badge_progress(profile, badge):
    """デフォルトのバッジ進捗データを取得"""
    progress_data = {}
    
    # 経験値条件の進捗をチェック
    if badge.required_experience > 0:
        progress_percent = min((profile.experience / badge.required_experience) * 100, 100) if badge.required_experience > 0 else 0
        progress_data['experience'] = {
            'current': profile.experience,
            'required': badge.required_experience,
            'progress': progress_percent
        }
    
    # レベル条件の進捗をチェック
    if badge.required_level > 0:
        progress_percent = min((profile.level / badge.required_level) * 100, 100) if badge.required_level > 0 else 0
        progress_data['level'] = {
            'current': profile.level,
            'required': badge.required_level,
            'progress': progress_percent
        }
    
    # チャプター条件の進捗をチェック
    if badge.required_chapters > 0:
        progress_percent = min((profile.total_chapters_completed / badge.required_chapters) * 100, 100) if badge.required_chapters > 0 else 0
        progress_data['chapters'] = {
            'current': profile.total_chapters_completed,
            'required': badge.required_chapters,
            'progress': progress_percent
        }
    
    return progress_data

@login_required
@require_http_methods(["POST"])
def delete_wrong_answer(request, wrong_answer_id):
    """
    誤答記録を削除
    """
    try:
        wrong_answer = get_object_or_404(WrongAnswer, id=wrong_answer_id, user=request.user)
        wrong_answer.delete()
        
        return JsonResponse({'success': True, 'message': '誤答記録を削除しました'})
    
    except Exception as e:
        logger.error(f"誤答削除エラー: {e}")
        return JsonResponse({'success': False, 'message': '削除に失敗しました'})

# ==================== ブロックとアーキテクチャ図ビュー ====================

@login_required
def building_blocks(request):
    """
    ブロックページメインビュー
    """
    try:
        # すべてのアクティブなブロックを取得
        all_blocks = BuildingBlock.objects.filter(is_active=True)
        
        # アンロック済みとロックされたブロックを分離
        unlocked_blocks = []
        locked_blocks = []
        
        for block in all_blocks:
            if block.is_unlocked_for_user(request.user):
                unlocked_blocks.append(block)
            else:
                locked_blocks.append(block)
        
        # ユーザーのアーキテクチャスロットを取得または作成
        slots_with_assignments = get_user_architecture_slots(request.user)
        
        # チャプター完了状況を計算
        chapters_completed = get_completed_chapters_count(request.user)
        total_chapters = get_total_chapters_count()
        
        context = {
            'unlocked_blocks': unlocked_blocks,
            'locked_blocks': locked_blocks,
            'slots_with_assignments': slots_with_assignments,
            'chapters_completed': chapters_completed,
            'total_chapters': total_chapters,
        }
        
        return render(request, 'tutorial/building_blocks.html', context)
    
    except Exception as e:
        logger.error(f"積木ページ読み込みエラー: {e}")
        # エラーハンドリング - デフォルトデータを提供
        context = {
            'unlocked_blocks': BuildingBlock.objects.filter(is_active=True)[:5],
            'locked_blocks': [],
            'slots_with_assignments': [],
            'chapters_completed': 0,
            'total_chapters': Chapter.objects.filter(is_active=True).count(),
        }
        return render(request, 'tutorial/building_blocks.html', context)

@login_required
def block_detail(request, block_id):
    """
    ブロック詳細ページ
    """
    try:
        block = get_object_or_404(BuildingBlock, id=block_id)
        
        # ユーザーがこのブロックをアンロックしているかチェック
        if not block.is_unlocked_for_user(request.user):
            messages.warning(request, 'この積木はまだアンロックされていません')
            return redirect('building_blocks')
        
        context = {
            'block': block
        }
        return render(request, 'block_detail.html', context)
    
    except Exception as e:
        logger.error(f"ブロック詳細読み込みエラー: {e}")
        messages.error(request, 'ブロック詳細の読み込み中にエラーが発生しました')
        return redirect('tutorial/building_blocks')
    
@login_required
def get_architecture_data(request):
    """获取架构图数据"""
    try:
        # 创建或获取默认架构图
        diagram, created = ArchitectureDiagramTemplate.objects.get_or_create(
            name="物品管理系统架构图",
            defaults={
                'description': '基于Django的物品管理系统标准架构',
                'layers': [
                    {'name': 'HTTP层',   'color': '#3B82F6', 'order': 0, 'x': 100, 'y': 200, 'size': 160},
                    {'name': 'URL路由层', 'color': '#10B981', 'order': 1, 'x': 320, 'y': 200, 'size': 160},
                    {'name': '视图层',   'color': '#8B5CF6', 'order': 2, 'x': 540, 'y': 200, 'size': 160},
                    {'name': '表单层',   'color': '#EC4899', 'order': 3, 'x': 760, 'y': 200, 'size': 160},
                    {'name': '模型层',   'color': '#EF4444', 'order': 4, 'x': 980, 'y': 200, 'size': 160},
                    {'name': '模板层',   'color': '#06B6D4', 'order': 5, 'x': 1200,'y': 200, 'size': 160},
                ],
                'connections': [
                    {'from': 'http_request', 'to': 'url_router', 'type': 'solid'},
                    {'from': 'url_items', 'to': 'item_list_view', 'type': 'solid'},
                    {'from': 'url_add', 'to': 'item_create_view', 'type': 'solid'},
                    {'from': 'url_detect', 'to': 'item_delete_view', 'type': 'solid'},
                    {'from': 'item_list_view', 'to': 'item_model', 'type': 'solid'},
                    {'from': 'item_create_view', 'to': 'item_form', 'type': 'solid'},
                    {'from': 'item_delete_view', 'to': 'item_model', 'type': 'solid'},
                    {'from': 'item_form', 'to': 'item_model', 'type': 'solid'},
                    {'from': 'item_list_view', 'to': 'item_list_template', 'type': 'dashed'},
                    {'from': 'item_create_view', 'to': 'item_form_template', 'type': 'dashed'},
                ]
            }
        )
        
        # 如果新创建，则初始化组件
        if created:
            components_data = [
                # HTTP层
                {'name': 'HTTP请求', 'type': 'http_request', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#3B82F6', 'layer': 'HTTP层', 'allowed_types': ['url'], 'order': 0},
        
                # URL路由层
                {'name': 'URL路由器', 'type': 'url_router', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#10B981', 'layer': 'URL路由层', 'allowed_types': ['url'], 'order': 0},
                {'name': '/items/', 'type': 'url_items', 'x': 200, 'y': 10, 'width': 100, 'height': 40, 'color': '#10B981', 'layer': 'URL路由层', 'allowed_types': ['view'], 'order': 1},
                {'name': '/items/add/', 'type': 'url_add', 'x': 330, 'y': 10, 'width': 100, 'height': 40, 'color': '#10B981', 'layer': 'URL路由层', 'allowed_types': ['view'], 'order': 2},
                {'name': '/items/detect/', 'type': 'url_detect', 'x': 460, 'y': 10, 'width': 100, 'height': 40, 'color': '#10B981', 'layer': 'URL路由层', 'allowed_types': ['view'], 'order': 3},
        
                # 视图层
                {'name': 'ItemListView', 'type': 'item_list_view', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#8B5CF6', 'layer': '视图层', 'allowed_types': ['view'], 'order': 0},
                {'name': 'ItemCreateView', 'type': 'item_create_view', 'x': 200, 'y': 10, 'width': 120, 'height': 60, 'color': '#8B5CF6', 'layer': '视图层', 'allowed_types': ['view'], 'order': 1},
                {'name': 'ItemDeleteView', 'type': 'item_delete_view', 'x': 350, 'y': 10, 'width': 120, 'height': 60, 'color': '#8B5CF6', 'layer': '视图层', 'allowed_types': ['view'], 'order': 2},
        
                # 表单层
                {'name': 'ItemForm', 'type': 'item_form', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#EC4899', 'layer': '表单层', 'allowed_types': ['form'], 'order': 0},
        
                # 模型层
                {'name': 'Item模型', 'type': 'item_model', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#EF4444', 'layer': '模型层', 'allowed_types': ['data_model'], 'order': 0},
        
                # 模板层
                {'name': 'item_list.html', 'type': 'item_list_template', 'x': 50, 'y': 10, 'width': 120, 'height': 60, 'color': '#06B6D4', 'layer': '模板层', 'allowed_types': ['template'], 'order': 0},
                {'name': '表单模板', 'type': 'item_form_template', 'x': 200, 'y': 10, 'width': 120, 'height': 60, 'color': '#06B6D4', 'layer': '模板层', 'allowed_types': ['template'], 'order': 1},
            ]

            for comp_data in components_data:
                DiagramComponent.objects.create(
                    diagram=diagram,
                    name=comp_data['name'],
                    component_type=comp_data['type'],
                    position_x=comp_data['x'],
                    position_y=comp_data['y'],
                    width=comp_data['width'],
                    height=comp_data['height'],
                    color=comp_data['color'],
                    allowed_block_types=comp_data['allowed_types'],
                    layer=comp_data['layer'],
                    order=comp_data['order']
                )
        
        # 获取组件数据
        components = DiagramComponent.objects.filter(diagram=diagram)
        components_list = []
        for comp in components:
            components_list.append({
                'id': comp.id,
                'name': comp.name,
                'type': comp.component_type,
                'position': {'x': comp.position_x, 'y': comp.position_y},
                'size': {'width': comp.width, 'height': comp.height},
                'color': comp.color,
                'allowed_block_types': comp.allowed_block_types,
                'layer': comp.layer
            })

        for idx, layer in enumerate(diagram.layers):
            layer.setdefault('x', 100 + idx * 220)
            layer.setdefault('y', 200)
            layer.setdefault('size', 160)
        
        return JsonResponse({
            'success': True,
            'diagram': {
                'name': diagram.name,
                'description': diagram.description,
                'layers': diagram.layers,
                'components': components_list,
                'connections': diagram.connections
            }
        })
        
    except Exception as e:
        logger.error(f"获取架构图数据错误: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取架构图数据失败: {str(e)}'
        })
    
@login_required
@require_http_methods(["POST"])
def save_layer_layout(request):
    """
    保存架构层的布局（位置/尺寸），写回 ArchitectureDiagramTemplate.layers JSON
    传入数据格式：
    {
      "layers": [
        {"name": "HTTP层", "x": 120, "y": 260, "size": 160},
        ...
      ]
    }
    """
    try:
        payload = json.loads(request.body)
        incoming_layers = payload.get('layers', [])

        diagram = ArchitectureDiagramTemplate.objects.get(name="物品管理系统架构图")
        # 现有层做映射：按 name 合并位置
        existing = {l['name']: l for l in diagram.layers}
        for item in incoming_layers:
            name = item.get('name')
            if not name or name not in existing:
                continue
            existing[name]['x'] = int(item.get('x', existing[name].get('x', 0)))
            existing[name]['y'] = int(item.get('y', existing[name].get('y', 0)))
            existing[name]['size'] = int(item.get('size', existing[name].get('size', 160)))

        # 写回列表（维持原顺序）
        updated_layers = [existing[l['name']] for l in diagram.layers]
        diagram.layers = updated_layers
        diagram.save()

        return JsonResponse({'success': True, 'message': '布局已保存'})
    except Exception as e:
        logger.error(f"保存布局失败: {e}")
        return JsonResponse({'success': False, 'message': f'保存失败: {str(e)}'})

# ==================== ブロックシステムAPIビュー ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def assign_block_to_slot(request):
    """
    API: ブロックをスロットに割り当て
    """
    try:
        data = json.loads(request.body)
        slot_id = data.get('slot_id')
        block_id = data.get('block_id')
        
        # スロットとブロックを取得
        slot = get_object_or_404(ArchitectureSlot, id=slot_id)
        block = get_object_or_404(BuildingBlock, id=block_id)
        
        # ブロックタイプが一致するかチェック
        if block.block_type not in slot.allowed_block_types:
            return JsonResponse({
                'success': False, 
                'message': f'ブロックタイプが一致しません。このスロットで許可されているタイプ: {", ".join(slot.allowed_block_types)}'
            })
        
        # ユーザーのアーキテクチャ図を取得または作成
        user_architecture, created = UserArchitecture.objects.get_or_create(
            user=request.user
        )
        
        # ブロックをスロットに割り当て
        user_architecture.assign_block_to_slot(slot_id, block_id)
        
        return JsonResponse({
            'success': True, 
            'message': 'ブロックの割り当てに成功しました',
            'block_name': block.name
        })
    
    except Exception as e:
        logger.error(f"ブロック割り当てエラー: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'ブロックの割り当て中にエラーが発生しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def remove_block_from_slot(request, slot_id):
    """
    API: スロットからブロックを削除
    """
    try:
        # ユーザーのアーキテクチャ図を取得
        user_architecture = get_object_or_404(UserArchitecture, user=request.user)
        
        # スロットからブロックを削除
        user_architecture.remove_block_from_slot(slot_id)
        
        return JsonResponse({
            'success': True, 
            'message': 'ブロックの削除に成功しました'
        })
    
    except Exception as e:
        logger.error(f"ブロック削除エラー: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'ブロックの削除中にエラーが発生しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def reset_architecture(request):
    """
    API: ユーザーアーキテクチャ図をリセット
    """
    try:
        # ユーザーのアーキテクチャ図を取得
        user_architecture = get_object_or_404(UserArchitecture, user=request.user)
        
        # すべてのスロット割り当てをリセット
        user_architecture.slot_assignments = {}
        user_architecture.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'アーキテクチャ図をリセットしました'
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ図リセットエラー: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'アーキテクチャ図のリセット中にエラーが発生しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def generate_architecture_code(request):
    """
    API: アーキテクチャコードを生成
    """
    try:
        #　ユーザーのアーキテクチャ設定を取得
        user_architecture = get_object_or_404(UserArchitecture, user=request.user)
        assigned_blocks = user_architecture.get_assigned_blocks()
        
        architecture_data = []
        
        for slot_id, block in assigned_blocks.items():
            architecture_data.append({
                'slot_name': f"Slot {slot_id}",
                'block_name': block.name,
                'block_type': block.block_type,
                'code_snippet': block.code_snippet
            })
        
        # コードを生成
        generated_code = generate_code_from_architecture(architecture_data)
        
        #  生成されたコードをユーザーアーキテクチャ図に保存
        user_architecture.generated_code = generated_code
        user_architecture.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'コードの生成に成功しました',
            'generated_code': generated_code
        })
    
    except Exception as e:
        logger.error(f"コード生成エラー: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'コードの生成中にエラーが発生しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_architecture(request):
    """
    API: アーキテクチャ図を保存
    """
    try:
        data = json.loads(request.body)
        name = data.get('name', 'マイアーキテクチャ図')
        description = data.get('description', '')
        
        # ユーザーのアーキテクチャ図を取得
        user_architecture, created = UserArchitecture.objects.get_or_create(user=request.user)
        user_architecture.name = name
        user_architecture.description = description
        user_architecture.save()
        
        return JsonResponse({
            'success': True,
            'message': 'アーキテクチャ図を保存しました'
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ図保存エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図の保存に失敗しました: {str(e)}'
        })
    
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_architecture_state(request):
    """
    API: アーキテクチャ状態を保存（スロット割り当てを含む）
    """
    try:
        data = json.loads(request.body)
        name = data.get('name', 'マイアーキテクチャ図')
        description = data.get('description', '')
        slot_assignments = data.get('slot_assignments', {})
        
        # ユーザーのアーキテクチャ図を取得
        user_architecture, created = UserArchitecture.objects.get_or_create(user=request.user)
        user_architecture.name = name
        user_architecture.description = description
        user_architecture.slot_assignments = slot_assignments
        user_architecture.save()
        
        return JsonResponse({
            'success': True,
            'message': 'アーキテクチャ図を保存しました',
            'architecture_id': user_architecture.id
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ状態保存エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図の保存に失敗しました: {str(e)}'
        })

@login_required
def get_user_architectures(request):
    """
    API: ユーザーのアーキテクチャ図リストを取得
    """
    try:
        architectures = UserArchitecture.objects.filter(user=request.user)
        architectures_list = []
        
        for arch in architectures:
            architectures_list.append({
                'id': arch.id,
                'name': arch.name,
                'description': arch.description,
                'created_at': arch.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': arch.updated_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'architectures': architectures_list
        })
    
    except Exception as e:
        logger.error(f"ユーザーアーキテクチャ図リスト取得エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図の取得に失敗しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def load_architecture(request, architecture_id):
    """
    API: 特定のアーキテクチャ図を読み込む
    """
    try:
        # 指定されたアーキテクチャ図を取得
        user_architecture = get_object_or_404(UserArchitecture, id=architecture_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'アーキテクチャ図を読み込みました',
            'architecture': {
                'id': user_architecture.id,
                'name': user_architecture.name,
                'description': user_architecture.description,
                'slot_assignments': user_architecture.slot_assignments
            }
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ図読み込みエラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図の読み込みに失敗しました: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_architecture(request, architecture_id):
    """
    API:  アーキテクチャ図を削除
    """
    try:
        # 指定されたアーキテクチャ図を取得
        user_architecture = get_object_or_404(UserArchitecture, id=architecture_id, user=request.user)
        
        # デフォルトアーキテクチャ図は削除不可
        if user_architecture.name == "マイアーキテクチャ図":
            return JsonResponse({
                'success': False,
                'message': 'デフォルトのアーキテクチャ図は削除できません'
            })
        
        user_architecture.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'アーキテクチャ図を削除しました'
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ図削除エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図の削除に失敗しました: {str(e)}'
        })

@login_required
def get_block_categories(request):
    """
    API: ブロックカテゴリを取得
    """
    try:
        # すべてのアクティブなブロックを取得
        all_blocks = BuildingBlock.objects.filter(is_active=True)
        
        # タイプ別に分類
        categories = {}
        for block in all_blocks:
            block_type = block.block_type
            if block_type not in categories:
                categories[block_type] = {
                    'name': block.get_block_type_display(),
                    'blocks': []
                }
            
            # ブロックがアンロックされているかチェック
            is_unlocked = block.is_unlocked_for_user(request.user)
            
            categories[block_type]['blocks'].append({
                'id': block.id,
                'name': block.name,
                'description': block.description,
                'is_unlocked': is_unlocked
            })
        
        return JsonResponse({
            'success': True,
            'categories': categories
        })
    
    except Exception as e:
        logger.error(f"ブロックカテゴリ取得エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'積木カテゴリの取得に失敗しました: {str(e)}'
        })

@login_required
def get_architecture_preview(request):
    """
    API: アーキテクチャ図プレビューを取得
    """
    try:
        #　ユーザーのアーキテクチャ図を取得
        user_architecture, created = UserArchitecture.objects.get_or_create(user=request.user)
        assigned_blocks = user_architecture.get_assigned_blocks()
        
        # プレビューデータを構築
        preview_data = {
            'total_blocks': len(assigned_blocks),
            'blocks_by_type': {},
            'architecture_valid': len(assigned_blocks) > 0
        }
        
        for slot_id, block in assigned_blocks.items():
            block_type = block.block_type
            if block_type not in preview_data['blocks_by_type']:
                preview_data['blocks_by_type'][block_type] = 0
            preview_data['blocks_by_type'][block_type] += 1
        
        return JsonResponse({
            'success': True,
            'preview': preview_data
        })
    
    except Exception as e:
        logger.error(f"アーキテクチャ図プレビュー取得エラー: {e}")
        return JsonResponse({
            'success': False,
            'message': f'アーキテクチャ図のプレビュー取得に失敗しました: {str(e)}'
        })

@login_required
def block_detail_api(request, block_id):
    """
    API: ブロック詳細を取得
    """
    try:
        print(f"=== ブロック詳細APIが呼び出されました ===")
        print(f"リクエストユーザー: {request.user}")
        print(f"リクエストブロックID: {block_id}")
        
        block = get_object_or_404(BuildingBlock, id=block_id)
        print(f"ブロックを発見: {block.name}")
        
        # ユーザーがこのブロックをアンロックしているかチェック
        is_unlocked = block.is_unlocked_for_user(request.user)
        print(f"ブロックアンロック状態: {is_unlocked}")
        
        if not is_unlocked:
            print("ブロックがアンロックされていない、エラーを返す")
            return JsonResponse({
                'success': False,
                'message': 'このブロックはまだアンロックされていません'
            })
        
        # 返却データを準備
        block_data = {
            'id': block.id,
            'name': block.name,
            'description': block.description,
            'block_type': block.block_type,
            'block_type_display': block.get_block_type_display(),
            'code_snippet': block.code_snippet or '# コードスニペットが定義されていません',
            'expand_knowledge': block.expand_knowledge or '<p class="no-content">拡張知識はまだ設定されていません<</p>',
            'usage_examples': block.usage_examples or '// 使用例はまだ設定されていません',
            'possible_projects': '<p class="no-content">制作可能なプロジェクトはまだ設定されていません</p>'
        }
        
        print(f"返却データ: {block_data['name']}")
        print("=== ブロック詳細API呼び出し完了 ===")
        
        return JsonResponse({
            'success': True,
            'block': block_data
        })
    
    except Exception as e:
        logger.error(f"ブロック詳細取得エラー: {e}")
        print(f"!!! ブロック詳細APIエラー: {e} !!!")
        return JsonResponse({
            'success': False,
            'message': f'ブロック詳細の取得中にエラーが発生しました: {str(e)}'
        })

# ==================== 補助ページビュー ====================

def building_blocks_home(request):
    """
    ブロックシステムホームページ
    """
    return render(request, 'building_blocks.html')

def architecture_documentation(request):
    """
    アーキテクチャ図ドキュメントページ
    """
    return render(request, 'architecture_documentation.html')

@login_required
def block_library(request):
    """
    ブロックライブラリページ
    """
    try:
        # すべてのブロックを取得しタイプ別に分類
        blocks_by_type = {}
        all_blocks = BuildingBlock.objects.filter(is_active=True).order_by('block_type', 'order')
        
        for block in all_blocks:
            if block.block_type not in blocks_by_type:
                blocks_by_type[block.block_type] = {
                    'display_name': block.get_block_type_display(),
                    'blocks': []
                }
            
            blocks_by_type[block.block_type]['blocks'].append(block)
        
        context = {
            'blocks_by_type': blocks_by_type,
            'total_blocks': all_blocks.count()
        }
        
        return render(request, 'block_library.html', context)
    
    except Exception as e:
        logger.error(f"ブロックライブラリページエラー: {e}")
        return render(request, 'tutorial/block_library.html', {'blocks_by_type': {}, 'total_blocks': 0})

# ==================== 補助関数 ====================

def get_user_architecture_slots(user):
    """
    ユーザーのアーキテクチャスロットと割り当て状況を取得
    """
    try:
        # すべてのアクティブなアーキテクチャスロットを取得
        slots = ArchitectureSlot.objects.filter(required=False)  # 必須でないスロットのみ取得
        
        # スロットが存在しない場合、デフォルトスロットを作成
        if not slots.exists():
            slots = create_default_slots()
        
        # ユーザーのアーキテクチャ図を取得
        user_architecture, created = UserArchitecture.objects.get_or_create(user=user)
        assigned_blocks = user_architecture.get_assigned_blocks()
        
        # 返却データを構築
        slots_with_assignments = []
        for slot in slots:
            assigned_block = assigned_blocks.get(str(slot.id))
            slots_with_assignments.append({
                'slot': slot,
                'assigned_block': assigned_block
            })
        
        return slots_with_assignments
    
    except Exception as e:
        logger.error(f"ユーザーアーキテクチャスロット取得エラー: {e}")
        return []

def create_default_slots():
    """
    デフォルトのアーキテクチャスロットを作成
    """
    default_slots_data = [
        {
            'name': 'データモデル層',
            'description': 'データモデルとデータベース構造を定義',
            'allowed_block_types': ['data_model'],
            'x_position': 100,
            'y_position': 100,
            'border_color': '#4C56B3',
            'background_color': '#F0F9FF',
            'required': False,
            'order': 1
        },
        {
            'name': 'ビジネスロジック層',
            'description': 'ビジネスロジックと計算を処理',
            'allowed_block_types': ['view'],
            'x_position': 400,
            'y_position': 100,
            'border_color': '#059669',
            'background_color': '#F0FDF4',
            'required': False,
            'order': 2
        },
        {
            'name': 'ビューレイヤー',
            'description': 'HTTPリクエストとレスポンスを処理',
            'allowed_block_types': ['view'],
            'x_position': 100,
            'y_position': 300,
            'border_color': '#DC2626',
            'background_color': '#FEF2F2',
            'required': False,
            'order': 3
        },
        {
            'name': 'URL層',
            'description': 'URLルーティングを定義',
            'allowed_block_types': ['url'],
            'x_position': 400,
            'y_position': 300,
            'border_color': '#0891B2',
            'background_color': '#F0FDFA',
            'required': False,
            'order': 4
        },
        {
            'name': 'テンプレート層',
            'description': 'フロントエンドテンプレートを定義',
            'allowed_block_types': ['template'],
            'x_position': 700,
            'y_position': 300,
            'border_color': '#DB2777',
            'background_color': '#FDF2F8',
            'required': False,
            'order': 5
        },
    ]
    
    slots = []
    for slot_data in default_slots_data:
        slot = ArchitectureSlot.objects.create(**slot_data)
        slots.append(slot)
    
    return slots

def get_completed_chapters_count(user):
    """
    ユーザーが完了したチャプター数を取得
    """
    try:
        return UserProgress.objects.filter(user=user, completed=True).count()
    except Exception as e:
        logger.error(f"完了チャプター数取得エラー: {e}")
        return 0

def get_total_chapters_count():
    """
    総チャプター数を取得
    """
    try:
        return Chapter.objects.filter(is_active=True).count()
    except Exception as e:
        logger.error(f"総チャプター数取得エラー: {e}")
        return 10

def generate_code_from_architecture(architecture_data):
    """
    アーキテクチャデータに基づいてコードを生成
    """
    if not architecture_data:
        return "# まずアーキテクチャ図を設定してください\n# ブロックをアーキテクチャ図にドラッグしてコードを生成"
    
    code_parts = []
    code_parts.append("# 生成されたDjangoコード\n")
    code_parts.append("from django.db import models")
    code_parts.append("from django.urls import path")
    code_parts.append("from django.shortcuts import render, get_object_or_404, redirect")
    code_parts.append("from django.contrib import admin\n")
    
    # ブロックタイプ別にコードを整理
    for item in architecture_data:
        block_type = item['block_type']
        block_name = item['block_name']
        
        if block_type == 'data_model':
            code_parts.append(f"\n# {block_name} - データモデル")
            code_parts.append(item.get('code_snippet', '# コードスニペットが定義されていません'))
        
        elif block_type == 'view':
            code_parts.append(f"\n# {block_name} - ビューロジック")
            code_parts.append(item.get('code_snippet', '# コードスニペットが定義されていません'))
        
        elif block_type == 'url':
            code_parts.append(f"\n# {block_name} - URL設定")
            code_parts.append(item.get('code_snippet', '# コードスニペットが定義されていません'))
        
        elif block_type == 'template':
            code_parts.append(f"\n# {block_name} - テンプレート")
            code_parts.append(item.get('code_snippet', '# コードスニペットが定義されていません'))
        
        elif block_type == 'admin':
            code_parts.append(f"\n# {block_name} -　管理画面")
            code_parts.append(item.get('code_snippet', '# コードスニペットが定義されていません'))
    
    return "\n".join(code_parts)


# ==================== 徽章检查相关视图 ====================

@login_required
def check_badges(request):
    """
    检查并授予徽章
    """
    try:
        profile = request.user.userprofile
        new_badges = profile.check_and_award_badges()
        
        if new_badges:
            badge_names = [badge.name for badge in new_badges]
            messages.success(request, f'获得了 {len(new_badges)} 个新徽章: {", ".join(badge_names)}')
        else:
            messages.info(request, '没有获得新徽章。继续努力！')
            
    except Exception as e:
        logger.error(f"检查徽章错误: {e}")
        messages.error(request, '检查徽章时出现错误。')
    
    return redirect('level_profile')

@login_required
def force_check_badges(request):
    """
    强制检查并授予徽章（用于调试）
    """
    try:
        profile = request.user.userprofile
        new_badges = profile.check_and_award_badges()
        
        if new_badges:
            badge_names = [badge.name for badge in new_badges]
            messages.success(request, f'获得了 {len(new_badges)} 个新徽章: {", ".join(badge_names)}')
        else:
            messages.info(request, '没有获得新徽章。继续努力！')
            
    except Exception as e:
        logger.error(f"强制检查徽章错误: {e}")
        messages.error(request, '检查徽章时出现错误。')
    
    return redirect('level_profile')

# ==================== エラーハンドリングビュー ====================

def page_not_found(request, exception):
    """
    404エラーページ
    """
    return render(request, 'tutorial/404.html', status=404)

def server_error(request):
    """
    500エラーページ
    """
    return render(request, 'tutorial/500.html', status=500)

def bad_request(request, exception):
    """
    400エラーページ
    """
    return render(request, '400.html', status=400)

def permission_denied(request, exception):
    """
    403エラーページ
    """
    return render(request, '403.html', status=403)
