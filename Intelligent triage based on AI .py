from flask import Flask, render_template_string, request, jsonify
import os
import json
import re
import ast
from openai import OpenAI
from openai.types.chat.chat_completion import Choice
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging
import speech_recognition as sr
import wave
import io

# 配置日志记录
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 初始化 OpenAI 客户端
client = OpenAI(
    base_url="https://api.moonshot.cn/v1",  # 确保这是正确的 API 地址
    api_key="填写moonshotkey"  # 确保这是有效的 API 密钥
)

# 系统消息内容
SYSTEM_MESSAGE = """
你是一位专业的导诊员，由 Moonshot AI 提供支持。请通过多轮对话的方式，逐步了解患者的症状和情况。

Role: 专业导诊员
Background: 用户可能对自身病情描述不够清晰，需要通过引导性的提问来获取更多信息。
Skills: 
1. 善于倾听和提问，通过追问获取关键信息
2. 能够根据用户的回答动态调整提问方向
3. 具备专业的医学知识，能准确理解症状描述

Workflow:
1. 首先让患者描述主要症状
2. 根据症状进行有针对性的追问：
   - 症状持续时间
   - 是否有诱因
   - 是否伴随其他不适
   - 是否有既往病史
3. 获取足够信息后，推荐最合适的就诊科室

注意事项：
- 每次对话要有重点，避免一次性问太多问题
- 提问要通俗易懂，避免专业术语
- 如发现危急症状，及时建议就医
"""

# 初始化对话历史
history = [{"role": "system", "content": SYSTEM_MESSAGE}]





def check_satisfaction(history: str) -> tuple[bool, str]:
    """判断问诊是否完整并返回缺失信息"""
    try:
        messages = [
            {"role": "system", "content": """你是一位专业的导诊员。请严格检查问诊信息的完整性，必须确保完成至少6轮有效对话。
                必须包含以下所有信息，每个信息点需要详细追问：
                1. 主要症状：
                   - 具体症状描述
                   - 症状的具体部位
                   - 症状的性质（如疼痛类型、程度等）
                
                2. 症状持续时间：
                   - 首次出现时间
                   - 发作频率
                   - 是否规律发作
                
                3. 症状诱因：
                   - 可能的诱发因素
                   - 加重或缓解因素
                   - 是否与特定行为相关
                
                4. 伴随症状：
                   - 其他不适感
                   - 生活作息影响
                   - 情绪变化
                
                5. 既往病史：
                   - 相关疾病史
                   - 家族病史
                   - 过敏史
                
                6. 基本生活状况：
                   - 作息规律
                   - 饮食习惯
                   - 工作环境
                
                请按以下格式回复：
                - 如果所有信息完整且【不超过10轮对话】：True|已收集完整信息
                - 如果信息不完整或对话不足6轮：False|下一个需要追问的具体问题"""},
            {"role": "user", "content": f"请分析以下问诊对话：\n{history}"}
        ]
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages,
            temperature=0.1,
        )
        response = completion.choices[0].message.content.strip()
        is_complete, message = response.split('|', 1)
        return is_complete.lower() == 'true', message.strip()
    except Exception as e:
        logging.error(f"检查问诊完整性时发生错误: {e}")
        return False, "请详细描述您的主要症状"

