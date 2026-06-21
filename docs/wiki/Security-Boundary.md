# Security Boundary

本项目只适用于学校授权的校内 XipuAI 网页环境。安全边界是项目答辩和后续维护中的关键部分。

## 1. 允许的用途

项目适用于：

- 学校 AI 比赛演示；
- 教学环境中的系统原型；
- 学校授权的 XipuAI 访问；
- 个人本地测试；
- 校内模型资源统一接入研究。

## 2. 不应做的事情

项目不应用于：

- 绕过学校登录；
- 破解验证码或风控；
- 读取他人 Cookie；
- 使用他人账号或共享账号；
- 把学校 XipuAI 作为公开匿名 API 转售；
- 保存或传播用户敏感对话；
- 将 `school_gpt_state.json` 上传到 GitHub；
- 将真实账号、密码、Cookie、token 写入代码仓库。

## 3. 登录状态文件

`login_once.py` 会生成：

```text
school_gpt_state.json
```

该文件包含本地浏览器登录状态。项目通过以下方式保护它：

- `.gitignore` 排除；
- `.dockerignore` 排除；
- release 打包脚本排除；
- README 和 Wiki 明确提示不要上传。

## 4. API Key

当前演示 API Key：

```text
sk-student-demo-001
```

只适合比赛演示。正式项目应改成：

- 后端生成 API Key；
- 数据库存储 key 哈希；
- 支持 key 启用、禁用和轮换；
- 每个用户独立配额；
- 按用户记录请求量。

## 5. 日志策略

比赛版日志只建议保存：

```text
user_id
model
model_name
question_length
answer_length
input_tokens
output_tokens
total_tokens
latency_ms
created_at
```

不建议长期保存完整问题和回答。如果需要调试，可以在本地临时开启详细日志，但不要上传包含隐私内容的日志文件。

## 6. 请求限制

为了避免影响学校 XipuAI 服务，建议后续加入：

- 每个用户每分钟请求限制；
- 每个用户每日请求限制；
- 并发请求限制；
- 失败重试上限；
- 超时控制；
- 管理员禁用异常用户。

## 7. 答辩表述建议

可以这样说明：

> 本项目没有绕过学校认证，也没有读取他人登录状态。系统使用用户本人在本地手动登录后保存的授权状态访问学校 XipuAI。中转站重点展示校内模型服务的统一接入、接口封装、模型区分、日志统计和安全治理能力。项目通过 `.gitignore`、`.dockerignore` 和 release 打包规则排除登录状态与隐私文件，避免敏感信息进入 GitHub 或发布包。
