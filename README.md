
# 智能导诊问答系统

一个基于 Flask 和 Moonshot AI 的智能导诊系统，通过多轮对话收集患者信息，提供初步诊断建议和就医指导。

## 功能特点

- 🤖 智能问诊对话：通过多轮对话逐步了解患者症状
- 🎙️ 语音输入支持：支持语音描述症状
- 📝 专业病历记录：自动生成规范的门诊病历
- 🏥 科室精准推荐：根据症状智能推荐就诊科室
- 🔒 隐私安全保护：确保患者信息安全
- 📱 响应式界面：支持各种设备访问

## 技术栈

- 后端：Flask
- AI 模型：Moonshot AI
- 前端：HTML5 + CSS3 + JavaScript
- 语音识别：SpeechRecognition
- UI 组件：Font Awesome
- Markdown 渲染：Marked.js

## 快速开始

### 环境要求

- Python 3.7+
- Flask
- OpenAI Python SDK
- SpeechRecognition

### 安装依赖

```bash
pip install flask openai speechrecognition
```

### 配置

1. 在代码中设置 Moonshot AI 的 API 密钥：

```python
client = OpenAI(
    base_url="https://api.moonshot.cn/v1",
    api_key="your-api-key"
)
```

### 运行

```bash
python app.py
```

访问 `http://localhost:5000` 即可使用系统。

## 使用流程

1. 填写基本信息：性别、年龄、职业、婚育状况
2. 描述主要症状（支持文字或语音输入）
3. 回答系统追问，提供更详细信息
4. 获取诊断建议和就医指导

## 系统特性

### 智能问诊

- 动态追问策略
- 专业医学知识支持
- 危急症状及时预警

### 病历记录

自动生成包含以下内容的规范病历：
- 主诉
- 现病史
- 既往史
- 初步诊断
- 就诊建议

### 用户界面

- 深色主题设计
- 流畅的动画效果
- 直观的操作方式

## 注意事项

- 本系统建议仅供参考，不能替代专业医生的诊断
- 如遇紧急情况请立即就医
- 请确保提供真实准确的症状信息

## 开源协议

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 致谢

- [Moonshot AI](https://www.moonshot.cn/) - 提供 AI 模型支持
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Font Awesome](https://fontawesome.com/) - 图标支持
- [Marked.js](https://marked.js.org/) - Markdown 渲染