def refine_response(query: str, history: list) -> str:
    try:
        logging.info("开始处理用户输入...")
        
        # 如果是首次输入（包含患者基本信息）
        if "患者基本信息：" in query:
            history.append({"role": "user", "content": query})
            welcome_message = "感谢您提供基本信息。请详细描述您目前的主要症状和不适感。"
            history.append({"role": "assistant", "content": welcome_message})
            return welcome_message
            
        # 原有的问诊逻辑
        history.append({"role": "user", "content": query})
        is_complete, message = check_satisfaction(str(history))
        
        if is_complete and len(history) >= 10:  # 确保至少6轮对话（每轮包含问和答）
            medical_record = generate_medical_record(history)
            result = f"【问诊结束】\n\n{medical_record}\n\n如需继续问诊，请重新开始。"
            history.append({"role": "assistant", "content": result})
            history.clear()
            history.append({"role": "system", "content": SYSTEM_MESSAGE})
            logging.info("问诊完成，已生成病历记录")
        else:
            messages = [
                {"role": "system", "content": """你是一位专业的导诊员。请根据患者的回答进行智能追问：
                1. 仔细分析患者最新回答的内容
                2. 对每个症状点进行深入追问，直到获取足够详细的信息
                3. 发现危急症状时立即建议就医
                4. 每次只问一个最关键的问题
                5. 确保问题不重复，且逐步深入
                6. 注意可能被忽略的细节
                
                提问要求：
                - 问题要具体且一次只问一个要点
                - 问题要简短明确
                - 循序渐进，由表及里
                - 注意症状之间的关联性
                - 关注患者的生活质量影响
                - 问题不要重复，或者难以理解
                """},
                {"role": "user", "content": f"这是问诊记录，请根据患者最新回答生成下一个问题：\n{str(history)}"}
            ]
            
            completion = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=messages,
                temperature=0.3,
            )
            
            next_question = completion.choices[0].message.content
            history.append({"role": "assistant", "content": next_question})
            logging.info(f"追问问题: {next_question}")
            result = next_question
        
        return result
    except Exception as e:
        logging.error(f"处理对话时发生错误: {e}")
        return "抱歉，系统出现错误，请重新描述您的症状。"


def generate_medical_record(history: list) -> str:
    """生成规范的病历记录"""
    try:
        messages = [
            {"role": "system", "content": """请根据问诊对话生成一份规范的病历记录，使用 Markdown 格式：
# 门诊病历记录

**就诊时间：** [当前时间]

## 主诉
患者主要症状和不适

## 现病史
1. **发病时间：** 
   - 首次出现时间
   - 发作频率

2. **症状特点：**
   - 具体表现
   - 发展过程
   - 严重程度

3. **诱因分析：**
   - 可能的诱发因素
   - 加重/缓解因素

4. **伴随症状：**
   - 其他不适表现
   - 对日常生活的影响

## 既往史
- **疾病史：** 相关病史记录
- **家族史：** 家族相关病史
- **过敏史：** 药物或其他过敏情况

## 初步诊断
根据症状的初步判断分析

## 就诊建议
1. **建议科室：** 推荐就诊的专科
2. **就医建议：** 具体就医指导
3. **注意事项：** 日常注意要点

请确保格式规范，便于阅读。"""},
            {"role": "user", "content": f"请根据以下对话生成病历记录：\n{str(history)}"}
        ]
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages,
            temperature=0.3,
        )
        
        # 替换可能的 HTML 标签为 Markdown 语法
        medical_record = completion.choices[0].message.content
        medical_record = medical_record.replace('<br>', '\n')
        medical_record = medical_record.replace('<b>', '**').replace('</b>', '**')
        medical_record = medical_record.replace('<strong>', '**').replace('</strong>', '**')
        medical_record = medical_record.replace('<em>', '*').replace('</em>', '*')
        
        return medical_record
    except Exception as e:
        logging.error(f"生成病历记录时发生错误: {e}")
        return "无法生成病历记录"


# 语音识别函数
def recognize_speech_from_audio(audio_data) -> str:
    """从音频数据识别语音并返回文本"""
    recognizer = sr.Recognizer()
    audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
    try:
        logging.info("识别语音中...")
        query = recognizer.recognize_google(audio, language="zh-CN")
        logging.info(f"识别结果: {query}")
        return query
    except sr.UnknownValueError:
        logging.error("无法识别语音")
        return "无法识别语音"
    except sr.RequestError as e:
        logging.error(f"请求错误; {e}")
        return "请求错误"


app = Flask(__name__)

