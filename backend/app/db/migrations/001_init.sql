-- ============================================================
-- StockGod 数据库初始化脚本
-- 运行: mysql -u root -p < 001_init.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS stock_god
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE stock_god;

-- -----------------------------------------------------------
-- 1. signals — 股票信号记录
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS signals (
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

-- -----------------------------------------------------------
-- 2. price_snapshots — 价格快照
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_snapshots (
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

-- -----------------------------------------------------------
-- 3. llm_logs — LLM 调用日志
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_logs (
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

-- -----------------------------------------------------------
-- 4. signal_accuracy — 信号准确率追踪
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS signal_accuracy (
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

-- -----------------------------------------------------------
-- 5. bili_dynamics — B站动态记录
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS bili_dynamics (
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

-- -----------------------------------------------------------
-- 6. limit_up_daily — 每日涨停记录
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS limit_up_daily (
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

-- -----------------------------------------------------------
-- 7. stock_pool — 股票池
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_pool (
    stock_code  VARCHAR(10) PRIMARY KEY,
    stock_name  VARCHAR(50) NOT NULL,
    market      TINYINT NOT NULL COMMENT '0=深证 1=上证',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票池';
