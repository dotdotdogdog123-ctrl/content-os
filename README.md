# Content OS — 财经视频选题雷达

公开网页： https://dotdotdogdog123-ctrl.github.io/content-os/

## 数据原则

- **视频优先，新闻分开**：`data/videos.json` 仅保留有平台视频 ID 的公开链接；`data/topics.json` 是新闻背景参考，绝不冒充视频。
- **公开视频发现，不是全网热榜**：从 YouTube 官方频道 Atom RSS（最近最多约 15 条/频道）和 B站公开分区/热门接口采集。观察名单包含小Lin说、美投讲美股、一口新飯、財經M平方、游庭皓、懶錢包、老王愛說笑。频道的选择具有主观性，不代表市场总体热度或推荐质量。
- **不绕过访问限制**：不用账号、cookie、签名破解、反爬绕过或私人接口。公开接口返回错误码、空结果都原样记录在 `errors` 和 `source_stats`。
- **只依据标题归类**：财经方向与“访谈/对话、讲解/科普、口播/观点、热点争议”都是关键词启发式；`format_evidence` 会标明“标题推断”或“待人工核验”。`manually_verified=false`，不代表已经观看、验证或认可视频观点。
- **数字不补造**：YouTube Atom RSS 提供标题、ID 和发布时间；部分 feed 的 `media:statistics` 还提供真实播放量，但不保证存在。赞/评论没有可直接使用的完整指标，默认 `null`。B站公开接口有返回对应统计字段时才填写。
- **可选 YouTube 官方数据**：在仓库 Actions secrets 中自行设置 `YOUTUBE_API_KEY`（YouTube Data API v3 的合法 API key），脚本才会尝试官方 `videos.list(part=statistics)` 获取公开播放量、赞、评论。未设置时仍可正常使用 RSS；不需要配置账号 cookie。脚本不会打印 API key 或带 key 的请求 URL。
- **互动率口径不同**：B站=(赞+评论+收藏+分享)/播放；YouTube=(赞+评论)/播放，只有所有必需字段真实存在且播放>0才计算。**不能跨平台比较这两个百分比**。
- **样本内热度**：同平台、同发布时间桶（0–7、8–30、31–180天）至少 3 条有播放数据时，计算“视频播放量 ÷ 组内播放量中位数”。这只是当前采样集内相对值，不是平台官方热榜，也没有控制频道粉丝规模、发布时间和曝光。
- **失败与过期**：每个来源记录 fetched/matched_new/status；若全轮无匹配，保留上次非空视频并设置 `data_stale=true`，不会把历史结果伪装为新抓取。页面显示时间戳和质量摘要。

## 本地验证

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
python scripts/video_radar.py  # 需要能访问公开来源；不需要 API key
python -m json.tool data/videos.json >/dev/null
```

GitHub Actions 的 `.github/workflows/update-topics.yml` 每天北京时间约 09:15、17:15 运行，并在脚本或工作流修改时尝试更新数据。GitHub Pages 的发布可能晚于数据提交；检查页面时可刷新缓存。

## 已知限制和后续

1. B站公开接口可能返回 -352、-404 或零条候选；不能视为“财经视频不存在”，也不会绕过平台限制。
2. YouTube 官方 RSS 只覆盖选定频道最近约 15 条，且有时返回的内容不符合财经分类；网页不能宣称覆盖抖音、小红书或视频号。
3. 没有官方 YouTube Data API key 时，YouTube 互动率为“未提供”；如 Atom 有真实播放量且同平台同时间桶样本足够，仍可计算样本内相对播放热度。**缺失不等于 0**。
4. 尚无自动观看/人工核验机制。收藏策划卡后，仍需打开原视频核对标题、实际视频形式、论点、关键数据和反方证据。
5. 如需更广覆盖，应先核实频道身份及其公开 RSS，再增补到 `YOUTUBE_CHANNELS`；不建议随意接入未经授权的第三方抓取服务。