# 嵌入的 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能导诊系统</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>

        .patient-info-form {
        padding: 30px;
        background-color: #242f3d;
        border-radius: 12px;
        margin: 40px auto;
        max-width: 500px;
    }
    .patient-info-form h2 {
        color: #fff;
        margin-bottom: 25px;
        text-align: center;
        font-size: 20px;
    }
    .form-group {
        margin-bottom: 20px;
    }
    .form-group label {
        display: block;
        color: #fff;
        margin-bottom: 8px;
    }
    .form-group input[type="text"],
    .form-group input[type="number"],
    .form-group select {
        width: 100%;
        padding: 10px;
        border: 1px solid #3b4654;
        border-radius: 6px;
        background-color: #17212b;
        color: #fff;
    }
    .radio-group {
        display: flex;
        gap: 20px;
    }
    .radio-group input[type="radio"] {
        margin-right: 8px;
    }
    .submit-info-btn {
        width: 100%;
        padding: 12px;
        background-color: #2b5278;
        margin-top: 20px;
    }
    .submit-info-btn:hover {
        background-color: #3a6d9c;
    }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background-color: #17212b;
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .app-container {
            display: flex;
            width: 95%;
            max-width: 1200px;
            height: 90vh;
            background-color: #17212b;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }
        .sidebar {
            width: 280px;
            background-color: #242f3d;
            padding: 20px;
            color: #fff;
            border-right: 1px solid #3b4654;
        }
        .sidebar h2 {
            font-size: 20px;
            margin-bottom: 20px;
            color: #fff;
        }
        .feature-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .feature-item {
            padding: 12px 15px;
            margin-bottom: 8px;
            background-color: #2b5278;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .feature-item:hover {
            background-color: #3a6d9c;
        }
        .feature-item i {
            margin-right: 10px;
            width: 20px;
        }
        .chat-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: #0e1621;
        }
        .header {
            background-color: #242f3d;
            color: white;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            border-bottom: 1px solid #3b4654;
        }
        .header-title {
            font-size: 18px;
            font-weight: normal;
            margin: 0;
            color: #fff;
        }
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background-color: #0e1621;
        }
        .message {
            display: flex;
            align-items: flex-start;
            margin-bottom: 16px;
            animation: fadeIn 0.2s ease;
        }
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin: 0 12px;
            flex-shrink: 0;
            background-color: #242f3d;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 8px;
            position: relative;
            font-size: 15px;
            line-height: 1.4;
        }
        .bot-message {
            background-color: #242f3d;
            color: #fff;
            margin-right: auto;
        }
        .user-message {
            background-color: #2b5278;
            color: #fff;
            margin-left: auto;
        }
        .message-time {
            font-size: 12px;
            color: #8e8e8e;
            margin-top: 4px;
            text-align: right;
        }
        .input-container {
            padding: 15px;
            background-color: #242f3d;
            border-top: 1px solid #3b4654;
        }
        .input-wrapper {
            display: flex;
            gap: 10px;
            background-color: #17212b;
            border-radius: 8px;
            padding: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 8px;
            border: none;
            background: none;
            font-size: 15px;
            outline: none;
            color: #fff;
        }
        input[type="text"]::placeholder {
            color: #8e8e8e;
        }
        .action-buttons {
            display: flex;
            gap: 8px;
        }
        button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: background-color 0.2s;
        }
        .send-button {
            background-color: #2b5278;
        }
        .send-button:hover {
            background-color: #3a6d9c;
        }
        .record-button {
            background-color: #2b5278;
        }
        .record-button:hover {
            background-color: #3a6d9c;
        }
        .record-button.recording {
            background-color: #c13d3d;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        /* 自定义滚动条 */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #17212b;
        }
        ::-webkit-scrollbar-thumb {
            background: #3b4654;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #4a5a70;
        }

        
    // ... existing styles ...
    
    /* AI 思考动画样式 */
    .thinking-animation {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
    }
    
    .thinking-dot {
        width: 6px;
        height: 6px;
        background: #fff;
        border-radius: 50%;
        opacity: 0.4;
        animation: thinkingAnimation 1.4s infinite;
    }
    
    .thinking-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .thinking-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes thinkingAnimation {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
    }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <h2>功能介绍</h2>
            <ul class="feature-list">
                <li class="feature-item">
                    <i class="fas fa-comment-medical"></i>
                    智能问诊对话
                </li>
                <li class="feature-item">
                    <i class="fas fa-microphone"></i>
                    语音输入支持
                </li>
                <li class="feature-item">
                    <i class="fas fa-clipboard-list"></i>
                    专业病历记录
                </li>
                <li class="feature-item">
                    <i class="fas fa-hospital"></i>
                    科室精准推荐
                </li>
                <li class="feature-item">
                    <i class="fas fa-user-md"></i>
                    专业医学知识
                </li>
                <li class="feature-item">
                    <i class="fas fa-shield-alt"></i>
                    隐私安全保护
                </li>
                <li class="feature-item" onclick="showHelp()">
                    <i class="fas fa-question-circle"></i>
                    使用帮助
                </li>
            </ul>
        </div>
        <div class="chat-section">
            <div class="header">
                <h1 class="header-title">智能导诊助手</h1>
            </div>
            <!-- 添加患者信息表单 -->
            <div id="patient-info-form" class="patient-info-form">
                <h2>患者基本信息</h2>
                <div class="form-group">
                    <label>性别：</label>
                    <div class="radio-group">
                        <input type="radio" id="male" name="gender" value="男" required>
                        <label for="male">男</label>
                        <input type="radio" id="female" name="gender" value="女">
                        <label for="female">女</label>
                    </div>
                </div>
                <div class="form-group">
                    <label for="age">年龄：</label>
                    <input type="number" id="age" min="0" max="120" required>
                </div>
                <div class="form-group">
                    <label for="occupation">职业：</label>
                    <input type="text" id="occupation" required>
                </div>
                <div class="form-group">
                    <label>婚育状况：</label>
                    <select id="marital-status" required>
                        <option value="">请选择</option>
                        <option value="未婚">未婚</option>
                        <option value="已婚已育">已婚已育</option>
                        <option value="已婚未育">已婚未育</option>
                        <option value="其他">其他</option>
                    </select>
                </div>
                <button onclick="submitPatientInfo()" class="submit-info-btn">开始问诊</button>
            </div>
            <!-- 修改聊天容器，默认隐藏 -->
            <div id="chat-container" class="chat-container" style="display: none;">
                <div class="message">
                    <div class="message-avatar bot-avatar">
                        <i class="fas fa-user-md"></i>
                    </div>
                    <div class="message-content bot-message">
                        您好！我是您的智能导诊助手，请详细描述您的症状，我会为您推荐合适的就诊科室。
                        <div class="message-time">系统消息</div>
                    </div>
                </div>
            </div>
            <div class="input-container">
                <div class="input-wrapper">
                    <input type="text" id="text_input" placeholder="请描述您的症状...">
                    <div class="action-buttons">
                        <button id="record_button" class="record-button">
                            <i class="fas fa-microphone"></i>
                            语音输入
                        </button>
                        <button onclick="submitForm()" class="send-button">
                            <i class="fas fa-paper-plane"></i>
                            发送
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;

        function showHelp() {
            const helpContent = `
# 智能导诊系统使用帮助

## 基本操作
1. **文字输入**
   - 在底部输入框输入症状描述
   - 按发送按钮或回车键提交

2. **语音输入**
   - 点击"语音输入"按钮开始录音
   - 再次点击停止录音
   - 系统自动识别并发送语音内容

## 问诊流程
1. 系统会引导您描述主要症状
2. 根据您的回答进行追问
3. 收集足够信息后生成诊断建议
4. 推荐合适的就诊科室

## 注意事项
- 请尽可能详细描述症状
- 如遇紧急情况请立即就医
- 系统建议仅供参考
`;
            addMessage(helpContent);
        }

        // 配置 marked 选项
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });

        function addMessage(content, isUser = false) {
            const chatContainer = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
    
            const now = new Date();
            const time = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    
            const avatar = `
                <div class="message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}">
                    <i class="fas ${isUser ? 'fa-user' : 'fa-user-md'}"></i>
                </div>
            `;
    
            // 处理 Markdown 内容
            const formattedContent = isUser ? content : marked.parse(content);
            
            const messageContent = `
                <div class="message-content ${isUser ? 'user-message' : 'bot-message'}">
                    ${formattedContent}
                    <div class="message-time">${time}</div>
                </div>
            `;
    
            messageDiv.innerHTML = isUser ? messageContent + avatar : avatar + messageContent;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        document.getElementById('record_button').addEventListener('click', () => {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });

        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);

                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const formData = new FormData();
                    formData.append('audio_input', audioBlob, 'recording.wav');
                    submitForm(formData);
                };

                mediaRecorder.start();
                isRecording = true;
                const recordButton = document.getElementById('record_button');
                recordButton.classList.add('recording');
                recordButton.innerHTML = '<i class="fas fa-stop"></i> 停止录音';
            } catch (error) {
                console.error('录音失败:', error);
                alert('无法访问麦克风，请检查权限设置');
            }
        }

        function stopRecording() {
            mediaRecorder.stop();
            isRecording = false;
            const recordButton = document.getElementById('record_button');
            recordButton.classList.remove('recording');
            recordButton.innerHTML = '<i class="fas fa-microphone"></i> 语音输入';
            audioChunks = [];
        }

          function showThinkingAnimation() {
            const chatContainer = document.getElementById('chat-container');
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'message thinking-message';
            thinkingDiv.innerHTML = `
                <div class="message-avatar bot-avatar">
                    <i class="fas fa-user-md"></i>
                </div>
                <div class="message-content bot-message">
                    <div class="thinking-animation">
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                    </div>
                </div>
            `;
            chatContainer.appendChild(thinkingDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return thinkingDiv;
        }

        function removeThinkingAnimation(element) {
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }

        // 修改 submitForm 函数
        async function submitForm(formData = null) {
            const textInput = document.getElementById('text_input');
            const text = textInput.value.trim();
    
            if (!formData) {
                if (!text) {
                    alert('请输入内容');
                    return;
                }
                formData = new FormData();
                formData.append('text_input', text);
                addMessage(text, true);
            }
    
            const thinkingAnimation = showThinkingAnimation();
    
            try {
                const response = await fetch('/submit', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                removeThinkingAnimation(thinkingAnimation);
                addMessage(data.result);
                textInput.value = '';
            } catch (error) {
                console.error('Error:', error);
                removeThinkingAnimation(thinkingAnimation);
                addMessage('抱歉，服务出现错误，请稍后重试。');
            }
        }

        // 支持按回车发送消息
        document.getElementById('text_input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitForm();
            }
        });
        function submitPatientInfo() {
        const gender = document.querySelector('input[name="gender"]:checked')?.value;
        const age = document.getElementById('age').value;
        const occupation = document.getElementById('occupation').value;
        const maritalStatus = document.getElementById('marital-status').value;

        if (!gender || !age || !occupation || !maritalStatus) {
            alert('请填写所有必填信息');
            return;
        }

        const patientInfo = `患者基本信息：
- 性别：${gender}
- 年龄：${age}岁
- 职业：${occupation}
- 婚育状况：${maritalStatus}`;

        // 隐藏表单，显示聊天界面
        document.getElementById('patient-info-form').style.display = 'none';
        document.getElementById('chat-container').style.display = 'block';
        document.getElementById('input-container').style.display = 'block';

        // 发送患者信息
        const formData = new FormData();
        formData.append('text_input', patientInfo);
        submitForm(formData);
    }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/submit', methods=['POST'])
def submit():
    global history
    if 'text_input' in request.form:
        query = request.form['text_input']
    elif 'audio_input' in request.files:
        audio_file = request.files['audio_input']
        audio_data = audio_file.read()
        query = recognize_speech_from_audio(audio_data)
    else:
        return jsonify({"error": "无效的输入方式"}), 400

    refined_result = refine_response(query, history)
    return jsonify({"result": refined_result})


if __name__ == '__main__':
    app.run(debug=True)


