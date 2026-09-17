# Debug Session: miniprogram-cloud-login
- **Status**: [OPEN]
- **Issue**: 小程序在开发者工具中编译运行后无法登录；后端已推送到云托管。
- **Debug Server**: 待定
- **Log File**: .dbg/trae-debug-log-miniprogram-cloud-login.ndjson

## Reproduction Steps
1. 将后端 Django 项目推送到云托管环境。
2. 在微信开发者工具中编译运行小程序。
3. 进入登录页面，输入用户名和密码，点击登录。
4. 观察到登录失败（提示“登录失败”或类似错误）。

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | 小程序 `request.js` 中的 `BASE_URL` 仍指向本地 `http://127.0.0.1:8000`，未改为云托管 HTTPS 地址 | High | Low | ✅ 已确认：用户云托管公网域名为 `https://<你的云托管公网域名>`，代码仍为 `http://127.0.0.1:8000` |
| B | 微信小程序未将云托管域名加入 `request合法域名` 白名单，或使用了 HTTP 而非 HTTPS | High | Low | ⏳ 待确认：需用户检查小程序后台域名配置 |
| C | 云托管环境变量名称与后端 `settings.py` 不匹配（`MYSQL_USERNAME` vs `MYSQL_USER`，缺少 `MYSQL_DATABASE`/`MYSQL_PORT`） | High | Low | ✅ 已确认：截图中环境变量为 `MYSQL_USERNAME`/`MYSQL_ADDRESS`，后端读取 `MYSQL_USER`/`MYSQL_HOST`/`MYSQL_PORT` |
| D | 后端 `/api/auth/login/` 接口在云托管上返回错误（如用户不存在、CSRF、ALLOWED_HOSTS、CORS 等） | Low | Medium | ⏳ 待验证：修复 A/C 后复测 |
| E | 小程序登录页逻辑未正确调用 `login` 或错误处理覆盖了真实错误 | Low | Low | ⏳ 待验证 |

## Static Findings
- `miniapp/utils/request.js:1` 中 `BASE_URL` 硬编码为 `http://127.0.0.1:8000`。
- `rice_guard/settings.py:80` 中 `ALLOWED_HOSTS` 默认值为 `*`，若环境变量 `DJANGO_ALLOWED_HOSTS` 未包含云托管域名，则可能被拒绝。
- 后端默认使用 SQLite；云托管生产环境应配置 MySQL 环境变量。

## Log Evidence
- 用户反馈：重新推送部署失败，无明显报错。
- 本地验证：`python manage.py ensure_database --help` 命令可正常识别，代码本身无语法错误。
- 构建日志显示：镜像大小 1.16GB，Docker 镜像构建和推送均成功，但最终「Revision status create failed」。
- 待获取：容器运行日志、服务事件、服务监控，以确认 revision 创建失败的具体原因。

## Fix Applied
- 由于微信云托管默认公网域名无法配置到小程序 `request合法域名` 白名单，将小程序 API 请求改为微信推荐的 `wx.cloud.callContainer` 内网调用方式。
- `miniapp/app.js` 在 `onLaunch` 中增加 `wx.cloud.init()`。
- `miniapp/utils/request.js` 中 `request()` 改用 `wx.cloud.callContainer`，服务名 `<你的云托管服务名>`，无需 BASE_URL 和域名白名单即可发起请求。
- `uploadFile()` 与 `statistics.js` 中的下载/导出仍使用公网 `BASE_URL`，后续若需在体验版使用，仍需绑定自定义域名并配置白名单。
- 新增 `apps/diagnosis/management/commands/ensure_database.py`，启动时自动检测并创建 MySQL 数据库。
- 修改 `Dockerfile` 的 `CMD`，启动时自动执行：建库 → 迁移 → 收集静态文件 → 启动 gunicorn。

## Pending Actions
1. 在云托管控制台补充环境变量（确保后端使用 MySQL）：
   - `MYSQL_USER=root`
   - `MYSQL_PORT=3306`
   - `MYSQL_DATABASE=<你的数据库名>`（如没有单独建库，可先用 `rice_guard`）
2. 在云托管控制台设置生产环境变量：
   - `DJANGO_SECRET_KEY=<随机长字符串>`
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=<你的云托管公网域名>`
3. 重新推送代码并触发云托管部署；启动命令会自动完成建库、迁移、启动。
4. 在微信开发者工具中重新编译小程序并测试登录。

## Verification Conclusion
[待用户在完成上述步骤后复测]

