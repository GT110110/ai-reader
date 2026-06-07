# 📚 AI 书僮

上传一本书，AI 扮演作者逐章带你阅读。

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| **📚 书架管理** | 上传 PDF/TXT → 自动识别章节目录 → 卡片展示 → 进度追踪 |
| **📖 AI 阅读** | AI 以作者口吻逐章讲解，互动提问，自动保存进度 |
| **📋 粘贴文本** | 粘贴视频转录稿/博客文章，AI 带你读 |
| **🔖 智能目录** | 章节状态追踪、书签管理、搜索筛选、多级标题 |
| **📊 阅读统计** | 阅读进度、章节状态、完成度一目了然 |

### 🎯 v2.0 新增功能

#### 📑 增强版目录系统
- ✅ **章节状态追踪**：未读/正在阅读/已完成，自动标记
- ⭐ **书签功能**：一键收藏重点章节，支持书签筛选
- 🔍 **目录搜索**：快速定位目标章节
- 📊 **阅读统计**：实时显示阅读进度和书签数量

#### 🏗️ 多级章节支持
- 智能识别一级、二级标题
- 自动提取章节摘要
- 子章节层级展示

#### 🤖 智能分段
- 无章节标记时自动分段
- 保持内容完整性

[查看完整更新日志](CHANGELOG.md)

## 快速开始

```bash
cd D:\AIcode\ai-reader
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 `http://localhost:8501`

## 配置 API Key

在项目目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=sk-你的key
```

## 项目结构

```
ai-reader/
├── app.py              # Streamlit 主应用（书架 + 阅读）
├── shelf.py            # 书架存储、进度持久化
├── reader.py           # DeepSeek API 流式调用
├── book_parser.py      # PDF/TXT 解析 + 章节检测
├── prompt.py           # AI 提示词模板
├── shelf/              # 书架数据（自动生成）
├── requirements.txt    # Python 依赖
├── Dockerfile          # Docker 部署
└── README.md           # 本文件
```

## 部署

```bash
docker build -t ai-reader .
docker run -p 8501:8501 --env-file .env ai-reader
```

访问 `http://localhost:8501`
