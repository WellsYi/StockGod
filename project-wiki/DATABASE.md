# 数据库设计

## 概览

6 张表，全部 InnoDB，utf8mb4，`id` 统一 BIGINT。

| 表 | 用途 | 核心字段 | 数据量预估 |
|----|------|---------|-----------|
| `signals` | 股票信号记录 | code, type, time, price, llm_analysis | ~50条/天 |
| `price_snapshots` | 价格快照 | code, time, price, signal_id | ~500条/天 |
| `llm_logs` | LLM 调用日志 | scenario, input/output, tokens | ~50条/天 |
| `signal_accuracy` | 信号准确率 | signal_id, price_5/15/30min, verdict | ~50条/天 |
| `bili_dynamics` | B站动态 | dynamic_id, author, content, summary | ~5条/天 |
| `limit_up_daily` | 每日涨停 | code, price, limit_times, reason, concepts | ~50条/天(交易日) |

## ER 关系

```
signals ──1:1──→ signal_accuracy    （信号→准确率追踪）
signals ──1:N──→ price_snapshots    （信号→关联快照）
llm_logs            （按 stock_code 逻辑关联）
bili_dynamics       （独立表）
limit_up_daily      （独立表，按交易日+代码唯一）
```

## 表结构

### signals — 股票信号记录

```sql
CREATE TABLE signals (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code    VARCHAR(10) NOT NULL,
    stock_name    VARCHAR(50) NOT NULL,
    signal_type   VARCHAR(50) NOT NULL COMMENT '异常放量拉升/急涨/VWAP突破/逼近涨停/连续拉升/连续砸盘',
    trigger_time  DATETIME(3) NOT NULL COMMENT '精确到毫秒',
    price         DECIMAL(10,3) NOT NULL,
    change_pct    DECIMAL(6,3) COMMENT '触发时涨跌幅',
    signal_detail JSON COMMENT '量比/换手率等技术参数',
    llm_analysis  TEXT COMMENT 'LLM 解读',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code_time (stock_code, trigger_time),
    INDEX idx_type_time (signal_type, trigger_time),
    INDEX idx_date (trigger_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票信号记录';
```

索引说明：
- `idx_code_time` — 查询某只股票的历史信号
- `idx_type_time` — 按信号类型聚合统计
- `idx_date` — 按日期筛选

### price_snapshots — 价格快照

```sql
CREATE TABLE price_snapshots (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code    VARCHAR(10) NOT NULL,
    snapshot_time DATETIME(3) NOT NULL,
    price         DECIMAL(10,3) NOT NULL,
    change_pct    DECIMAL(6,3),
    volume_ratio  DECIMAL(6,2),
    signal_id     BIGINT DEFAULT NULL COMMENT '关联信号ID',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code_time (stock_code, snapshot_time),
    INDEX idx_signal (signal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='价格快照（信号准确率追踪用）';
```

说明：信号触发时记一条"触发价"，之后 5min/15min/30min 各记一条"跟踪价"，用于算信号准确率。

### llm_logs — LLM 调用日志

```sql
CREATE TABLE llm_logs (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario      VARCHAR(50) NOT NULL COMMENT 'new_stock/signal/batch/rag/...',
    input_text    TEXT NOT NULL,
    output_text   TEXT NOT NULL,
    stock_code    VARCHAR(10) DEFAULT NULL,
    model         VARCHAR(50),
    tokens_input  INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    INDEX idx_stock (stock_code),
    INDEX idx_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LLM 调用日志（RAG数据源+算账）';
```

两个用途：
1. **算账** — 每天花了多少 API 费用
2. **RAG 数据源** — 历史 LLM 分析结果可检索

### signal_accuracy — 信号准确率

```sql
CREATE TABLE signal_accuracy (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    signal_id     BIGINT NOT NULL UNIQUE,
    price_5min    DECIMAL(10,3) COMMENT '触发后5分钟价格',
    price_15min   DECIMAL(10,3) COMMENT '触发后15分钟价格',
    price_30min   DECIMAL(10,3) COMMENT '触发后30分钟价格',
    price_close   DECIMAL(10,3) COMMENT '收盘价',
    close_change  DECIMAL(6,3) COMMENT '触发→收盘涨跌幅',
    verdict       ENUM('pending','hit','miss','uncertain') DEFAULT 'pending',
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES signals(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号准确率追踪';
```

verdict 判断逻辑（后续代码实现）：
- 放量拉升/急涨信号：30min 后价格高于触发价 → hit
- 急跌/砸盘信号：30min 后价格低于触发价 → hit
- 其他情况按具体信号类型定义

### bili_dynamics — B站动态记录

```sql
CREATE TABLE bili_dynamics (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    dynamic_id    VARCHAR(50) NOT NULL UNIQUE,
    author        VARCHAR(100) NOT NULL,
    content       TEXT NOT NULL,
    llm_summary   TEXT COMMENT 'LLM 摘要',
    link_url      VARCHAR(500),
    pushed_at     DATETIME(3) DEFAULT NULL COMMENT '推送时间',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_author (author),
    INDEX idx_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='B站动态记录';
```

### limit_up_daily — 每日涨停记录

```sql
CREATE TABLE limit_up_daily (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date    DATE NOT NULL COMMENT '交易日',
    stock_code    VARCHAR(10) NOT NULL,
    stock_name    VARCHAR(50) NOT NULL,
    price         DECIMAL(10,3) NOT NULL COMMENT '收盘价(涨停价)',
    change_pct    DECIMAL(6,3) COMMENT '涨幅',
    turnover_rate DECIMAL(6,2) COMMENT '换手率',
    fd_amount     DECIMAL(10,2) COMMENT '封单金额(亿)',
    limit_times   INT DEFAULT 1 COMMENT '连板次数',
    board_type    VARCHAR(20) COMMENT '主板/创业板/科创板',
    reason_llm    TEXT COMMENT 'LLM 分析的涨停原因',
    reason_tags   JSON COMMENT '原因标签(板块/消息/业绩等)',
    concept_tags  JSON COMMENT '所属概念板块',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_code (trade_date, stock_code),
    INDEX idx_date (trade_date),
    INDEX idx_times (limit_times)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日涨停记录';
```

## 约定

- 所有 `id` 用 BIGINT（为未来海量数据预留）
- 时间字段带毫秒的用 `DATETIME(3)`（10秒轮询，秒精度不够）
- JSON 字段存储变长技术参数
- 外键只在必要的准确率表使用，其他表用代码逻辑关联
