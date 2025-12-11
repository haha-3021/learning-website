// 选择题选择功能
function selectChoice(questionId, choiceId) {
    // 取消其他选项的选择
    const radios = document.querySelectorAll(`input[name="choice-${questionId}"]`);
    radios.forEach(radio => {
        radio.checked = false;
        radio.parentElement.style.background = '#f8f9fa';
    });
    
    // 选择当前选项
    const selectedRadio = document.getElementById(`choice-${choiceId}`);
    selectedRadio.checked = true;
    selectedRadio.parentElement.style.background = '#e3f2fd';
    
    // 启用提交按钮
    document.getElementById(`choice-submit-${questionId}`).disabled = false;
}

// 提交填空题答案
function submitFillAnswer(questionId) {
    console.log(`=== 提交填空题答案，问题ID: ${questionId} ===`);
    
    // 获取必要的DOM元素
    const submitBtn = document.getElementById(`submit-${questionId}`);
    const resultDiv = document.getElementById(`result-${questionId}`);
    
    if (!submitBtn) {
        console.error(`❌ 未找到提交按钮: submit-${questionId}`);
        // 尝试查找替代的提交按钮
        const alternativeBtn = document.querySelector(`#question-${questionId} .submit-btn`);
        if (alternativeBtn) {
            console.log(`✅ 找到替代按钮:`, alternativeBtn);
        } else {
            alert('系统错误：未找到提交按钮');
            return;
        }
    }
    
    if (!resultDiv) {
        console.error(`❌ 未找到结果框: result-${questionId}`);
        alert('系统错误：未找到结果框');
        return;
    }
    
    // 收集所有输入框的答案
    let answerData = {};
    let hasEmptyAnswer = false;
    let emptyInputs = [];
    
    // 使用更可靠的选择器查找输入框
    const questionContainer = document.getElementById(`question-${questionId}`);
    if (!questionContainer) {
        console.error(`❌ 未找到问题容器: question-${questionId}`);
        alert('系统错误：未找到问题容器');
        return;
    }
    
    // 查找所有填空题输入框
    const inputs = questionContainer.querySelectorAll('input[type="text"]');
    console.log(`找到 ${inputs.length} 个输入框`);
    
    if (inputs.length === 0) {
        console.error('❌ 未找到任何输入框');
        alert('系统错误：未找到答案输入框');
        return;
    }
    
    inputs.forEach((input, index) => {
        let blankIndex = input.getAttribute('data-blank-index');
        
        // 如果没有设置 data-blank-index，自动分配
        if (blankIndex === null || blankIndex === undefined) {
            blankIndex = index.toString();
            console.log(`为输入框 ${index} 自动分配 blankIndex: ${blankIndex}`);
        }
        
        const answer = input.value.trim();
        console.log(`空格 ${blankIndex} (ID: ${input.id}): "${answer}"`);
        
        if (!answer) {
            hasEmptyAnswer = true;
            emptyInputs.push(parseInt(blankIndex) + 1);
        }
        
        answerData[blankIndex] = answer;
    });
    
    // 检查是否有空答案
    if (hasEmptyAnswer) {
        if (emptyInputs.length > 0) {
            alert(`请填写第 ${emptyInputs.join(', ')} 个空格`);
        } else {
            alert('请输入答案');
        }
        return;
    }
    
    console.log(`✅ 答案数据:`, answerData);
    
    // 显示加载状态
    submitBtn.innerHTML = '⏳ 提出中...';
    submitBtn.disabled = true;
    
    // 准备表单数据
    const formData = new FormData();
    formData.append('answer', JSON.stringify(answerData));
    
    // 提交答案
    fetch(`/question/${questionId}/submit/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(response => {
        console.log('响应状态:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('收到响应数据:', data);
        
        // 确保结果框显示
        resultDiv.style.display = 'block';
        
        if (data.correct !== undefined) {
            if (data.correct) {
                // 正确答案处理
                resultDiv.className = 'answer-feedback correct';
                let html = '✅ 正解！素晴らしい！';
                
                // 显示解析
                if (data.explanation && data.explanation.trim() !== '') {
                    html += `<div class="explanation-box"><strong>📘 解説:</strong> ${data.explanation}</div>`;
                }
                
                resultDiv.innerHTML = html;
                
                // 禁用所有输入框和按钮
                inputs.forEach(input => input.disabled = true);
                submitBtn.disabled = true;
                submitBtn.innerHTML = '✅ 回答済み';
                
                // 隐藏提示按钮（如果存在）
                const hintBtn = document.getElementById(`hint-btn-${questionId}`);
                if (hintBtn) {
                    hintBtn.style.display = 'none';
                }
                
            } else {
                // 错误答案处理
                resultDiv.className = 'answer-feedback incorrect';
                let html = '❌ 不正解、もう一度試してください！';
                
                // 显示提示（如果有）
                if (data.hint) {
                    html += `<div class="hint-box"><strong>💡 ヒント:</strong> ${data.hint}</div>`;
                }
                
                // 显示解析（如果有）
                if (data.explanation && data.explanation.trim() !== '') {
                    html += `<div class="explanation-box"><strong>📘 解説:</strong> ${data.explanation}</div>`;
                }
                
                // 显示正确答案（如果有）
                if (data.correct_answers && data.correct_answers.length > 0) {
                    html += `<div class="correct-answers"><strong>正解:</strong> ${data.correct_answers.join(', ')}</div>`;
                }
                
                resultDiv.innerHTML = html;
                
                // 恢复按钮状态
                submitBtn.innerHTML = '📤 再提出';
                submitBtn.disabled = false;
            }
        } else if (data.error) {
            // 处理服务器返回的错误
            resultDiv.className = 'answer-feedback incorrect';
            resultDiv.innerHTML = `❌ エラー: ${data.error}`;
            submitBtn.innerHTML = '📤 再提出';
            submitBtn.disabled = false;
        } else {
            // 未知响应格式
            resultDiv.className = 'answer-feedback incorrect';
            resultDiv.innerHTML = '❌ 不明なレスポンス形式です';
            submitBtn.innerHTML = '📤 再提出';
            submitBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('提交错误:', error);
        resultDiv.style.display = 'block';
        resultDiv.className = 'answer-feedback incorrect';
        resultDiv.innerHTML = '❌ 提出に失敗しました、ネットワーク接続を確認してください';
        submitBtn.innerHTML = '📤 再提出';
        submitBtn.disabled = false;
    });
}
// 提交选择题答案
function submitChoiceAnswer(questionId) {
    console.log(`提交选择题答案，问题ID: ${questionId}`);
    
    const selectedRadio = document.querySelector(`input[name="choice-${questionId}"]:checked`);
    const submitBtn = document.getElementById(`choice-submit-${questionId}`);
    const resultDiv = document.getElementById(`result-${questionId}`);
    
    if (!selectedRadio) {
        alert('请选择一个答案');
        return;
    }
    
    if (!submitBtn) {
        console.error(`未找到提交按钮 choice-submit-${questionId}`);
        alert('系统错误：未找到提交按钮');
        return;
    }
    
    if (!resultDiv) {
        console.error(`未找到结果框 result-${questionId}`);
        alert('系统错误：未找到结果框');
        return;
    }
    
    const selectedChoiceId = selectedRadio.value;
    console.log(`选择的选项ID: ${selectedChoiceId}`);
    
    // 显示加载状态
    submitBtn.innerHTML = '⏳ 提出中...';
    submitBtn.disabled = true;
    
    // 准备表单数据
    const formData = new FormData();
    formData.append('answer', selectedChoiceId);
    
    fetch(`/question/${questionId}/submit/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(response => {
        console.log('响应状态:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('收到响应数据:', data);
        
        // 确保结果框显示
        resultDiv.style.display = 'block';
        
        if (data.correct !== undefined) {
            if (data.correct) {
                resultDiv.className = 'answer-feedback correct';
                let html = '✅ 正解！素晴らしい！';
                
                // 显示解析
                if (data.explanation && data.explanation.trim() !== '') {
                    html += `<div class="explanation-box"><strong>📘 解説:</strong> ${data.explanation}</div>`;
                }
                
                resultDiv.innerHTML = html;
                
                // 禁用所有单选按钮和按钮
                const radios = document.querySelectorAll(`input[name="choice-${questionId}"]`);
                radios.forEach(radio => radio.disabled = true);
                submitBtn.disabled = true;
                submitBtn.innerHTML = '✅ 回答済み';
                
                // 隐藏提示按钮（如果存在）
                const hintBtn = document.getElementById(`hint-btn-${questionId}`);
                if (hintBtn) {
                    hintBtn.style.display = 'none';
                }
                
            } else {
                resultDiv.className = 'answer-feedback incorrect';
                let html = '❌ 不正解、もう一度試してください！';
                
                // 显示提示（如果有）
                if (data.hint) {
                    html += `<div class="hint-box"><strong>💡 ヒント:</strong> ${data.hint}</div>`;
                }
                
                // 显示解析（如果有）
                if (data.explanation && data.explanation.trim() !== '') {
                    html += `<div class="explanation-box"><strong>📘 解説:</strong> ${data.explanation}</div>`;
                }
                
                // 显示正确答案（如果有）
                if (data.correct_answers && data.correct_answers.length > 0) {
                    html += `<div class="correct-answers"><strong>正解:</strong> ${data.correct_answers.join(', ')}</div>`;
                }
                
                resultDiv.innerHTML = html;
                submitBtn.innerHTML = '📤 再提出';
                submitBtn.disabled = false;
            }
        } else if (data.error) {
            resultDiv.className = 'answer-feedback incorrect';
            resultDiv.innerHTML = `❌ エラー: ${data.error}`;
            submitBtn.innerHTML = '📤 再提出';
            submitBtn.disabled = false;
        } else {
            resultDiv.className = 'answer-feedback incorrect';
            resultDiv.innerHTML = '❌ 不明なレスポンス形式です';
            submitBtn.innerHTML = '📤 再提出';
            submitBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('请求错误:', error);
        resultDiv.style.display = 'block';
        resultDiv.className = 'answer-feedback incorrect';
        resultDiv.innerHTML = `❌ 提出に失敗しました: ${error.message}`;
        submitBtn.innerHTML = '📤 再提出';
        submitBtn.disabled = false;
    });
}

function checkAllAnswers() {
    console.log('开始检查所有答案...');
    const questions = document.querySelectorAll('.question');
    console.log(`找到 ${questions.length} 个问题`);
    
    let allCorrect = true;
    let allAnswered = true;

    questions.forEach((question, index) => {
        const correctFeedback = question.querySelector('.answer-feedback.correct');
        const incorrectFeedback = question.querySelector('.answer-feedback.incorrect');
        
        // 检查是否已回答
        if (!correctFeedback && !incorrectFeedback) {
            allAnswered = false;
        }
        
        // 检查是否正确
        if (!correctFeedback) {
            allCorrect = false;
        }
    });
    
    if (!allAnswered) {
        alert('请先回答所有问题！');
        // 滚动到第一个未回答的问题
        const firstUnanswered = document.querySelector('.question:not(:has(.answer-feedback))');
        if (firstUnanswered) {
            firstUnanswered.scrollIntoView({ behavior: 'smooth' });
        }
        return;
    }

    if (allCorrect) {
        console.log('所有答案正确，发送通关请求...');
        completeChapter();
    } else {
        alert('请确保所有问题都回答正确！');
        // 滚动到第一个错误答案
        const firstIncorrect = document.querySelector('.answer-feedback.incorrect');
        if (firstIncorrect) {
            firstIncorrect.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

// 2. showHint 函数
function showHint(questionId) {
    console.log(`显示问题 ${questionId} 的提示`);
    const hintBox = document.getElementById(`hint-${questionId}`);
    const hintBtn = document.getElementById(`hint-btn-${questionId}`);
    
    if (!hintBox) {
        console.error(`未找到提示框 hint-${questionId}`);
        return;
    }
    
    if (!hintBtn) {
        console.error(`未找到提示按钮 hint-btn-${questionId}`);
        return;
    }
    
    // 显示加载状态
    hintBox.innerHTML = 'ヒントを読み込み中...';
    hintBox.style.display = 'block';
    hintBtn.disabled = true;
    hintBtn.innerHTML = '💡 ヒント表示中';
    
}

// 3. enableChoiceSubmit 函数
function enableChoiceSubmit(questionId) {
    const submitBtn = document.getElementById(`choice-submit-${questionId}`);
    if (submitBtn) {
        submitBtn.disabled = false;
        console.log(`已启用问题 ${questionId} 的选择题提交按钮`);
    } else {
        console.error(`未找到选择题提交按钮 choice-submit-${questionId}`);
    }
}

// 4. completeChapter 函数
function completeChapter() {
    console.log('发送章节完成请求...');
    
    fetch(`{% url 'complete_chapter' chapter.id %}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.status);
        }
        return response.json();
    })
    .then(responseData => {
        console.log('章节完成响应:', responseData);
        
        if (responseData.success) {
            let message = '🎉 恭喜！章节完成！';
            
            if (responseData.already_completed) {
                message = '✅ 本章节已完成！';
            } else {
                if (responseData.experience_added > 0) {
                    message += ` 经验值+${responseData.experience_added}`;
                }
                if (responseData.level_up) {
                    message += ` 等级提升！${responseData.old_level} → ${responseData.new_level}`;
                }
            }
            
            // 显示成功消息
            showCompletionMessage(message);
            
            // 更新页面状态
            updateCompletionStatus();
            
        } else {
            alert('完成状态更新失败: ' + (responseData.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('请求失败: ' + error.message);
    });
}

// 5. showCompletionMessage 函数
function showCompletionMessage(message) {
    // 这个函数可以保持原有逻辑，因为章节完成是重要事件
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 20px;
        border-radius: 8px;
        background: var(--success-500);
        color: white;
        font-weight: 500;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(messageEl);
    
    setTimeout(() => {
        messageEl.style.opacity = '0';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }, 5000);
}

// 6. updateCompletionStatus 函数
function updateCompletionStatus() {
    // 更新进度指示器
    const progressSteps = document.querySelectorAll('.progress-step');
    if (progressSteps.length >= 2) {
        progressSteps.forEach(step => step.classList.add('completed'));
    }
    
    // 禁用提交按钮
    const submitAllBtn = document.getElementById('submit-all-answers');
    if (submitAllBtn) {
        submitAllBtn.disabled = true;
        submitAllBtn.textContent = '✅ 已完成';
    }
    
    // 显示完成状态
    const completionStatus = document.querySelector('.completion-status');
    if (completionStatus) {
        completionStatus.style.display = 'block';
    }
}

// 7. 修复选择题选项点击处理
// 替换现有的单选按钮onchange事件
document.addEventListener('DOMContentLoaded', function() {
    // ... 其他初始化代码 ...
    
    // 修复选择题的点击事件
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const questionId = this.name.replace('choice-', '');
            enableChoiceSubmit(questionId);
        });
    });
    
    // 修复提示按钮的点击事件
    document.querySelectorAll('.hint-button').forEach(button => {
        button.addEventListener('click', function() {
            const questionId = this.id.replace('hint-btn-', '');
            showHint(questionId);
        });
    });
    
    // 修复填空题提交按钮的点击事件
    document.querySelectorAll('.submit-btn').forEach(button => {
        if (button.id.startsWith('submit-')) {
            button.addEventListener('click', function() {
                const questionId = this.id.replace('submit-', '');
                submitFillAnswer(questionId);
            });
        }
    });
    
    // 修复选择题提交按钮的点击事件
    document.querySelectorAll('.submit-btn').forEach(button => {
        if (button.id.startsWith('choice-submit-')) {
            button.addEventListener('click', function() {
                const questionId = this.id.replace('choice-submit-', '');
                submitChoiceAnswer(questionId);
            });
        }
    });
});

// 简化 enableChoiceSubmit 函数
function enableChoiceSubmit(questionId) {
    const submitBtn = document.getElementById(`choice-submit-${questionId}`);
    if (submitBtn) {
        submitBtn.disabled = false;
    }
}

// 通用答案提交函数
function submitAnswer(questionId, type, answer, button, resultDiv) {
    const formData = new FormData();
    formData.append('answer', answer);
    
    fetch(`/question/${questionId}/submit/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        resultDiv.style.display = 'block';
        
        if (data.correct) {
            resultDiv.className = 'answer-feedback correct';
            resultDiv.innerHTML = '✅ 回答正确！太棒了！';
            // 禁用输入
            if (type === 'fill') {
                document.getElementById(`answer-${questionId}`).disabled = true;
            } else {
                document.querySelectorAll(`input[name="choice-${questionId}"]`).forEach(input => {
                    input.disabled = true;
                });
            }
            button.disabled = true;
            button.innerHTML = '已答对';
        } else {
            resultDiv.className = 'answer-feedback incorrect';
            resultDiv.innerHTML = '❌ 回答错误，请再试一次！';
            resetButton(button, '重新提交');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        resultDiv.style.display = 'block';
        resultDiv.className = 'answer-feedback incorrect';
        resultDiv.innerHTML = '❌ 提交失败，请检查网络连接';
        resetButton(button, '重新提交');
    });
}

// 显示加载状态
function showLoading(button) {
    button.innerHTML = '提交中...';
    button.disabled = true;
}

// 重置按钮状态
function resetButton(button, text) {
    button.innerHTML = text;
    button.disabled = false;
}

// 获取CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 基础JavaScript功能
function showLoading(element) {
    element.innerHTML = '提交中...';
    element.disabled = true;
}

function resetButton(element, text) {
    element.innerHTML = text;
    element.disabled = false;
}