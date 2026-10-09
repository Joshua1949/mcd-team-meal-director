---
name: mcd-team-meal-director
description: Use real McDonald's China MCP menu and nutrition data to create three budget-aware pickup meal plans for a group. Apply when users need a team meal, group dining, overtime meal, or multi-person McDonald's recommendation; do not use it for medical nutrition advice or autonomous ordering.
---

# 麦麦团建导演

为多人到店自提场景生成三套真实数据候选方案：最省钱、营养相对均衡、品类最丰富。当前 v1 只支持到店自提，不要把企业团餐外送描述为已实现能力。

## 收集需求

确认以下信息，缺失时一次只询问一个会影响结果的问题：

- 人数；
- 总预算；
- 城市和公共地点关键词，不索取家庭或公司详细地址；
- 希望控制热量的人数；
- 其他饮食目标。

人数、预算必须大于零，控制热量人数不得超过总人数。

## 只读规划流程

1. 调用 `query-nearby-stores`，传入 `beType=1`、`searchType=2`、城市和公共地点关键词。
2. 展示门店名称、距离、营业状态和预约能力，让用户明确选择门店。
3. 对所选门店调用 `query-meals`，传入 `storeCode`、`orderType=1`、`beType=1`；到店自提不得传 `beCode`。
4. 调用无参数的 `list-nutrition-foods`。
5. 使用真实 `currentPrice`，并仅按完整餐品名称精确关联营养数据。未匹配时标记为暂无营养数据，不做模糊猜测。
6. 只将单人餐、汉堡或卷、1+1、厚牛堡和 500 大卡套餐等可作为一人主餐的分类用于规划。酱料、单独饮品、甜品、儿童附属商品及份量不明的多人拼盘不得独立占一人份。
7. 生成并按固定顺序展示三套方案：最省钱、营养相对均衡、品类最丰富。

仓库环境中优先运行 `mcd-plan-live`，该命令只调用 `query-meals` 和 `list-nutrition-foods`，并复用经过测试的确定性规划器。

## 解释结果

- 清楚列出餐品、数量、预估总价和方案差异。
- 营养相对均衡方案使用启发式热量目标，仅用于候选方案比较，不构成医疗或营养建议。
- 菜单价格是方案阶段的预估值，实际价格、供应状态和可用优惠以麦当劳官方实时结果为准。
- 如果缺少足够的真实营养数据或预算内没有可行方案，应说明限制，不得编造数据。

## 确认与副作用边界

展示三套方案后必须等待用户明确选择。选择方案不等于授权下单。

- 用户确认方案前，不调用 `calculate-price`。
- 任何情况下都不得自动调用 `create-order`。
- 创建订单前必须再次展示门店、餐品、数量、取餐方式和最终价格，并获得用户对“创建订单”的明确确认。
- 不自动领券、取消订单、创建地址、兑换积分或执行抽奖。
- 不输出、记录或提交 MCP Token、手机号、地址、订单号等敏感信息。

## 输出格式

先给出三套方案的简明对比，再请用户选择一个方案。没有收到选择时停止，不继续计价或下单。
