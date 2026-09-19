-- =============================================================================
-- 10_daily_raw_pipeline.sql  — Daily Synthetic Data Ingestion
-- Creates a Python stored procedure + Task scheduled at midnight UTC.
-- Deploy once with: python scripts/deploy_daily_pipeline.py
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- Stored Procedure (Python) — generates daily synthetic batch
-- BATCH_SIZE: number of new customers per run (default 20).
-- Related tables are scaled proportionally.
-- =========================================================================
CREATE OR REPLACE PROCEDURE CUSTOMER_360.RAW.SP_DAILY_SYNTHETIC_DATA(BATCH_SIZE FLOAT)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS $$
def run(session, batch_size: float) -> str:
    n   = max(1, int(batch_size))
    np_ = max(1, int(batch_size * 1.5))   # policies
    nc  = max(1, int(batch_size * 0.6))   # claims
    nl  = max(1, int(batch_size * 0.8))   # loans
    ni  = max(1, int(batch_size * 3.0))   # interactions
    nt  = max(1, int(batch_size * 0.5))   # transcripts

    # 1. RAW_CUSTOMERS --------------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_CUSTOMERS
        WITH cust_offset AS (SELECT COALESCE(MAX(CUSTOMER_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_CUSTOMERS),
        first_names AS (SELECT column1 AS v FROM VALUES
            ('Olivia'),('Noah'),('Emma'),('Liam'),('Ava'),('Ethan'),('Isabella'),('Mason'),
            ('Sophia'),('Logan'),('Mia'),('Lucas'),('Charlotte'),('Aiden'),('Amelia'),('Jackson'),
            ('Grace'),('Henry'),('Chloe'),('Samuel'),('Victoria'),('David'),('Riley'),('Joseph'),
            ('Arjun'),('Divya'),('Rohan'),('Ananya'),('Hiroshi'),('Yuki'),('Zhang'),('Ling'),
            ('Mohammed'),('Aisha'),('Alejandro'),('Valentina'),('Diego'),('Camila')
        ),
        last_names AS (SELECT column1 AS v FROM VALUES
            ('Adams'),('Baker'),('Campbell'),('Dixon'),('Edwards'),('Foster'),('Graham'),('Hayes'),
            ('Ingram'),('Jenkins'),('Knight'),('Lambert'),('Morgan'),('Nash'),('Owen'),('Palmer'),
            ('Quinn'),('Reed'),('Simmons'),('Turner'),('Sharma'),('Nair'),('Iyer'),('Kapoor'),
            ('Nakamura'),('Suzuki'),('Abdullah'),('Rahman'),('Hassan'),('Santos')
        ),
        segs AS (SELECT column1 AS v FROM VALUES ('Basic'),('Basic'),('Standard'),('Standard'),('Standard'),('Premium'),('VIP')),
        locs AS (SELECT column1 AS country, column2 AS st, column3 AS city FROM VALUES
            ('USA','California','Los Angeles'),('USA','New York','New York City'),
            ('USA','Texas','Houston'),('USA','Florida','Miami'),('USA','Illinois','Chicago'),
            ('USA','Washington','Seattle'),('UK','England','London'),
            ('Canada','Ontario','Toronto'),('India','Maharashtra','Mumbai'),
            ('Australia','NSW','Sydney'),('Singapore','SG','Singapore'),('UAE','Dubai','Dubai')
        ),
        emp AS (SELECT column1 AS v FROM VALUES ('Employed'),('Self-Employed'),('Retired'),('Unemployed'),('Part-Time'))
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            fn.v, ln.v,
            LOWER(fn.v || '.' || ln.v || (o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM())) || '@' ||
                CASE MOD(UNIFORM(1,4,RANDOM()),4)
                    WHEN 0 THEN 'gmail.com' WHEN 1 THEN 'outlook.com'
                    WHEN 2 THEN 'yahoo.com' ELSE 'icloud.com' END),
            '+1-' || LPAD(UNIFORM(200,999,RANDOM())::VARCHAR,3,'0') || '-' ||
                LPAD(UNIFORM(1000,9999,RANDOM())::VARCHAR,4,'0'),
            DATEADD('day',-UNIFORM(6570,29200,RANDOM()),CURRENT_DATE()),
            UNIFORM(100,9999,RANDOM())::VARCHAR || ' Main St',
            l.city, l.st, l.country, s.v,
            CASE s.v WHEN 'VIP' THEN UNIFORM(750,850,RANDOM()) WHEN 'Premium' THEN UNIFORM(700,800,RANDOM())
                     WHEN 'Standard' THEN UNIFORM(620,750,RANDOM()) ELSE UNIFORM(480,680,RANDOM()) END,
            CASE s.v WHEN 'VIP' THEN UNIFORM(120000,600000,RANDOM()) WHEN 'Premium' THEN UNIFORM(70000,250000,RANDOM())
                     WHEN 'Standard' THEN UNIFORM(35000,110000,RANDOM()) ELSE UNIFORM(18000,65000,RANDOM()) END::NUMBER(12,2),
            e.v,
            CASE WHEN UNIFORM(1,100,RANDOM()) <= 85 THEN TRUE ELSE FALSE END,
            CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
        FROM first_names fn CROSS JOIN last_names ln CROSS JOIN segs s
        CROSS JOIN locs l CROSS JOIN emp e CROSS JOIN cust_offset o
        ORDER BY RANDOM() LIMIT {n}
    """).collect()

    # 2. RAW_POLICIES ---------------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_POLICIES
        WITH pol_offset AS (SELECT COALESCE(MAX(POLICY_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_POLICIES),
        new_c AS (SELECT CUSTOMER_ID FROM CUSTOMER_360.RAW.RAW_CUSTOMERS ORDER BY CUSTOMER_ID DESC LIMIT {n}),
        pt AS (SELECT column1 AS v FROM VALUES ('Auto'),('Home'),('Life'),('Health'),('Travel'),('Cyber')),
        ps AS (SELECT column1 AS v FROM VALUES ('Active'),('Active'),('Active'),('Renewed'),('Lapsed'),('Cancelled'))
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            c.CUSTOMER_ID, pt.v, ps.v,
            CASE pt.v WHEN 'Auto' THEN UNIFORM(400,3500,RANDOM()) WHEN 'Home' THEN UNIFORM(700,6000,RANDOM())
                      WHEN 'Life' THEN UNIFORM(150,2500,RANDOM()) WHEN 'Health' THEN UNIFORM(250,1800,RANDOM())
                      WHEN 'Cyber' THEN UNIFORM(300,2000,RANDOM()) ELSE UNIFORM(80,900,RANDOM()) END::NUMBER(12,2),
            CASE pt.v WHEN 'Auto' THEN UNIFORM(12000,120000,RANDOM()) WHEN 'Home' THEN UNIFORM(80000,600000,RANDOM())
                      WHEN 'Life' THEN UNIFORM(50000,2000000,RANDOM()) WHEN 'Health' THEN UNIFORM(20000,250000,RANDOM())
                      ELSE UNIFORM(3000,60000,RANDOM()) END::NUMBER(14,2),
            UNIFORM(250,5000,RANDOM())::NUMBER(10,2),
            DATEADD('day',-UNIFORM(0,365,RANDOM()),CURRENT_DATE()),
            DATEADD('day',UNIFORM(30,730,RANDOM()),CURRENT_DATE()),
            DATEADD('day',UNIFORM(30,365,RANDOM()),CURRENT_DATE()),
            UNIFORM(20,100,RANDOM())::NUMBER(5,2),
            CASE WHEN UNIFORM(1,100,RANDOM())<=40 THEN 'Low'
                 WHEN UNIFORM(1,100,RANDOM())<=75 THEN 'Medium' ELSE 'High' END,
            CURRENT_TIMESTAMP()
        FROM new_c c CROSS JOIN pt CROSS JOIN ps CROSS JOIN pol_offset o
        ORDER BY RANDOM() LIMIT {np_}
    """).collect()

    # 3. RAW_CLAIMS -----------------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_CLAIMS
        WITH claim_offset AS (SELECT COALESCE(MAX(CLAIM_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_CLAIMS),
        new_p AS (SELECT POLICY_ID, CUSTOMER_ID FROM CUSTOMER_360.RAW.RAW_POLICIES ORDER BY POLICY_ID DESC LIMIT {np_}),
        ct AS (SELECT column1 AS v FROM VALUES ('Accident'),('Theft'),('Medical'),('Property Damage'),('Fire'),('Flood')),
        cs AS (SELECT column1 AS v FROM VALUES ('Open'),('InReview'),('Approved'),('Denied'),('Settled')),
        cd AS (SELECT column1 AS v FROM VALUES
            ('Vehicle collision requiring bodywork and windshield replacement'),
            ('Water damage from burst pipe, flooring and drywall affected'),
            ('Medical procedure requiring emergency room visit and follow-up care'),
            ('Kitchen fire requiring appliance and cabinet replacement'),
            ('Theft of personal electronics from vehicle while parked'),
            ('Flooding from heavy rainfall, first floor water damage'))
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            p.POLICY_ID, p.CUSTOMER_ID, ct.v, cs.v,
            UNIFORM(500,75000,RANDOM())::NUMBER(12,2),
            CASE WHEN cs.v IN ('Approved','Settled') THEN UNIFORM(400,70000,RANDOM())::NUMBER(12,2) ELSE NULL END,
            DATEADD('day',-UNIFORM(0,30,RANDOM()),CURRENT_DATE()),
            CASE WHEN cs.v IN ('Approved','Denied','Settled')
                 THEN DATEADD('day',-UNIFORM(0,20,RANDOM()),CURRENT_DATE()) ELSE NULL END,
            cd.v, CURRENT_TIMESTAMP()
        FROM new_p p CROSS JOIN ct CROSS JOIN cs CROSS JOIN cd CROSS JOIN claim_offset o
        ORDER BY RANDOM() LIMIT {nc}
    """).collect()

    # 4. RAW_LOANS ------------------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_LOANS
        WITH loan_offset AS (SELECT COALESCE(MAX(LOAN_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_LOANS),
        new_c AS (SELECT CUSTOMER_ID FROM CUSTOMER_360.RAW.RAW_CUSTOMERS ORDER BY CUSTOMER_ID DESC LIMIT {n}),
        lt AS (SELECT column1 AS v FROM VALUES ('Mortgage'),('Auto'),('Personal'),('Business'),('Student')),
        ls AS (SELECT column1 AS v FROM VALUES ('Active'),('Active'),('Active'),('PaidOff'),('Default'),('Delinquent'))
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            c.CUSTOMER_ID, lt.v, ls.v,
            CASE lt.v WHEN 'Mortgage' THEN UNIFORM(80000,900000,RANDOM()) WHEN 'Auto' THEN UNIFORM(8000,75000,RANDOM())
                      WHEN 'Personal' THEN UNIFORM(3000,60000,RANDOM()) WHEN 'Business' THEN UNIFORM(20000,600000,RANDOM())
                      ELSE UNIFORM(5000,80000,RANDOM()) END::NUMBER(14,2),
            UNIFORM(150,1400,RANDOM())/100.0,
            CASE lt.v WHEN 'Mortgage' THEN UNIFORM(600,5000,RANDOM()) WHEN 'Auto' THEN UNIFORM(150,1100,RANDOM())
                      WHEN 'Personal' THEN UNIFORM(80,900,RANDOM()) ELSE UNIFORM(100,800,RANDOM()) END::NUMBER(10,2),
            CASE ls.v WHEN 'PaidOff' THEN 0 ELSE UNIFORM(500,800000,RANDOM()) END::NUMBER(14,2),
            DATEADD('day',-UNIFORM(0,365,RANDOM()),CURRENT_DATE()),
            DATEADD('day',UNIFORM(365,10950,RANDOM()),CURRENT_DATE()),
            CASE ls.v WHEN 'Delinquent' THEN UNIFORM(30,150,RANDOM())
                      WHEN 'Default' THEN UNIFORM(150,730,RANDOM()) ELSE 0 END,
            CURRENT_TIMESTAMP()
        FROM new_c c CROSS JOIN lt CROSS JOIN ls CROSS JOIN loan_offset o
        ORDER BY RANDOM() LIMIT {nl}
    """).collect()

    # 5. RAW_INTERACTIONS -----------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_INTERACTIONS
        WITH inter_offset AS (SELECT COALESCE(MAX(INTERACTION_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_INTERACTIONS),
        new_c AS (SELECT CUSTOMER_ID FROM CUSTOMER_360.RAW.RAW_CUSTOMERS ORDER BY CUSTOMER_ID DESC LIMIT {n}),
        ch AS (SELECT column1 AS v FROM VALUES ('Email'),('Phone'),('Chat'),('Web'),('Mobile')),
        tp AS (SELECT column1 AS v FROM VALUES ('Inquiry'),('Complaint'),('ServiceRequest'),('Payment'),('ClaimUpdate')),
        sub AS (SELECT column1 AS v FROM VALUES
            ('Policy renewal inquiry'),('Premium payment question'),('Claim status update'),
            ('Coverage change request'),('Billing discrepancy'),('New policy quote request'),
            ('Cancellation request'),('Loan payment schedule inquiry')),
        note AS (SELECT column1 AS v FROM VALUES
            ('Customer called to ask about upcoming policy renewal options and available discounts.'),
            ('Escalated complaint regarding delayed claim. Customer expressed frustration with timeline.'),
            ('Routine inquiry about adding a driver to auto policy. Provided quote and sent documents.'),
            ('Customer requested coverage increase on home policy due to recent renovations.'),
            ('Payment issue resolved: autopay failed due to expired card. Updated payment method.'),
            ('Customer inquired about life insurance options for family. Scheduled callback.'),
            ('Follow-up on denied claim. Customer provided additional documentation for review.'),
            ('Customer disputed premium increase. Explained underwriting factors. Retention offer made.')),
        res AS (SELECT column1 AS v FROM VALUES ('Resolved'),('Pending'),('Escalated'))
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            c.CUSTOMER_ID, ch.v, tp.v, sub.v, note.v, res.v,
            'AGT-' || LPAD(UNIFORM(100,999,RANDOM())::VARCHAR,3,'0'),
            DATEADD('hour',-UNIFORM(0,24,RANDOM()),CURRENT_TIMESTAMP()),
            CASE ch.v WHEN 'Phone' THEN UNIFORM(90,2400,RANDOM())
                      WHEN 'Chat' THEN UNIFORM(180,3000,RANDOM()) ELSE NULL END,
            CURRENT_TIMESTAMP()
        FROM new_c c CROSS JOIN ch CROSS JOIN tp CROSS JOIN sub CROSS JOIN note CROSS JOIN res CROSS JOIN inter_offset o
        ORDER BY RANDOM() LIMIT {ni}
    """).collect()

    # 6. RAW_CALL_TRANSCRIPTS -------------------------------------------
    session.sql(f"""
        INSERT INTO CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS
        WITH tran_offset AS (SELECT COALESCE(MAX(TRANSCRIPT_ID),0) AS mx FROM CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS),
        new_c AS (SELECT CUSTOMER_ID FROM CUSTOMER_360.RAW.RAW_CUSTOMERS ORDER BY CUSTOMER_ID DESC LIMIT {n}),
        reasons AS (SELECT column1 AS r FROM VALUES
            ('Policy Renewal'),('Claim Status'),('Premium Dispute'),('Payment Issue'),('Complaint')),
        txts AS (SELECT column1 AS r, column2 AS t FROM VALUES
            ('Policy Renewal', 'Agent: Thank you for calling SecureLife. How can I help?
Customer: My renewal premium increased 15 percent.
Agent: I can apply a multi-policy bundle discount of 8 percent. Would that help?
Customer: Yes, please apply it.
Agent: Done. Updated renewal notice arrives in 5 business days.'),
            ('Claim Status', 'Agent: SecureLife claims. How may I help?
Customer: I filed a claim three weeks ago and have not heard back.
Agent: I see your claim. There was a delay requesting additional photos. I am escalating to priority. The adjuster will call within 24 hours.
Customer: Thank you.
Agent: I apologize for the delay.'),
            ('Premium Dispute', 'Agent: SecureLife. How can I help?
Customer: My health premium went up 25 percent. I have been with you 8 years.
Agent: I can apply a 5 percent loyalty discount and move you to Silver tier, reducing your premium below your previous rate.
Customer: Lets do that.
Agent: Done. Confirmation arrives in 3 business days.'),
            ('Payment Issue', 'Agent: SecureLife. How can I assist?
Customer: My payment was charged twice and caused an overdraft.
Agent: I am processing an immediate refund and reimbursing your 35 dollar overdraft fee. Please email your bank statement to billing@securelife.com.
Customer: Thank you.
Agent: Of course.'),
            ('Complaint', 'Agent: SecureLife. How may I help?
Customer: My claim was denied but the pipe was clearly inside the wall.
Agent: I am escalating this to our senior claims review team. A second adjuster will review the damage. You will hear from a claims manager within 48 hours.
Customer: I expect a fair outcome.
Agent: Absolutely. I will follow up next week.')
        )
        SELECT
            o.mx + ROW_NUMBER() OVER (ORDER BY RANDOM()),
            c.CUSTOMER_ID, NULL,
            DATEADD('hour',-UNIFORM(0,24,RANDOM()),CURRENT_TIMESTAMP()),
            UNIFORM(120,1200,RANDOM()),
            'AGT-' || LPAD(UNIFORM(100,999,RANDOM())::VARCHAR,3,'0'),
            CASE MOD(UNIFORM(1,5,RANDOM()),5)
                WHEN 0 THEN 'Sarah Mitchell' WHEN 1 THEN 'Michael Torres'
                WHEN 2 THEN 'Jessica Chen'   WHEN 3 THEN 'David Patel'
                ELSE 'Amanda Rodriguez'
            END,
            x.t, x.r, CURRENT_TIMESTAMP()
        FROM new_c c CROSS JOIN reasons r CROSS JOIN txts x CROSS JOIN tran_offset o
        WHERE r.r = x.r
        ORDER BY RANDOM() LIMIT {nt}
    """).collect()

    return (
        f"Daily batch complete | "
        f"customers={n} policies={np_} claims={nc} "
        f"loans={nl} interactions={ni} transcripts={nt} | "
        f"run_at={__import__('datetime').datetime.utcnow().isoformat()}"
    )
$$;


-- =========================================================================
-- Task: runs the procedure every day at midnight UTC
-- Adjust BATCH_SIZE (default 20) to control daily data volume:
--   20  → ~730 customers/year
--   50  → ~1,825 customers/year
--  100  → ~3,650 customers/year
-- =========================================================================
CREATE OR REPLACE TASK CUSTOMER_360.RAW.TASK_DAILY_RAW_INGEST
    WAREHOUSE = COMPUTE_WH
    SCHEDULE  = 'USING CRON 0 0 * * * UTC'
    COMMENT   = 'Daily synthetic data ingestion for Customer 360 pipeline'
AS
    CALL CUSTOMER_360.RAW.SP_DAILY_SYNTHETIC_DATA(20);


-- Resume the task (tasks start SUSPENDED by default)
ALTER TASK CUSTOMER_360.RAW.TASK_DAILY_RAW_INGEST RESUME;


-- Verify
SHOW TASKS IN SCHEMA CUSTOMER_360.RAW;
