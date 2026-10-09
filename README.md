# 麦麦团建导演

多人点餐最麻烦的往往不是找不到餐品，而是很难同时照顾预算、热量和口味。麦麦团建导演面向办公室聚餐、小组活动等多人用餐场景，根据人数、总预算和饮食目标生成三套可以直接比较的方案：

1. 最省钱方案；
2. 营养相对均衡方案；
3. 品类最丰富方案。

项目通过麦当劳中国 MCP 查询真实门店、实时菜单和营养信息，再交给确定性 Python 引擎计算，不让大模型猜价格或口算组合。当前 v1 支持到店自提的只读规划，不执行精确计价或创建订单。没有 Token 时也可以用内置模拟数据运行 dry-run。

一句话概括：它不替团队武断地选一份餐，而是把“省钱、均衡、丰富”三种取舍摆在一起，让组织者自己决定。

## 当前状态

- 已完成 Python 数据模型和输入校验；
- 已完成三种可测试、可复现的确定性配餐策略；
- 已提供模拟菜单和 dry-run CLI；
- 已真实联调门店、菜单和营养查询；
- 已提供真实数据只读配餐命令；
- 当前仅支持到店自提，不支持企业团餐外送；
- 不执行精确计价或创建真实订单。

## 环境要求

- Python 3.11 或更高版本；
- [uv](https://docs.astral.sh/uv/)；
- Windows PowerShell、macOS 或 Linux 终端。

## 安装

克隆仓库并安装依赖：

```powershell
git clone https://github.com/Joshua1949/mcd-team-meal-director.git
Set-Location mcd-team-meal-director
uv sync --dev
```

该命令会创建项目虚拟环境、安装运行与测试依赖，并按照 `uv.lock` 复现依赖版本。

## 作为 Skill 使用

[`SKILL.md`](SKILL.md) 负责定义对话流程和安全边界，Python 程序负责读取 MCP 数据并计算方案。支持自定义 Skill 的客户端可以把整个项目目录加入其 Skill 目录；不同客户端的目录位置和加载方式可能不同，请以对应客户端文档为准。

加载后，可以这样发起请求：

> 帮我给 6 个人安排一顿麦当劳，预算 180 元，其中 2 个人想控制热量。地点在南京鼓楼医院附近，给我最省钱、相对均衡和品类丰富三套方案。

Skill 会先查询附近门店并让用户选择，然后读取该门店的菜单和营养数据。三套方案展示完毕后流程停止，不会自动计价或下单。

## Dry-run 演示

在项目根目录运行：

```powershell
uv run python -m mcd_team_meal_director `
  --people 6 `
  --budget 180 `
  --calorie-conscious 2 `
  --dietary-goal "丰富一点" `
  --dietary-goal "控制热量"
```

macOS 或 Linux 可以使用反斜杠续行：

```bash
uv run python -m mcd_team_meal_director \
  --people 6 \
  --budget 180 \
  --calorie-conscious 2 \
  --dietary-goal "丰富一点" \
  --dietary-goal "控制热量"
```

默认菜单文件为 [`examples/mock_menu.json`](examples/mock_menu.json)。也可以通过 `--menu` 指定另一份符合相同结构的 dry-run JSON 文件。

## 真实 MCP 演示

### 1. 配置 Token

从[麦当劳 MCP 官方页面](https://open.mcd.cn/mcp)申请 Token。下面的写法会在终端中提示输入，避免 Token 出现在命令历史里：

```powershell
$env:MCD_MCP_TOKEN = Read-Host "请输入 MCD MCP Token"
$desktop = [Environment]::GetFolderPath('Desktop')
```

不要把真实 Token 写入仓库、配置示例、命令脚本或 Issue。

### 2. 查询到店自提门店

使用城市和公共地点关键词，不要输入家庭或公司的详细地址：

```powershell
uv run mcd-find-stores `
  --city "南京市" `
  --keyword "鼓楼医院" `
  --output "$desktop\mcd_stores.json"
```

查看结果并选择一个 `storeCode`。把它保存到变量中，例如：

```powershell
$storeCode = "替换为上一步选出的 storeCode"
```

### 3. 生成真实数据方案

```powershell
uv run mcd-plan-live `
  --store-code $storeCode `
  --people 6 `
  --budget 180 `
  --calorie-conscious 2 `
  --dietary-goal "丰富一点" `
  --dietary-goal "控制热量" `
  --output "$desktop\mcd_live_plans.json"
```

命令只调用 `query-meals` 和 `list-nutrition-foods`，不会调用优惠券、精确计价或下单工具。完成后可清除当前会话中的 Token：

```powershell
Remove-Item Env:MCD_MCP_TOKEN
```

### 真实运行结果

2026-10-09 的南京门店联调使用了 6 人、180 元总预算、2 人控制热量的输入。MCP 返回 128 个菜单餐品；经过主餐资格过滤后得到 57 个候选，其中 12 个与营养记录精确匹配。

| 方案 | 餐品 | 预估总价 | 适合什么情况 |
| --- | --- | ---: | --- |
| 最省钱 | 精选超值随心配 × 6 | ¥83.40 | 预算优先，接受多人选择相同餐品 |
| 营养相对均衡 | 芝士安格斯厚牛堡 × 4；培根蔬萃双层牛堡 × 2 | ¥176.00 | 4 名普通成员和 2 名控热量成员分别匹配启发式热量目标 |
| 品类最丰富 | 精选超值随心配、牛肉堡单品精选、麦香鸡、酥脆无双套餐、大堡口福三件套、人气超值四件套随心选各 1 份 | ¥116.30 | 希望 6 个人尽量吃到不同品类 |

这些金额来自当时门店菜单的 `currentPrice`，是方案阶段的预估值，不代表最终结算价格。具体工具结构和调用流程见 [`MCP_INTEGRATION.md`](MCP_INTEGRATION.md)。

## 目标用户

- 负责办公室午餐、加班餐或小型团建的组织者；
- 需要在固定总预算内照顾多人选择的行政、项目负责人或社群组织者；
- 希望兼顾热量目标，但不需要医疗营养建议的小团队；
- 想比较不同取舍，而不是只得到一个黑盒推荐的人。

## 配餐规则

- 最省钱方案：在合格主餐中为每个人选择单价最低的餐品；
- 营养相对均衡方案：在预算内最小化普通成员和控热量成员的热量目标偏差；
- 品类最丰富方案：在每人一份合格主餐的前提下，尽可能增加不同餐品品类；
- 所有价格均为方案生成阶段的预估值；如未来接入 `calculate-price`，仍必须先由用户确认候选方案。

营养均衡策略仅用于候选方案比较，不构成营养或医疗建议。

## 测试

```powershell
uv run pytest
```

当前共有 57 项自动化测试，覆盖输入校验、三种配餐策略、MCP 响应解析、菜单筛选和 CLI 输出。

## 安全边界

- 不在仓库中保存 MCP Token、手机号、地址、订单号或其他个人数据；
- 默认使用 dry-run，不执行真实下单、取消订单、领券或积分兑换；
- 精确计价或创建订单前必须获得用户明确确认；
- 示例配置只能引用环境变量，不能包含真实密钥。

## 项目结构

```text
.
├── examples/                     # dry-run 模拟数据
├── src/mcd_team_meal_director/  # 数据模型、配餐算法和 CLI
├── tests/                        # 自动化测试
├── CONTEST_DECLARATION.md        # 官方参赛声明，内容不可修改
├── MCP_INTEGRATION.md            # 真实 MCP 集成与安全边界
├── SKILL.md                      # Skill 工作流
├── mcp-config.example.json       # 不含真实 Token 的配置示例
├── pyproject.toml
└── uv.lock
```

## License

[MIT](LICENSE)

本项目是麦当劳程序员创意开发大赛参赛作品，由参赛者独立开发，并非麦当劳官方产品。餐品、价格和供应状态以麦当劳官方实时结果为准。
