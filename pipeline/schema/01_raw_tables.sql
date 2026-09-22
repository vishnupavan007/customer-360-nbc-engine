-- =============================================================================
-- 01_raw_tables.sql - RAW Schema Table Definitions
-- All source tables land here with minimal transformation
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA RAW;

-- Core customer/policyholder profiles
CREATE OR REPLACE TABLE RAW.RAW_CUSTOMERS (
    CUSTOMER_ID       NUMBER(38,0)    NOT NULL,
    FIRST_NAME        VARCHAR(100),
    LAST_NAME         VARCHAR(100),
    EMAIL             VARCHAR(255),
    PHONE             VARCHAR(50),
    DOB               DATE,
    ADDRESS           VARCHAR(500),
    CITY              VARCHAR(100),
    STATE             VARCHAR(100),
    COUNTRY           VARCHAR(100),
    CUSTOMER_SEGMENT  VARCHAR(20),      -- Basic, Standard, Premium, VIP
    CREDIT_SCORE      NUMBER(3,0),
    ANNUAL_INCOME     NUMBER(12,2),
    EMPLOYMENT_STATUS VARCHAR(30),      -- Employed, Self-Employed, Retired, Unemployed
    IS_ACTIVE         BOOLEAN DEFAULT TRUE,
    CREATED_AT        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_CUSTOMERS PRIMARY KEY (CUSTOMER_ID)
);

-- Insurance policies
CREATE OR REPLACE TABLE RAW.RAW_POLICIES (
    POLICY_ID          NUMBER(38,0)   NOT NULL,
    CUSTOMER_ID        NUMBER(38,0)   NOT NULL,
    POLICY_TYPE        VARCHAR(30),     -- Auto, Home, Life, Health, Travel
    POLICY_STATUS      VARCHAR(20),     -- Active, Lapsed, Cancelled, Renewed
    PREMIUM_AMOUNT     NUMBER(12,2),
    COVERAGE_AMOUNT    NUMBER(14,2),
    DEDUCTIBLE_AMOUNT  NUMBER(10,2),
    START_DATE         DATE,
    END_DATE           DATE,
    RENEWAL_DATE       DATE,
    UNDERWRITING_SCORE NUMBER(5,2),
    RISK_CATEGORY      VARCHAR(10),     -- Low, Medium, High
    CREATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_POLICIES PRIMARY KEY (POLICY_ID)
);

-- Insurance claims
CREATE OR REPLACE TABLE RAW.RAW_CLAIMS (
    CLAIM_ID           NUMBER(38,0)   NOT NULL,
    POLICY_ID          NUMBER(38,0)   NOT NULL,
    CUSTOMER_ID        NUMBER(38,0)   NOT NULL,
    CLAIM_TYPE         VARCHAR(50),     -- Accident, Theft, Natural Disaster, Medical, Property Damage
    CLAIM_STATUS       VARCHAR(20),     -- Open, InReview, Approved, Denied, Settled
    CLAIM_AMOUNT       NUMBER(12,2),
    SETTLEMENT_AMOUNT  NUMBER(12,2),
    FILED_DATE         DATE,
    RESOLVED_DATE      DATE,
    DESCRIPTION        VARCHAR(2000),
    CREATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_CLAIMS PRIMARY KEY (CLAIM_ID)
);

-- Lending products
CREATE OR REPLACE TABLE RAW.RAW_LOANS (
    LOAN_ID             NUMBER(38,0)   NOT NULL,
    CUSTOMER_ID         NUMBER(38,0)   NOT NULL,
    LOAN_TYPE           VARCHAR(30),     -- Mortgage, Auto, Personal, Business
    LOAN_STATUS         VARCHAR(20),     -- Active, PaidOff, Default, Delinquent
    PRINCIPAL_AMOUNT    NUMBER(14,2),
    INTEREST_RATE       NUMBER(5,3),
    MONTHLY_PAYMENT     NUMBER(10,2),
    OUTSTANDING_BALANCE NUMBER(14,2),
    ORIGINATION_DATE    DATE,
    MATURITY_DATE       DATE,
    DAYS_PAST_DUE       NUMBER(5,0) DEFAULT 0,
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_LOANS PRIMARY KEY (LOAN_ID)
);

-- Structured interaction touchpoints
CREATE OR REPLACE TABLE RAW.RAW_INTERACTIONS (
    INTERACTION_ID     NUMBER(38,0)   NOT NULL,
    CUSTOMER_ID        NUMBER(38,0)   NOT NULL,
    CHANNEL            VARCHAR(20),     -- Email, Phone, Chat, Branch, Web, Mobile
    INTERACTION_TYPE   VARCHAR(30),     -- Inquiry, Complaint, ServiceRequest, PolicyChange, ClaimUpdate, Payment
    SUBJECT            VARCHAR(500),
    NOTES              VARCHAR(4000),
    RESOLUTION_STATUS  VARCHAR(20),     -- Resolved, Pending, Escalated
    AGENT_ID           VARCHAR(50),
    INTERACTION_DATE   TIMESTAMP_NTZ,
    DURATION_SECONDS   NUMBER(6,0),
    CREATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_INTERACTIONS PRIMARY KEY (INTERACTION_ID)
);

-- Unstructured call transcripts
CREATE OR REPLACE TABLE RAW.RAW_CALL_TRANSCRIPTS (
    TRANSCRIPT_ID      NUMBER(38,0)   NOT NULL,
    CUSTOMER_ID        NUMBER(38,0)   NOT NULL,
    INTERACTION_ID     NUMBER(38,0),
    CALL_DATE          TIMESTAMP_NTZ,
    DURATION_SECONDS   NUMBER(6,0),
    AGENT_ID           VARCHAR(50),
    AGENT_NAME         VARCHAR(100),
    TRANSCRIPT_TEXT    VARCHAR(16777216),  -- Full call transcript
    CALL_REASON        VARCHAR(100),
    CREATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_CALL_TRANSCRIPTS PRIMARY KEY (TRANSCRIPT_ID)
);

-- Insurance document content (claim forms, policy summaries)
CREATE OR REPLACE TABLE RAW.RAW_DOCUMENTS (
    DOCUMENT_ID       NUMBER(38,0)    NOT NULL,
    CUSTOMER_ID       NUMBER(38,0),
    DOCUMENT_TYPE     VARCHAR(50),       -- Claim Form, Policy Summary
    FILE_NAME         VARCHAR(500),
    DOCUMENT_TEXT     VARCHAR(16777216),  -- Full document content
    FILE_SIZE_BYTES   NUMBER,
    CREATED_AT        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_RAW_DOCUMENTS PRIMARY KEY (DOCUMENT_ID)
);
