# 第三方API配置指南

## 概述

文档分析系统现在支持通过第三方API转发平台访问GPT等模型服务，这样可以解决直连API的网络问题，降低成本，或使用国内的API转发服务。

## 支持的第三方平台

### 1. OneAPI
OneAPI是一个开源的API管理和转发平台，支持多种AI模型。

**配置示例：**
```bash
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=oneapi
THIRD_PARTY_API_KEY=sk-your-oneapi-key
THIRD_PARTY_BASE_URL=https://your-oneapi-domain.com
THIRD_PARTY_MODEL=gpt-3.5-turbo
```

### 2. FastGPT
FastGPT是一个知识库问答系统，也支持API转发。

**配置示例：**
```bash
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=fastgpt
THIRD_PARTY_API_KEY=fastgpt-your-key
THIRD_PARTY_BASE_URL=https://your-fastgpt-domain.com
THIRD_PARTY_MODEL=gpt-3.5-turbo
```

### 3. Azure OpenAI
微软Azure的OpenAI服务。

**配置示例：**
```bash
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=azure
THIRD_PARTY_API_KEY=your-azure-key
THIRD_PARTY_BASE_URL=https://your-resource.openai.azure.com
THIRD_PARTY_MODEL=gpt-35-turbo
```

### 4. Cloudflare Workers AI
Cloudflare的AI服务平台。

**配置示例：**
```bash
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=cloudflare
THIRD_PARTY_API_KEY=your-cloudflare-token
THIRD_PARTY_BASE_URL=https://api.cloudflare.com/client/v4/accounts/your-account-id/ai/v1
THIRD_PARTY_MODEL=@cf/meta/llama-2-7b-chat-int8
```

### 5. 自定义API
如果您使用其他平台，可以使用自定义配置。

**配置示例：**
```bash
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=custom
THIRD_PARTY_API_KEY=your-custom-key
THIRD_PARTY_BASE_URL=https://your-custom-api.com/v1
THIRD_PARTY_MODEL=gpt-3.5-turbo
```

## 配置步骤

### 1. 创建环境变量文件
```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件
notepad .env  # Windows
# 或
nano .env     # Linux/Mac
```

### 2. 填入您的API配置
在 `.env` 文件中填入您的第三方API平台信息：

- `THIRD_PARTY_API_KEY`: 您的API密钥
- `THIRD_PARTY_BASE_URL`: API端点地址
- `THIRD_PARTY_MODEL`: 要使用的模型名称

### 3. 启用第三方API
```bash
THIRD_PARTY_API_ENABLED=true
```

### 4. 重启应用
重启文档分析系统以应用新配置。

## 高级配置

### 请求头自定义
```bash
THIRD_PARTY_USER_AGENT=DocumentAnalysisSystem/1.0
THIRD_PARTY_SOURCE=document-analysis
```

### 代理设置
如果需要通过代理访问：
```bash
THIRD_PARTY_PROXY=http://proxy-server:8080
```

### 速率限制
```bash
THIRD_PARTY_RPM=60        # 每分钟请求数
THIRD_PARTY_TPM=60000     # 每分钟令牌数
```

### 重试配置
```bash
THIRD_PARTY_RETRY_ATTEMPTS=3    # 重试次数
THIRD_PARTY_RETRY_DELAY=1.0     # 重试延迟(秒)
```

## 常见问题

### Q: 如何测试API连接？
A: 在应用的侧边栏点击"测试AI连接"按钮。

### Q: 支持哪些模型？
A: 支持所有兼容OpenAI Chat Completions API的模型，包括：
- GPT-3.5-turbo
- GPT-4
- GPT-4-turbo
- Claude (通过兼容接口)
- 国产大模型 (通义千问、文心一言、智谱GLM等)

### Q: 如何切换回本地Ollama？
A: 设置 `THIRD_PARTY_API_ENABLED=false` 即可。

### Q: 配置不生效怎么办？
A: 请检查：
1. `.env` 文件格式是否正确
2. API密钥是否有效
3. 网络连接是否正常
4. 是否重启了应用

## 安全建议

1. **保护API密钥**: 不要将API密钥提交到版本控制系统
2. **使用HTTPS**: 确保API端点使用HTTPS协议
3. **设置速率限制**: 避免过度使用API导致被限制
4. **监控使用量**: 定期检查API使用情况和费用

## 故障排除

### 连接失败
- 检查API密钥是否正确
- 验证base_url是否可访问
- 确认网络连接正常

### 认证错误
- 确认API密钥格式正确
- 检查是否有足够的余额或配额
- 验证模型名称是否正确

### 超时错误
- 增加 `THIRD_PARTY_TIMEOUT` 值
- 检查网络延迟
- 考虑使用代理加速

如需更多帮助，请查看应用日志或联系技术支持。
