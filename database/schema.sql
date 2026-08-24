CREATE TABLE IF NOT EXISTS electricity_meters (
    meter_id VARCHAR(20) PRIMARY KEY,
    meter_description VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS electricity_readings (
    id BIGSERIAL PRIMARY KEY,
    meter_id VARCHAR(20) NOT NULL,
    period DATE NOT NULL,
    consumption_kwh NUMERIC(14, 2) NOT NULL,
    CONSTRAINT fk_electricity_meter
        FOREIGN KEY (meter_id)
        REFERENCES electricity_meters(meter_id),
    CONSTRAINT uq_meter_period
        UNIQUE (meter_id, period)
);

CREATE TABLE IF NOT EXISTS emission_factors (
    id BIGSERIAL PRIMARY KEY,
    activity VARCHAR(150) NOT NULL UNIQUE,
    scope SMALLINT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    kg_co2e_per_unit NUMERIC(10, 4) NOT NULL,
    source VARCHAR(255) NOT NULL,
    CHECK (scope BETWEEN 1 AND 3), -- GHG scope is typically 1 to 3
    CHECK (kg_co2e_per_unit > 0)
);

CREATE TABLE IF NOT EXISTS fuel_deliveries (
    id BIGSERIAL PRIMARY KEY,
    invoice_no VARCHAR(50) NOT NULL,
    delivery_date DATE NOT NULL,
    fuel_type VARCHAR(50) NOT NULL,
    quantity_litres NUMERIC(14, 2) NOT NULL,
    cost_aud NUMERIC(14, 2) NOT NULL,
    site_area VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id BIGSERIAL PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL,
    incident_date DATE NOT NULL,
    location VARCHAR(100) NOT NULL,
    type_code VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    source_record_hash VARCHAR(64) NOT NULL
);

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS source_row INTEGER,
    ADD COLUMN IF NOT EXISTS source_record_hash VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS uq_incidents_source_record_hash
    ON incidents(source_record_hash);

CREATE TABLE IF NOT EXISTS incident_ai_findings (
    source_record_hash VARCHAR(64) PRIMARY KEY,
    primary_hazard_domain VARCHAR(50) NOT NULL,
    secondary_hazard_domains TEXT[] NOT NULL,
    event_mechanism VARCHAR(80) NOT NULL,
    psychosocial_hazard BOOLEAN NOT NULL,
    psychosocial_types TEXT[] NOT NULL,
    severity_consistency VARCHAR(30) NOT NULL,
    suggested_severity VARCHAR(20) NOT NULL,
    category_evidence_quote TEXT NOT NULL,
    severity_evidence_quote TEXT,
    explanation TEXT NOT NULL,
    response_id VARCHAR(100),
    model VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL,
    attempts SMALLINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_finding_incident
        FOREIGN KEY (source_record_hash)
        REFERENCES incidents(source_record_hash)
        ON DELETE CASCADE,
    CHECK (
        severity_consistency IN (
            'consistent',
            'appears_inconsistent',
            'insufficient_context'
        )
    ),
    CHECK (
        suggested_severity IN (
            'Low',
            'Medium',
            'High',
            'Not assessed'
        )
    ),
    CHECK (attempts > 0)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGSERIAL PRIMARY KEY,
    supplier_name VARCHAR(150) NOT NULL,
    abn VARCHAR(11),
    category VARCHAR(100) NOT NULL,
    fy_spend_aud NUMERIC(14, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    id BIGSERIAL PRIMARY KEY,
    dataset VARCHAR(100) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,
    record_key VARCHAR(100),
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (action IN ('fixed', 'flagged', 'rejected'))
);
