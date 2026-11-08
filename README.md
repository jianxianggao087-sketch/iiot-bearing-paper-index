# IIoT × 轴承故障检测 论文索引

## 是什么 / 不是什么

这是一个纯静态论文索引，收录工业物联网、边缘智能与轴承故障诊断交叉领域中已录用或已发表的期刊论文。数据来自 OpenAlex，SQLite 数据库与导出的 JSON 随仓库保存。

本站不提供通用论文搜索，不展示摘要，不存储或代理论文全文，也没有账号、收藏、评论、Cookie 或统计功能。标题链接直接跳转至 DOI 解析页面。

## 本地运行（3 步）

需要 Python 3.11+、Node.js 20+ 和 npm。

1. 安装依赖：

   ```bash
   python -m pip install -r requirements.txt
   npm ci
   ```

2. 将 `.env.example` 复制为 `.env`，填入 `OPENALEX_API_KEY`，再运行：

   ```bash
   python -m scripts.fetch_papers
   python -m scripts.export_json
   ```

3. 启动静态站点：

   ```bash
   npm run dev
   ```

构建命令为 `npm run build`。构建只读取仓库内的 JSON，不访问网络；若首次没有论文数据，可用 `ALLOW_EMPTY=1` 运行构建校验。

## 获取 OpenAlex API Key

访问 OpenAlex 的 API Keys 页面并提交邮箱，按确认邮件启用免费 Key。将 Key 放进本地 `.env` 的 `OPENALEX_API_KEY`，或添加为 GitHub 仓库 Secret `OPENALEX_API_KEY`。Key 只用于抓取 job，不参与静态构建。

## 数据口径与已知偏差

抓取使用 OpenAlex `/works`，限定期刊 article、开放获取的 accepted/published 版本以及近 5 年窗口。检索词聚焦轴承故障诊断与 IIoT/边缘智能，并用标题相关性闸门排除建筑、岩土等 `bearing` 歧义。默认 `SYNC_MODE=rescan`，每日重扫并按 OpenAlex Work ID 幂等更新。

「已录用/已发表」取决于 OpenAlex 的版本字段，是近似判断。只覆盖可验证开放获取版本；中文期刊和国内学报覆盖可能不足；标题不含 bearing 但摘要提及轴承的记录会被排除。引用数可能滞后，作者名未经消歧。过期记录仍保留在数据库中，但不在近 5 年列表展示。

## 部署到 GitHub Pages

1. 仓库 Settings → Pages → Source 选择 **GitHub Actions**。
2. Settings → Secrets and variables → Actions 中添加 `OPENALEX_API_KEY`。
3. 将仓库默认分支设为 `main`，手动触发 `Daily Paper Update`。
4. 工作流每日 UTC 06:00 抓取、提交数据库与 JSON，再构建并部署 Pages。

项目站点子路径由 `GITHUB_REPOSITORY` 自动设置；也可以通过 `BASE_PATH` 指定路径，通过 `SITE_URL` 指定站点域名。

## 版权与边界

论文标题、作者、期刊、年份和引用数等元数据来自 OpenAlex 并以 CC0 发布，本站保留来源标注。本站不存储、不缓存、不转码、不代理论文全文、PDF、HTML 全文或图片，也不展示摘要正文。所有全文入口仅为 DOI 链接，访问权限由出版社与读者机构决定。本站代码建议采用 MIT 许可。
