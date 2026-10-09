# 麦当劳 MCP 集成说明

## 服务与连接方式

本项目连接麦当劳中国提供的远程 MCP Server：

```text
https://mcp.mcd.cn
```

- 传输协议：Streamable HTTP；
- Python SDK：`mcp`；
- 认证方式：`Authorization: Bearer ${MCD_MCP_TOKEN}`；
- Token 只从环境变量读取，不写入配置、日志或 Git；
- 示例配置见 [`mcp-config.example.json`](mcp-config.example.json)。

官方资料：

- [麦当劳 MCP Server 使用指南](https://github.com/M-China/mcd-mcp-server)
- [麦当劳程序员创意开发大赛](https://github.com/M-China/mcd-developer-innovation-challenge)

## 已完成的真实联调

以下工具均已使用真实 MCP Token 调用成功。联调发生于 2026-10-09，原始响应仅保存在本地临时文件中，没有提交到仓库。

### `query-nearby-stores`

用途：根据城市和公共地点关键词查询支持到店自提的真实门店。

本项目使用的输入：

```json
{
  "beType": 1,
  "searchType": 2,
  "city": "南京市",
  "keyword": "鼓楼医院"
}
```

真实返回为门店对象数组，已确认包含：

```text
storeCode
storeName
address
distance
businessStatus
businessStartTime
businessEndTime
longitude
latitude
reservation
reservationTimeOptions
```

演示时只展示门店名称、距离、营业状态和预约能力，由用户明确选择门店。详细地址和经纬度不写入项目文件。

### `query-meals`

用途：查询用户所选门店的实时菜单和菜单价格。

当前 v1 使用到店自提场景：

```json
{
  "storeCode": "1990696",
  "orderType": 1,
  "beType": 1
}
```

到店自提场景不得传递 `beCode`。真实返回的核心结构为：

```text
data.categories[]
  name
  meals[]
    code
    tags?

data.meals
  <productCode>
    name
    image
    currentPrice
    originalPrice
    canWithOrder
```

在联调门店中共返回 15 个分类、128 个餐品。`productCode` 是 `meals` 对象的键，价格字段为字符串，因此项目会显式转换为 `Decimal`。

### `list-nutrition-foods`

用途：查询麦当劳常见餐品的真实营养数据。该工具不需要输入参数：

```json
{}
```

真实响应的 `structuredContent.data` 是紧凑表格字符串，而不是 JSON 数组：

```text
[N]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  ...
```

联调时返回 160 条记录，字段包括：

```text
productName
nutritionDescription
energyKj
energyKcal
protein
fat
carbohydrate
sodium
calcium
```

项目对表头、行数、字段数量和数值进行严格校验。菜单与营养数据只按完整餐品名称精确关联；无法匹配或存在冲突时，营养值保持为空，不进行模糊猜测。

## 实际调用流程

```text
用户输入人数、预算和公共地点
        ↓
query-nearby-stores
        ↓
用户选择门店
        ↓
query-meals + list-nutrition-foods
        ↓
本地解析、主餐过滤和精确营养关联
        ↓
确定性生成三套方案
        ↓
用户选择，流程停止
```

真实只读闭环命令为：

```powershell
uv run mcd-plan-live `
  --store-code "1990696" `
  --people 6 `
  --budget 180 `
  --calorie-conscious 2 `
  --dietary-goal "丰富一点" `
  --dietary-goal "控制热量" `
  --output "mcd_live_plans.json"
```

该命令只调用 `query-meals` 和 `list-nutrition-foods`。门店选择通过单独的只读 `query-nearby-stores` 步骤完成。

## 数据规范化与业务价值

项目没有把配餐完全交给模型自由生成，而是使用确定性 Python 引擎：

- 使用菜单实时 `currentPrice` 计算预估总价；
- 将促销展示分类、多分类引用和餐品映射规范化；
- 排除酱料、单独饮品、甜品、儿童附属商品和份量不明的多人拼盘；
- 最省钱和品类丰富方案使用所有合格主餐；
- 营养相对均衡方案只使用具有可靠真实热量数据的候选；
- 所有方案必须满足人数和预算约束，并保持稳定、可测试的输出。

在已验证的南京门店示例中：

- 实时菜单餐品：128；
- 合格主餐候选：57；
- 具有精确营养匹配的候选：12；
- 成功生成最省钱、营养相对均衡和品类最丰富三套方案。

## 尚未调用的工具

通过真实 `tools/list` 共发现 35 个 MCP Tools。以下能力虽然与未来流程相关，但当前版本尚未调用，也不应被描述为已经完成：

- `query-meal-detail`；
- `query-store-coupons`；
- `query-promotions`；
- `query-meal-assistance`；
- `calculate-price`；
- `create-order`。

企业团餐外送需要 `delivery-query-addresses` 和 `delivery-query-stores`，会涉及用户地址数据，当前 v1 未实现。项目现阶段只支持到店自提。

## 安全与副作用边界

- 工具枚举、门店查询、菜单查询和营养查询均为只读操作；
- 当前真实闭环不会调用精确计价或订单创建；
- 展示三套方案后必须等待用户选择；
- 用户选择方案不等于授权创建订单；
- 将来接入 `calculate-price` 时，必须先由用户确认候选方案；
- `create-order` 必须在展示门店、餐品、数量、取餐方式和最终价格后再次获得明确确认；
- 不自动领券、取消订单、创建地址、兑换积分或参与抽奖；
- 不提交 Token、手机号、地址、订单号、traceId 或原始个人响应。
