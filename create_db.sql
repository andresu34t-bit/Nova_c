-- ============================================================
-- NOVA CAPITAL GROUP — Script de creación de base de datos
-- PostgreSQL
-- Ejecutar como superusuario o con permisos suficientes
-- ============================================================

-- 1. Crear usuario y base de datos
-- (ejecutar solo si no existen; ajusta la contraseña)
-- CREATE USER nova_capital_user WITH PASSWORD 'tu_password_aqui';
-- CREATE DATABASE nova_capital_db OWNER nova_capital_user;
-- \c nova_capital_db

-- ============================================================
-- EXTENSIONES
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- DJANGO AUTH (tablas requeridas por AbstractUser)
-- ============================================================

CREATE TABLE IF NOT EXISTS auth_permission (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL,
    codename    VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_group (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id            SERIAL PRIMARY KEY,
    group_id      INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE (group_id, permission_id)
);

CREATE TABLE IF NOT EXISTS django_content_type (
    id       SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model     VARCHAR(100) NOT NULL,
    UNIQUE (app_label, model)
);

-- ============================================================
-- APP: accounts
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts_user (
    -- AbstractUser fields
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    password                    VARCHAR(128) NOT NULL,
    last_login                  TIMESTAMPTZ,
    is_superuser                BOOLEAN NOT NULL DEFAULT FALSE,
    username                    VARCHAR(150) NOT NULL UNIQUE,
    first_name                  VARCHAR(150) NOT NULL DEFAULT '',
    last_name                   VARCHAR(150) NOT NULL DEFAULT '',
    is_staff                    BOOLEAN NOT NULL DEFAULT FALSE,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Custom fields
    email                       VARCHAR(254) NOT NULL UNIQUE,
    phone                       VARCHAR(20) NOT NULL DEFAULT '',
    avatar                      VARCHAR(100),
    date_of_birth               DATE,
    country                     VARCHAR(100) NOT NULL DEFAULT '',
    city                        VARCHAR(100) NOT NULL DEFAULT '',
    address                     TEXT NOT NULL DEFAULT '',
    account_type                VARCHAR(20) NOT NULL DEFAULT 'standard'
                                    CHECK (account_type IN ('standard','premium','institutional')),
    verification_status         VARCHAR(20) NOT NULL DEFAULT 'unverified'
                                    CHECK (verification_status IN ('unverified','pending','verified','rejected')),
    email_verified              BOOLEAN NOT NULL DEFAULT FALSE,
    email_verification_token    VARCHAR(100) NOT NULL DEFAULT '',
    email_verification_sent_at  TIMESTAMPTZ,
    two_factor_enabled          BOOLEAN NOT NULL DEFAULT FALSE,
    balance                     NUMERIC(20,2) NOT NULL DEFAULT 0.00,
    total_deposited             NUMERIC(20,2) NOT NULL DEFAULT 0.00,
    total_withdrawn             NUMERIC(20,2) NOT NULL DEFAULT 0.00,
    last_login_ip               INET,
    last_activity               TIMESTAMPTZ,
    is_suspended                BOOLEAN NOT NULL DEFAULT FALSE,
    suspension_reason           TEXT NOT NULL DEFAULT '',
    referral_code               VARCHAR(20) UNIQUE NOT NULL DEFAULT '',
    referred_by_id              UUID REFERENCES accounts_user(id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices clave para accounts_user
CREATE INDEX IF NOT EXISTS idx_accounts_user_email          ON accounts_user(email);
CREATE INDEX IF NOT EXISTS idx_accounts_user_account_type   ON accounts_user(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_user_verification   ON accounts_user(verification_status);
CREATE INDEX IF NOT EXISTS idx_accounts_user_created_at     ON accounts_user(created_at DESC);

-- Tabla M2M: user ↔ groups
CREATE TABLE IF NOT EXISTS accounts_user_groups (
    id       SERIAL PRIMARY KEY,
    user_id  UUID    NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id)    ON DELETE CASCADE,
    UNIQUE (user_id, group_id)
);

-- Tabla M2M: user ↔ permissions
CREATE TABLE IF NOT EXISTS accounts_user_user_permissions (
    id            SERIAL PRIMARY KEY,
    user_id       UUID    NOT NULL REFERENCES accounts_user(id)       ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE (user_id, permission_id)
);

CREATE TABLE IF NOT EXISTS accounts_activitylog (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    action      VARCHAR(30) NOT NULL
                    CHECK (action IN (
                        'login','logout','login_failed','password_change',
                        'profile_update','deposit','withdrawal','trade',
                        '2fa_enabled','2fa_disabled','email_verified','suspicious'
                    )),
    description TEXT NOT NULL DEFAULT '',
    ip_address  INET,
    user_agent  TEXT NOT NULL DEFAULT '',
    location    VARCHAR(200) NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_activitylog_user_id   ON accounts_activitylog(user_id);
CREATE INDEX IF NOT EXISTS idx_activitylog_action    ON accounts_activitylog(action);
CREATE INDEX IF NOT EXISTS idx_activitylog_created   ON accounts_activitylog(created_at DESC);

CREATE TABLE IF NOT EXISTS accounts_kycdocument (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    document_type    VARCHAR(30) NOT NULL
                         CHECK (document_type IN (
                             'passport','id_card','drivers_license',
                             'utility_bill','bank_statement'
                         )),
    document_file    VARCHAR(100) NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','approved','rejected')),
    rejection_reason TEXT NOT NULL DEFAULT '',
    uploaded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON accounts_kycdocument(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status  ON accounts_kycdocument(status);

-- ============================================================
-- APP: trading
-- ============================================================

CREATE TABLE IF NOT EXISTS trading_asset (
    id                    BIGSERIAL PRIMARY KEY,
    symbol                VARCHAR(20)  NOT NULL UNIQUE,
    name                  VARCHAR(100) NOT NULL,
    asset_type            VARCHAR(20)  NOT NULL
                              CHECK (asset_type IN ('crypto','stock','forex','index','commodity')),
    current_price         NUMERIC(20,8) NOT NULL DEFAULT 0,
    price_change_24h      NUMERIC(10,4) NOT NULL DEFAULT 0,
    price_change_pct_24h  NUMERIC(10,4) NOT NULL DEFAULT 0,
    volume_24h            NUMERIC(30,2) NOT NULL DEFAULT 0,
    market_cap            NUMERIC(30,2) NOT NULL DEFAULT 0,
    high_24h              NUMERIC(20,8) NOT NULL DEFAULT 0,
    low_24h               NUMERIC(20,8) NOT NULL DEFAULT 0,
    image_url             VARCHAR(200) NOT NULL DEFAULT '',
    coingecko_id          VARCHAR(100) NOT NULL DEFAULT '',
    is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
    rank                  INTEGER      NOT NULL DEFAULT 0,
    last_updated          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_symbol      ON trading_asset(symbol);
CREATE INDEX IF NOT EXISTS idx_asset_type        ON trading_asset(asset_type);
CREATE INDEX IF NOT EXISTS idx_asset_rank        ON trading_asset(rank);
CREATE INDEX IF NOT EXISTS idx_asset_active      ON trading_asset(is_active);

CREATE TABLE IF NOT EXISTS trading_order (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID         NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    asset_id         BIGINT       NOT NULL REFERENCES trading_asset(id) ON DELETE CASCADE,
    order_type       VARCHAR(20)  NOT NULL DEFAULT 'market'
                         CHECK (order_type IN ('market','limit','stop','stop_limit')),
    side             VARCHAR(10)  NOT NULL
                         CHECK (side IN ('buy','sell')),
    quantity         NUMERIC(20,8) NOT NULL,
    price            NUMERIC(20,8),
    filled_price     NUMERIC(20,8),
    filled_quantity  NUMERIC(20,8) NOT NULL DEFAULT 0,
    total_value      NUMERIC(20,2) NOT NULL DEFAULT 0,
    fee              NUMERIC(10,4) NOT NULL DEFAULT 0,
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','filled','partially_filled','cancelled','rejected')),
    notes            TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    filled_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_order_user_id    ON trading_order(user_id);
CREATE INDEX IF NOT EXISTS idx_order_asset_id   ON trading_order(asset_id);
CREATE INDEX IF NOT EXISTS idx_order_status     ON trading_order(status);
CREATE INDEX IF NOT EXISTS idx_order_created    ON trading_order(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_side       ON trading_order(side);

CREATE TABLE IF NOT EXISTS trading_watchlist (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID   NOT NULL REFERENCES accounts_user(id)  ON DELETE CASCADE,
    asset_id         BIGINT NOT NULL REFERENCES trading_asset(id)  ON DELETE CASCADE,
    added_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes            TEXT NOT NULL DEFAULT '',
    alert_price_high NUMERIC(20,8),
    alert_price_low  NUMERIC(20,8),
    UNIQUE (user_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON trading_watchlist(user_id);

-- ============================================================
-- APP: portfolio
-- ============================================================

CREATE TABLE IF NOT EXISTS portfolio_position (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID   NOT NULL REFERENCES accounts_user(id)  ON DELETE CASCADE,
    asset_id       BIGINT NOT NULL REFERENCES trading_asset(id)  ON DELETE CASCADE,
    quantity       NUMERIC(20,8) NOT NULL,
    avg_buy_price  NUMERIC(20,8) NOT NULL,
    current_price  NUMERIC(20,8) NOT NULL DEFAULT 0,
    is_open        BOOLEAN NOT NULL DEFAULT TRUE,
    opened_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at      TIMESTAMPTZ,
    realized_pnl   NUMERIC(20,2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_position_user_id  ON portfolio_position(user_id);
CREATE INDEX IF NOT EXISTS idx_position_asset_id ON portfolio_position(asset_id);
CREATE INDEX IF NOT EXISTS idx_position_is_open  ON portfolio_position(is_open);
CREATE INDEX IF NOT EXISTS idx_position_opened   ON portfolio_position(opened_at DESC);

CREATE TABLE IF NOT EXISTS portfolio_portfoliosnapshot (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    total_value   NUMERIC(20,2) NOT NULL,
    cash_balance  NUMERIC(20,2) NOT NULL,
    total_pnl     NUMERIC(20,2) NOT NULL DEFAULT 0,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_user_id ON portfolio_portfoliosnapshot(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_date    ON portfolio_portfoliosnapshot(snapshot_date DESC);

-- ============================================================
-- APP: finances
-- ============================================================

CREATE TABLE IF NOT EXISTS finances_transaction (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL
                         CHECK (transaction_type IN (
                             'deposit','withdrawal','fee','bonus',
                             'transfer','trade_buy','trade_sell'
                         )),
    amount           NUMERIC(20,2) NOT NULL,
    currency         VARCHAR(10) NOT NULL DEFAULT 'USD',
    status           VARCHAR(20) NOT NULL DEFAULT 'pending'
                         CHECK (status IN (
                             'pending','processing','completed',
                             'failed','cancelled','reversed'
                         )),
    payment_method   VARCHAR(30) NOT NULL DEFAULT 'internal'
                         CHECK (payment_method IN (
                             'bank_transfer','credit_card','debit_card',
                             'crypto','paypal','internal'
                         )),
    reference        VARCHAR(100) NOT NULL DEFAULT '',
    description      TEXT NOT NULL DEFAULT '',
    balance_before   NUMERIC(20,2) NOT NULL DEFAULT 0,
    balance_after    NUMERIC(20,2) NOT NULL DEFAULT 0,
    fee_amount       NUMERIC(10,4) NOT NULL DEFAULT 0,
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_transaction_user_id  ON finances_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_type     ON finances_transaction(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transaction_status   ON finances_transaction(status);
CREATE INDEX IF NOT EXISTS idx_transaction_created  ON finances_transaction(created_at DESC);

CREATE TABLE IF NOT EXISTS finances_bankaccount (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    bank_name        VARCHAR(100) NOT NULL,
    account_holder   VARCHAR(100) NOT NULL,
    account_number   VARCHAR(50)  NOT NULL,
    routing_number   VARCHAR(50)  NOT NULL DEFAULT '',
    iban             VARCHAR(50)  NOT NULL DEFAULT '',
    swift_code       VARCHAR(20)  NOT NULL DEFAULT '',
    currency         VARCHAR(10)  NOT NULL DEFAULT 'USD',
    is_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    is_primary       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bankaccount_user_id ON finances_bankaccount(user_id);

-- ============================================================
-- APP: markets
-- ============================================================

CREATE TABLE IF NOT EXISTS markets_marketdata (
    id           BIGSERIAL PRIMARY KEY,
    symbol       VARCHAR(20) NOT NULL,
    asset_type   VARCHAR(20) NOT NULL,
    data         JSONB NOT NULL DEFAULT '{}',
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, asset_type)
);

CREATE INDEX IF NOT EXISTS idx_marketdata_symbol ON markets_marketdata(symbol);

CREATE TABLE IF NOT EXISTS markets_economicevent (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    currency    VARCHAR(10)  NOT NULL,
    impact      VARCHAR(10)  NOT NULL CHECK (impact IN ('low','medium','high')),
    event_date  TIMESTAMPTZ  NOT NULL,
    actual      VARCHAR(50)  NOT NULL DEFAULT '',
    forecast    VARCHAR(50)  NOT NULL DEFAULT '',
    previous    VARCHAR(50)  NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_economicevent_date   ON markets_economicevent(event_date);
CREATE INDEX IF NOT EXISTS idx_economicevent_impact ON markets_economicevent(impact);

-- ============================================================
-- APP: news
-- ============================================================

CREATE TABLE IF NOT EXISTS news_newsarticle (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    source          VARCHAR(100) NOT NULL,
    source_url      VARCHAR(200) NOT NULL,
    image_url       VARCHAR(200) NOT NULL DEFAULT '',
    category        VARCHAR(20) NOT NULL DEFAULT 'general'
                        CHECK (category IN ('crypto','stocks','forex','economy','technology','general')),
    published_at    TIMESTAMPTZ NOT NULL,
    is_featured     BOOLEAN NOT NULL DEFAULT FALSE,
    sentiment       VARCHAR(20) NOT NULL DEFAULT '',
    related_symbols VARCHAR(200) NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_category     ON news_newsarticle(category);
CREATE INDEX IF NOT EXISTS idx_news_published    ON news_newsarticle(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_is_featured  ON news_newsarticle(is_featured);

-- ============================================================
-- DJANGO INTERNALS (sessions, admin log, migrations)
-- ============================================================

CREATE TABLE IF NOT EXISTS django_session (
    session_key  VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_expire ON django_session(expire_date);

CREATE TABLE IF NOT EXISTS django_migrations (
    id      BIGSERIAL PRIMARY KEY,
    app     VARCHAR(255) NOT NULL,
    name    VARCHAR(255) NOT NULL,
    applied TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS django_admin_log (
    id              BIGSERIAL PRIMARY KEY,
    action_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    object_id       TEXT,
    object_repr     VARCHAR(200) NOT NULL,
    action_flag     SMALLINT NOT NULL CHECK (action_flag > 0),
    change_message  TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id         UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE
);

-- ============================================================
-- django-axes (protección brute force)
-- ============================================================

CREATE TABLE IF NOT EXISTS axes_accessattempt (
    id              BIGSERIAL PRIMARY KEY,
    user_agent      VARCHAR(255) NOT NULL,
    ip_address      INET,
    username        VARCHAR(255),
    http_accept     VARCHAR(1025) NOT NULL,
    path_info       VARCHAR(255)  NOT NULL,
    attempt_time    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    get_data        TEXT NOT NULL,
    post_data       TEXT NOT NULL,
    failures_since_start INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS axes_accesslog (
    id           BIGSERIAL PRIMARY KEY,
    user_agent   VARCHAR(255) NOT NULL,
    ip_address   INET,
    username     VARCHAR(255),
    http_accept  VARCHAR(1025) NOT NULL,
    path_info    VARCHAR(255)  NOT NULL,
    attempt_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    logout_time  TIMESTAMPTZ
);

-- ============================================================
-- django-otp / two_factor
-- ============================================================

CREATE TABLE IF NOT EXISTS otp_totp_totpdevice (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    name        VARCHAR(64) NOT NULL,
    confirmed   BOOLEAN NOT NULL DEFAULT TRUE,
    key         VARCHAR(80) NOT NULL,
    step        SMALLINT NOT NULL DEFAULT 30,
    t0          BIGINT NOT NULL DEFAULT 0,
    digits      SMALLINT NOT NULL DEFAULT 6,
    drift       SMALLINT NOT NULL DEFAULT 0,
    last_t      BIGINT NOT NULL DEFAULT -1,
    tolerance   SMALLINT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS otp_static_staticdevice (
    id        BIGSERIAL PRIMARY KEY,
    user_id   UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    name      VARCHAR(64) NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS otp_static_statictoken (
    id        BIGSERIAL PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES otp_static_staticdevice(id) ON DELETE CASCADE,
    token     VARCHAR(16) NOT NULL
);

-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================
