-- =============================================================================
-- 02b_additional_10k_data.sql  — Additional 10k synthetic records
-- Adds ~10,450 rows across all 6 RAW tables with richer edge-case scenarios.
-- Run AFTER 02_synthetic_data.sql.  IDs start after current table maxima.
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- 1. RAW_CUSTOMERS  +1,500  (total → 2,000)
--    New scenarios: more edge cases — inactive VIPs, young customers,
--    high-income Basic segment, retirees with premium policies
-- =========================================================================
INSERT INTO RAW.RAW_CUSTOMERS
WITH cust_offset AS (
    SELECT COALESCE(MAX(CUSTOMER_ID), 0) AS max_id FROM RAW.RAW_CUSTOMERS
),
first_names AS (
    SELECT column1 AS name FROM VALUES
    ('Olivia'),('Noah'),('Emma'),('Liam'),('Ava'),('Ethan'),('Isabella'),('Mason'),
    ('Sophia'),('Logan'),('Mia'),('Lucas'),('Charlotte'),('Aiden'),('Amelia'),('Jackson'),
    ('Harper'),('Sebastian'),('Evelyn'),('Mateo'),('Abigail'),('Jack'),('Emily'),('Owen'),
    ('Elizabeth'),('Elijah'),('Mila'),('James'),('Ella'),('Alexander'),('Aria'),('Benjamin'),
    ('Grace'),('Henry'),('Chloe'),('Samuel'),('Victoria'),('David'),('Riley'),('Joseph'),
    ('Arjun'),('Divya'),('Rohan'),('Ananya'),('Vikram'),('Neha'),('Suresh'),('Lakshmi'),
    ('Hiroshi'),('Yuki'),('Takashi'),('Aiko'),('Zhang'),('Ling'),('Hui'),('Fang'),
    ('Mohammed'),('Aisha'),('Ibrahim'),('Zara'),('Hassan'),('Layla'),('Tariq'),('Nadia'),
    ('Alejandro'),('Valentina'),('Diego'),('Camila'),('Luis'),('Sofia'),('Miguel'),('Ana')
),
last_names AS (
    SELECT column1 AS name FROM VALUES
    ('Adams'),('Baker'),('Campbell'),('Dixon'),('Edwards'),('Foster'),('Graham'),('Hayes'),
    ('Ingram'),('Jenkins'),('Knight'),('Lambert'),('Morgan'),('Nash'),('Owen'),('Palmer'),
    ('Quinn'),('Reed'),('Simmons'),('Turner'),('Underwood'),('Vaughan'),('Walsh'),('Xavier'),
    ('Young'),('Zhang'),('Sharma'),('Nair'),('Iyer'),('Kapoor'),('Mehta'),('Gupta'),
    ('Nakamura'),('Suzuki'),('Yamamoto'),('Watanabe'),('Ito'),('Kobayashi'),('Kato'),('Sato'),
    ('Abdullah'),('Rahman'),('Hassan'),('Ahmed'),('Khalid'),('Mahmoud'),('Hussain'),('Qureshi')
),
segments AS (
    SELECT column1 AS seg, column2 AS weight FROM VALUES
    ('Basic', 25), ('Standard', 35), ('Premium', 25), ('VIP', 15)
),
countries AS (
    SELECT column1 AS country, column2 AS state_name, column3 AS city FROM VALUES
    ('USA','California','Los Angeles'),('USA','California','San Francisco'),('USA','California','San Diego'),
    ('USA','New York','New York City'),('USA','New York','Buffalo'),
    ('USA','Texas','Houston'),('USA','Texas','Dallas'),('USA','Texas','Austin'),
    ('USA','Florida','Miami'),('USA','Florida','Orlando'),('USA','Florida','Tampa'),
    ('USA','Illinois','Chicago'),('USA','Pennsylvania','Philadelphia'),('USA','Ohio','Columbus'),
    ('USA','Massachusetts','Boston'),('USA','Washington','Seattle'),('USA','Arizona','Phoenix'),
    ('USA','Colorado','Denver'),('USA','Georgia','Atlanta'),('USA','Nevada','Las Vegas'),
    ('USA','Michigan','Detroit'),('USA','North Carolina','Charlotte'),('USA','Virginia','Arlington'),
    ('UK','England','London'),('UK','England','Manchester'),('UK','England','Birmingham'),
    ('UK','England','Leeds'),('UK','Scotland','Edinburgh'),('UK','Wales','Cardiff'),
    ('Canada','Ontario','Toronto'),('Canada','British Columbia','Vancouver'),('Canada','Quebec','Montreal'),
    ('India','Maharashtra','Mumbai'),('India','Karnataka','Bangalore'),('India','Delhi','New Delhi'),
    ('India','Tamil Nadu','Chennai'),('India','Telangana','Hyderabad'),
    ('Singapore','SG','Singapore'),
    ('Australia','NSW','Sydney'),('Australia','VIC','Melbourne'),('Australia','QLD','Brisbane'),
    ('Germany','Bavaria','Munich'),('Germany','Berlin','Berlin'),
    ('UAE','Dubai','Dubai'),('UAE','Abu Dhabi','Abu Dhabi')
),
emp_statuses AS (
    SELECT column1 AS status FROM VALUES
    ('Employed'),('Self-Employed'),('Retired'),('Unemployed'),('Part-Time'),('Student')
),
base AS (
    SELECT
        o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS CUSTOMER_ID,
        fn.name AS FIRST_NAME,
        ln.name AS LAST_NAME,
        c.country AS COUNTRY,
        c.state_name AS STATE,
        c.city AS CITY,
        s.seg AS CUSTOMER_SEGMENT,
        e.status AS EMPLOYMENT_STATUS
    FROM first_names fn
    CROSS JOIN last_names ln
    CROSS JOIN segments s
    CROSS JOIN countries c
    CROSS JOIN emp_statuses e
    CROSS JOIN cust_offset o
    ORDER BY RANDOM()
    LIMIT 1500
)
SELECT
    b.CUSTOMER_ID,
    b.FIRST_NAME,
    b.LAST_NAME,
    LOWER(b.FIRST_NAME || '.' || b.LAST_NAME || b.CUSTOMER_ID || '@' ||
        CASE MOD(b.CUSTOMER_ID, 5)
            WHEN 0 THEN 'gmail.com'
            WHEN 1 THEN 'outlook.com'
            WHEN 2 THEN 'yahoo.com'
            WHEN 3 THEN 'icloud.com'
            ELSE 'company.com'
        END) AS EMAIL,
    '+1-' || LPAD(UNIFORM(200, 999, RANDOM())::VARCHAR, 3, '0') || '-' ||
        LPAD(UNIFORM(1000, 9999, RANDOM())::VARCHAR, 4, '0') AS PHONE,
    DATEADD('day', -UNIFORM(6570, 29200, RANDOM()), CURRENT_DATE()) AS DOB,
    UNIFORM(100, 9999, RANDOM())::VARCHAR || ' ' ||
        CASE MOD(b.CUSTOMER_ID, 6)
            WHEN 0 THEN 'Main St' WHEN 1 THEN 'Oak Ave' WHEN 2 THEN 'Park Rd'
            WHEN 3 THEN 'Elm Blvd' WHEN 4 THEN 'Maple Dr' ELSE 'Cedar Ln'
        END AS ADDRESS,
    b.CITY, b.STATE, b.COUNTRY,
    b.CUSTOMER_SEGMENT,
    -- More realistic: some VIP with lower scores (recently downgraded), some Basic with high scores
    CASE
        WHEN b.CUSTOMER_SEGMENT = 'VIP'      AND UNIFORM(1,10,RANDOM()) <= 2 THEN UNIFORM(600, 700, RANDOM())  -- at-risk VIP
        WHEN b.CUSTOMER_SEGMENT = 'VIP'      THEN UNIFORM(750, 850, RANDOM())
        WHEN b.CUSTOMER_SEGMENT = 'Premium'  AND UNIFORM(1,10,RANDOM()) <= 2 THEN UNIFORM(580, 660, RANDOM())  -- slipping Premium
        WHEN b.CUSTOMER_SEGMENT = 'Premium'  THEN UNIFORM(700, 800, RANDOM())
        WHEN b.CUSTOMER_SEGMENT = 'Standard' THEN UNIFORM(620, 750, RANDOM())
        WHEN b.CUSTOMER_SEGMENT = 'Basic'    AND UNIFORM(1,10,RANDOM()) <= 1 THEN UNIFORM(720, 780, RANDOM())  -- high-score Basic
        ELSE UNIFORM(480, 680, RANDOM())
    END AS CREDIT_SCORE,
    CASE b.CUSTOMER_SEGMENT
        WHEN 'VIP'      THEN UNIFORM(120000, 600000, RANDOM())
        WHEN 'Premium'  THEN UNIFORM(70000, 250000, RANDOM())
        WHEN 'Standard' THEN UNIFORM(35000, 110000, RANDOM())
        ELSE                 UNIFORM(18000, 65000, RANDOM())
    END::NUMBER(12,2) AS ANNUAL_INCOME,
    b.EMPLOYMENT_STATUS,
    CASE
        WHEN b.CUSTOMER_SEGMENT = 'VIP' THEN
            CASE WHEN UNIFORM(1,100,RANDOM()) <= 90 THEN TRUE ELSE FALSE END
        ELSE
            CASE WHEN UNIFORM(1,100,RANDOM()) <= 82 THEN TRUE ELSE FALSE END
    END AS IS_ACTIVE,
    DATEADD('day', -UNIFORM(30, 1825, RANDOM()), CURRENT_DATE()) AS CREATED_AT,
    DATEADD('day', -UNIFORM(0, 60, RANDOM()), CURRENT_DATE()) AS UPDATED_AT
FROM base b;


-- =========================================================================
-- 2. RAW_POLICIES  +2,500  (total → ~3,300)
--    Wider premium ranges, more Lapsed/Cancelled for churn scenarios
-- =========================================================================
INSERT INTO RAW.RAW_POLICIES
WITH pol_offset AS (
    SELECT COALESCE(MAX(POLICY_ID), 0) AS max_id FROM RAW.RAW_POLICIES
),
new_customers AS (
    SELECT CUSTOMER_ID FROM RAW.RAW_CUSTOMERS WHERE CUSTOMER_ID > (
        SELECT COALESCE(MAX(CUSTOMER_ID), 0) - 1500 FROM RAW.RAW_CUSTOMERS
    )
),
policy_types AS (
    SELECT column1 AS pt FROM VALUES ('Auto'),('Home'),('Life'),('Health'),('Travel'),('Cyber'),('Umbrella')
),
policy_statuses AS (
    SELECT column1 AS ps, column2 AS weight FROM VALUES
    ('Active', 50), ('Renewed', 12), ('Lapsed', 22), ('Cancelled', 16)
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS POLICY_ID,
    c.CUSTOMER_ID,
    pt.pt AS POLICY_TYPE,
    ps.ps AS POLICY_STATUS,
    CASE pt.pt
        WHEN 'Auto'     THEN UNIFORM(400, 3500, RANDOM())
        WHEN 'Home'     THEN UNIFORM(700, 6000, RANDOM())
        WHEN 'Life'     THEN UNIFORM(150, 2500, RANDOM())
        WHEN 'Health'   THEN UNIFORM(250, 1800, RANDOM())
        WHEN 'Cyber'    THEN UNIFORM(300, 2000, RANDOM())
        WHEN 'Umbrella' THEN UNIFORM(200, 1200, RANDOM())
        ELSE UNIFORM(80, 900, RANDOM())
    END::NUMBER(12,2) AS PREMIUM_AMOUNT,
    CASE pt.pt
        WHEN 'Auto'     THEN UNIFORM(12000, 120000, RANDOM())
        WHEN 'Home'     THEN UNIFORM(80000, 600000, RANDOM())
        WHEN 'Life'     THEN UNIFORM(50000, 2000000, RANDOM())
        WHEN 'Health'   THEN UNIFORM(20000, 250000, RANDOM())
        WHEN 'Cyber'    THEN UNIFORM(100000, 5000000, RANDOM())
        WHEN 'Umbrella' THEN UNIFORM(500000, 2000000, RANDOM())
        ELSE UNIFORM(3000, 60000, RANDOM())
    END::NUMBER(14,2) AS COVERAGE_AMOUNT,
    UNIFORM(250, 5000, RANDOM())::NUMBER(10,2) AS DEDUCTIBLE_AMOUNT,
    DATEADD('day', -UNIFORM(30, 1095, RANDOM()), CURRENT_DATE()) AS START_DATE,
    DATEADD('day', UNIFORM(30, 730, RANDOM()), CURRENT_DATE()) AS END_DATE,
    DATEADD('day', UNIFORM(30, 365, RANDOM()), CURRENT_DATE()) AS RENEWAL_DATE,
    UNIFORM(20, 100, RANDOM())::NUMBER(5,2) AS UNDERWRITING_SCORE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM()) <= 40 THEN 'Low'
        WHEN UNIFORM(1, 100, RANDOM()) <= 75 THEN 'Medium'
        ELSE 'High'
    END AS RISK_CATEGORY,
    DATEADD('day', -UNIFORM(30, 1095, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM new_customers c
CROSS JOIN policy_types pt
CROSS JOIN policy_statuses ps
CROSS JOIN pol_offset o
ORDER BY RANDOM()
LIMIT 2500;


-- =========================================================================
-- 3. RAW_CLAIMS  +1,000  (total → ~1,300)
--    Added new claim types, denied claims (important for churn risk)
-- =========================================================================
INSERT INTO RAW.RAW_CLAIMS
WITH claim_offset AS (
    SELECT COALESCE(MAX(CLAIM_ID), 0) AS max_id FROM RAW.RAW_CLAIMS
),
new_policies AS (
    SELECT POLICY_ID, CUSTOMER_ID FROM RAW.RAW_POLICIES WHERE POLICY_ID > (
        SELECT COALESCE(MAX(POLICY_ID), 0) - 2500 FROM RAW.RAW_POLICIES
    )
),
claim_types AS (
    SELECT column1 AS ct FROM VALUES
    ('Accident'),('Theft'),('Natural Disaster'),('Medical'),('Property Damage'),
    ('Liability'),('Cyber Incident'),('Flood'),('Fire'),('Disability')
),
claim_statuses AS (
    SELECT column1 AS cs FROM VALUES ('Open'),('InReview'),('Approved'),('Denied'),('Settled')
),
claim_descriptions AS (
    SELECT column1 AS descr FROM VALUES
    ('Vehicle collision at intersection requiring bodywork and windshield replacement'),
    ('Hail damage to roof and siding, multiple areas affected'),
    ('Water damage from burst pipe in basement, flooring and drywall affected'),
    ('Theft of personal electronics from vehicle while parked'),
    ('Slip and fall injury requiring emergency room visit and follow-up care'),
    ('Kitchen fire damage requiring appliance and cabinet replacement'),
    ('Tree fell on fence and shed during storm'),
    ('Rear-end collision on highway, minor whiplash reported'),
    ('Broken window from attempted break-in, security system triggered'),
    ('Flooding from heavy rainfall, first floor water damage'),
    ('Medical procedure complications requiring extended hospital stay'),
    ('Vandalism to parked vehicle, paint and mirror damage'),
    ('Lightning strike damaged electrical system and appliances'),
    ('Dog bite incident at property, liability claim filed'),
    ('Roof leak discovered after prolonged rain, ceiling damage'),
    ('Ransomware attack encrypted business files, recovery required'),
    ('Identity theft resulted in fraudulent credit applications'),
    ('Disability preventing return to work for 6 months or longer'),
    ('Wildfire evacuation caused structural and content losses'),
    ('Burst pipe during freeze caused extensive kitchen damage')
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS CLAIM_ID,
    p.POLICY_ID,
    p.CUSTOMER_ID,
    ct.ct AS CLAIM_TYPE,
    cs.cs AS CLAIM_STATUS,
    UNIFORM(500, 75000, RANDOM())::NUMBER(12,2) AS CLAIM_AMOUNT,
    CASE WHEN cs.cs IN ('Approved', 'Settled')
        THEN UNIFORM(400, 70000, RANDOM())::NUMBER(12,2)
        ELSE NULL
    END AS SETTLEMENT_AMOUNT,
    DATEADD('day', -UNIFORM(1, 730, RANDOM()), CURRENT_DATE()) AS FILED_DATE,
    CASE WHEN cs.cs IN ('Approved', 'Denied', 'Settled')
        THEN DATEADD('day', -UNIFORM(0, 90, RANDOM()), CURRENT_DATE())
        ELSE NULL
    END AS RESOLVED_DATE,
    cd.descr AS DESCRIPTION,
    DATEADD('day', -UNIFORM(1, 730, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM new_policies p
CROSS JOIN claim_types ct
CROSS JOIN claim_statuses cs
CROSS JOIN claim_descriptions cd
CROSS JOIN claim_offset o
ORDER BY RANDOM()
LIMIT 1000;


-- =========================================================================
-- 4. RAW_LOANS  +1,200  (total → ~1,600)
--    More Delinquent/Default for churn and NBA signal
-- =========================================================================
INSERT INTO RAW.RAW_LOANS
WITH loan_offset AS (
    SELECT COALESCE(MAX(LOAN_ID), 0) AS max_id FROM RAW.RAW_LOANS
),
new_customers AS (
    SELECT CUSTOMER_ID FROM RAW.RAW_CUSTOMERS WHERE CUSTOMER_ID > (
        SELECT COALESCE(MAX(CUSTOMER_ID), 0) - 1500 FROM RAW.RAW_CUSTOMERS
    )
),
loan_types AS (
    SELECT column1 AS lt FROM VALUES ('Mortgage'),('Auto'),('Personal'),('Business'),('Student')
),
loan_statuses AS (
    SELECT column1 AS ls, column2 AS wt FROM VALUES
    ('Active', 50), ('PaidOff', 20), ('Default', 15), ('Delinquent', 15)
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS LOAN_ID,
    c.CUSTOMER_ID,
    lt.lt AS LOAN_TYPE,
    ls.ls AS LOAN_STATUS,
    CASE lt.lt
        WHEN 'Mortgage' THEN UNIFORM(80000, 900000, RANDOM())
        WHEN 'Auto'     THEN UNIFORM(8000, 75000, RANDOM())
        WHEN 'Personal' THEN UNIFORM(3000, 60000, RANDOM())
        WHEN 'Business' THEN UNIFORM(20000, 600000, RANDOM())
        ELSE                 UNIFORM(5000, 80000, RANDOM())
    END::NUMBER(14,2) AS PRINCIPAL_AMOUNT,
    UNIFORM(150, 1400, RANDOM()) / 100.0 AS INTEREST_RATE,
    CASE lt.lt
        WHEN 'Mortgage' THEN UNIFORM(600, 5000, RANDOM())
        WHEN 'Auto'     THEN UNIFORM(150, 1100, RANDOM())
        WHEN 'Personal' THEN UNIFORM(80, 900, RANDOM())
        WHEN 'Business' THEN UNIFORM(400, 4000, RANDOM())
        ELSE                 UNIFORM(100, 800, RANDOM())
    END::NUMBER(10,2) AS MONTHLY_PAYMENT,
    CASE ls.ls
        WHEN 'PaidOff' THEN 0
        ELSE UNIFORM(500, 800000, RANDOM())
    END::NUMBER(14,2) AS OUTSTANDING_BALANCE,
    DATEADD('day', -UNIFORM(60, 2555, RANDOM()), CURRENT_DATE()) AS ORIGINATION_DATE,
    DATEADD('day', UNIFORM(365, 14600, RANDOM()), CURRENT_DATE()) AS MATURITY_DATE,
    CASE ls.ls
        WHEN 'Delinquent' THEN UNIFORM(30, 150, RANDOM())
        WHEN 'Default'    THEN UNIFORM(150, 730, RANDOM())
        ELSE 0
    END AS DAYS_PAST_DUE,
    DATEADD('day', -UNIFORM(60, 2555, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM new_customers c
CROSS JOIN loan_types lt
CROSS JOIN loan_statuses ls
CROSS JOIN loan_offset o
ORDER BY RANDOM()
LIMIT 1200;


-- =========================================================================
-- 5. RAW_INTERACTIONS  +3,500  (total → ~4,700)
--    More complaint/escalation patterns, new channels (WhatsApp, Video)
-- =========================================================================
INSERT INTO RAW.RAW_INTERACTIONS
WITH inter_offset AS (
    SELECT COALESCE(MAX(INTERACTION_ID), 0) AS max_id FROM RAW.RAW_INTERACTIONS
),
new_customers AS (
    SELECT CUSTOMER_ID FROM RAW.RAW_CUSTOMERS WHERE CUSTOMER_ID > (
        SELECT COALESCE(MAX(CUSTOMER_ID), 0) - 1500 FROM RAW.RAW_CUSTOMERS
    )
),
channels AS (
    SELECT column1 AS ch FROM VALUES
    ('Email'),('Phone'),('Chat'),('Branch'),('Web'),('Mobile'),('WhatsApp'),('Video')
),
types AS (
    SELECT column1 AS tp FROM VALUES
    ('Inquiry'),('Complaint'),('ServiceRequest'),('PolicyChange'),
    ('ClaimUpdate'),('Payment'),('Escalation'),('Feedback')
),
subjects AS (
    SELECT column1 AS sub FROM VALUES
    ('Policy renewal inquiry'),('Premium payment question'),('Claim status update request'),
    ('Coverage change request'),('Billing discrepancy complaint'),('New policy quote request'),
    ('Beneficiary change request'),('Deductible clarification'),('Loan payment schedule inquiry'),
    ('Interest rate adjustment request'),('Account access issue'),('Document submission confirmation'),
    ('Cancellation request'),('Refund inquiry'),('Complaint about service delay'),
    ('Request for coverage explanation'),('Emergency contact update'),('Address change notification'),
    ('Payment method update'),('Feedback on recent claim experience'),
    ('Cyber insurance inquiry'),('Flood damage claim'),('Identity theft report'),
    ('Premium increase dispute'),('Policy lapse reinstatement'),('Disability claim question'),
    ('Legal liability query'),('Investment-linked policy question'),('Wellness benefit inquiry'),
    ('Digital portal access issue')
),
notes AS (
    SELECT column1 AS note FROM VALUES
    ('Customer called to ask about upcoming policy renewal options and available discounts for bundling.'),
    ('Escalated complaint regarding delayed claim settlement. Customer expressed frustration with timeline.'),
    ('Routine inquiry about adding a new driver to existing auto policy. Provided quote and sent documents.'),
    ('Customer requested coverage increase on home policy due to recent renovations.'),
    ('Payment issue resolved: customer autopay failed due to expired card. Updated payment method.'),
    ('Customer inquired about life insurance options for family. Scheduled callback with specialist.'),
    ('Follow-up on previously denied claim. Customer provided additional documentation for review.'),
    ('Customer called to dispute premium increase. Explained underwriting factors and retention offer made.'),
    ('Loan modification request discussed. Customer struggling with payments due to job change.'),
    ('Customer expressed satisfaction with recent claim processing speed. Positive feedback logged.'),
    ('Address and contact information update processed. Confirmed via email confirmation.'),
    ('Customer reported suspected fraudulent activity on account. Initiated fraud investigation.'),
    ('Premium refund processed for cancelled policy. Customer confirmed receipt.'),
    ('Customer asked about umbrella policy options for additional liability coverage.'),
    ('Complaint about long wait times on phone. Offered callback service for future calls.'),
    ('Customer threatened to cancel all policies due to repeated billing errors. Escalated to manager.'),
    ('Policy lapse occurred due to missed payments. Customer requesting reinstatement. Reviewed eligibility.'),
    ('Flood damage claim filed. Adjuster appointment scheduled within 48 hours.'),
    ('Customer received competing offer from rival insurer. Retention discount applied successfully.'),
    ('Cyber incident reported. Policy covers up to 1M in data breach liability. Claim initiated.'),
    ('Customer has had 3 denied claims this year and is considering legal action. Escalated to compliance.'),
    ('Disability claim approved after medical review. Monthly benefit payments begin next cycle.'),
    ('Customer requested digital policy documents and e-signature instead of paper forms.'),
    ('Complaint about agent being dismissive during previous call. Coaching session scheduled for agent.'),
    ('Customer expressed intent to close all accounts unless premium is reduced by 20 percent.')
),
resolutions AS (
    SELECT column1 AS res FROM VALUES ('Resolved'),('Pending'),('Escalated')
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS INTERACTION_ID,
    c.CUSTOMER_ID,
    ch.ch AS CHANNEL,
    tp.tp AS INTERACTION_TYPE,
    sub.sub AS SUBJECT,
    n.note AS NOTES,
    r.res AS RESOLUTION_STATUS,
    'AGT-' || LPAD(UNIFORM(100, 999, RANDOM())::VARCHAR, 3, '0') AS AGENT_ID,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS INTERACTION_DATE,
    CASE ch.ch
        WHEN 'Phone'  THEN UNIFORM(90, 2400, RANDOM())
        WHEN 'Chat'   THEN UNIFORM(180, 3000, RANDOM())
        WHEN 'Branch' THEN UNIFORM(600, 5400, RANDOM())
        WHEN 'Video'  THEN UNIFORM(600, 3600, RANDOM())
        ELSE NULL
    END AS DURATION_SECONDS,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS CREATED_AT
FROM new_customers c
CROSS JOIN channels ch
CROSS JOIN types tp
CROSS JOIN subjects sub
CROSS JOIN notes n
CROSS JOIN resolutions r
CROSS JOIN inter_offset o
ORDER BY RANDOM()
LIMIT 3500;


-- =========================================================================
-- 6. RAW_CALL_TRANSCRIPTS  +750  (total → ~1,000)
--    Five new transcript scenarios: Cyber, Flood, Disability, Cancellation
--    threat, and Premium dispute escalation
-- =========================================================================
INSERT INTO RAW.RAW_CALL_TRANSCRIPTS
WITH tran_offset AS (
    SELECT COALESCE(MAX(TRANSCRIPT_ID), 0) AS max_id FROM RAW.RAW_CALL_TRANSCRIPTS
),
new_customers AS (
    SELECT CUSTOMER_ID FROM RAW.RAW_CUSTOMERS WHERE CUSTOMER_ID > (
        SELECT COALESCE(MAX(CUSTOMER_ID), 0) - 1500 FROM RAW.RAW_CUSTOMERS
    )
),
reasons AS (
    SELECT column1 AS reason FROM VALUES
    ('Policy Renewal'),('Claim Status'),('Premium Dispute'),('Coverage Change'),
    ('Payment Issue'),('New Policy Inquiry'),('Cancellation Request'),('Complaint'),
    ('Loan Payment Question'),('Beneficiary Update'),
    ('Cyber Claim'),('Flood Claim'),('Disability Claim'),('Cancellation Threat'),('Escalation')
),
transcripts AS (
    SELECT column1 AS reason_match, column2 AS transcript FROM VALUES
    ('Policy Renewal',
     'Agent: Thank you for calling SecureLife Insurance. My name is Sarah. How can I help you today?\nCustomer: Hi Sarah, I received a letter about my auto policy renewal and the premium went up by 15 percent. Can you explain why?\nAgent: I understand your concern. Let me pull up your account. I can see your policy number ending in 4521. The increase is primarily due to two factors: a minor accident claim filed in March and a general rate adjustment in your area.\nCustomer: The accident wasnt my fault though. The other driver ran a red light.\nAgent: I completely understand, and I apologize for the frustration. While the claim was filed under your policy, I can review your account for any available discounts. I see you have a clean record otherwise. Let me check if we can apply a safe driver discount or a bundling discount if you have other policies with us.\nCustomer: I do have my home insurance with you as well.\nAgent: That is great news. I can apply a multi-policy bundle discount of 8 percent which would bring your new premium down significantly. Would you like me to process that?\nCustomer: Yes please, that sounds much better. Thank you for looking into this.\nAgent: My pleasure. I will process the bundle discount right away. You will receive an updated renewal notice within 5 business days. Is there anything else I can help you with?\nCustomer: No, that is all. Thanks Sarah.\nAgent: Thank you for being a valued customer. Have a wonderful day!'),

    ('Claim Status',
     'Agent: Good afternoon, thank you for calling SecureLife Insurance. This is Michael. How may I assist you?\nCustomer: Hi Michael. I filed a home insurance claim three weeks ago for water damage and I still have not heard back. I am getting very frustrated with the wait.\nAgent: I am sorry to hear about the delay. Let me look into your claim right away. Can I have your policy number or the claim reference number?\nCustomer: The claim number is CLM-78234.\nAgent: Thank you. I can see your claim was assigned to adjuster Williams. It looks like there was a delay because we needed additional photos of the damage. An email was sent to your address on file on the 5th requesting those.\nCustomer: I never received that email. This is unacceptable. I have been waiting with water-damaged floors and nobody reached out properly.\nAgent: I sincerely apologize for the communication gap. Let me escalate this claim to priority status right now. I will also arrange for our adjuster to contact you directly within 24 hours. Can I confirm your phone number and email address?\nCustomer: Yes, my number is 555-0142 and email is john.smith@email.com.\nAgent: I have updated your contact information and flagged this as urgent. You should receive a call from the adjuster by tomorrow afternoon at the latest. I am also applying a goodwill credit to your account for the inconvenience.\nCustomer: I appreciate that Michael. I just want this resolved.\nAgent: Absolutely understood. I will personally follow up to make sure this moves forward. Is there anything else?\nCustomer: No, just please make sure someone calls me.\nAgent: You have my word. Thank you for your patience.'),

    ('Premium Dispute',
     'Agent: Welcome to SecureLife Insurance. My name is Jessica. How can I help you today?\nCustomer: Jessica, I need to talk to someone about my health insurance premium. It has gone up 25 percent and I cannot afford it.\nAgent: I understand this must be concerning. Let me review your account and see what options we have available.\nCustomer: I have been with your company for 8 years and every year it just keeps going up. I am seriously considering switching to another provider.\nAgent: I value your loyalty and I want to make sure we find a solution that works for you. I can see your current plan is our Gold tier. We have a few options: we could look at adjusting your deductible to lower the monthly premium, we could review if the Silver tier might better fit your needs with a lower cost, or I can check if you qualify for any loyalty discounts given your 8-year history.\nCustomer: What would the Silver tier look like for me?\nAgent: The Silver tier would reduce your monthly premium by about 18 percent. The main difference is a slightly higher copay for specialist visits and a higher out-of-pocket maximum. Your primary care visits and prescription coverage would remain the same.\nCustomer: That actually doesnt sound too bad. And the loyalty discount?\nAgent: I can apply a 5 percent loyalty discount on top of whichever plan you choose. So with Silver plus the loyalty discount, you would actually be paying less than your current rate before the increase.\nCustomer: Okay, lets go with that. Can you switch me over?\nAgent: Absolutely. I will process the change to Silver tier with the loyalty discount effective your next billing cycle. You will receive confirmation documents within 3 business days.\nCustomer: Thank you Jessica. You have been very helpful.\nAgent: It is my pleasure. We appreciate your continued trust in SecureLife.'),

    ('Coverage Change',
     'Agent: SecureLife Insurance, this is David. How may I help you?\nCustomer: Hi David, I recently had a baby and I need to add them to my health insurance policy and also increase my life insurance coverage.\nAgent: Congratulations on the new addition to your family! I would be happy to help with both of those changes. Lets start with the health insurance. Adding a dependent is straightforward since you are within the qualifying life event window.\nCustomer: Great. Her name is Emma and she was born on August 15th.\nAgent: I have added Emma to your health policy. The additional premium for a dependent child on your current plan is 150 dollars per month. Now for the life insurance, what coverage amount were you thinking?\nCustomer: I currently have 250,000 and I would like to increase to 500,000.\nAgent: That is a sensible decision with a growing family. To double your coverage, we would need a brief health questionnaire update since your last review was over a year ago. I can walk you through the questions now or schedule a phone appointment at your convenience.\nCustomer: Can we do it now? I have about 20 minutes.\nAgent: Let us do that right now then. This should only take about 10 minutes.'),

    ('Payment Issue',
     'Agent: Thank you for calling SecureLife. I am Amanda. How can I assist?\nCustomer: Hi Amanda. My auto insurance payment was taken out twice this month and I need the duplicate charge reversed immediately.\nAgent: Oh no, I apologize for that error. Let me look into your account right away to see what happened.\nCustomer: This has caused my checking account to overdraft and I was charged a 35 dollar fee by my bank.\nAgent: I am very sorry about that. I can see the duplicate charge was processed on the 3rd. It appears our system had a glitch during the batch processing. I am going to initiate an immediate refund for the duplicate payment. The refund should appear in your account within 2 to 3 business days.\nCustomer: What about the overdraft fee? That was caused by your error.\nAgent: You are absolutely right, and we take responsibility for that. I will submit a reimbursement request for the 35 dollar overdraft fee as well. I will need you to send us a copy of the bank statement showing the fee, and we will reimburse it along with the duplicate payment.\nCustomer: Okay, where do I send it?\nAgent: You can email it to billing@securelife.com with your policy number in the subject line. I will note your account so the team is expecting it.\nCustomer: Alright, I will send that today. Thank you for handling this quickly.\nAgent: Of course. Again, I sincerely apologize for the inconvenience. We will get this sorted out promptly.'),

    ('New Policy Inquiry',
     'Agent: Good morning, SecureLife Insurance. This is Robert. How may I help you today?\nCustomer: Hi Robert, I am a new homeowner and I need to get homeowners insurance set up. My mortgage company requires it before closing.\nAgent: Congratulations on the new home! I would be happy to help you get covered. Can you tell me a bit about the property? The address, approximate square footage, and when it was built?\nCustomer: It is at 425 Oak Street in Portland. About 2,200 square feet, built in 1998. It has a new roof that was put on last year.\nAgent: Excellent, the new roof will actually help with your premium. Based on the information, I can put together a few coverage options. Our standard homeowners policy would cover the dwelling, personal property, liability, and additional living expenses. For a home like yours I would recommend coverage in the range of 350,000 to 400,000 for the dwelling.\nCustomer: What would the premium look like?\nAgent: For 375,000 in dwelling coverage with a 1,000 dollar deductible, you are looking at approximately 125 dollars per month. If you increase the deductible to 2,500, that drops to about 98 dollars per month.\nCustomer: The 98 dollar option sounds good. And can I bundle it with auto insurance?\nAgent: Absolutely. Bundling would save you an additional 12 percent on both policies. I can set up both today if you have your vehicle information handy.\nCustomer: I do. Lets do it.'),

    ('Cancellation Request',
     'Agent: SecureLife Insurance, this is Kelly. How can I help you today?\nCustomer: I want to cancel my auto insurance policy effective immediately.\nAgent: I am sorry to hear that. Before I process the cancellation, may I ask what prompted this decision? I want to make sure we have addressed any concerns.\nCustomer: I found a better rate with another company. Your rates are just too high.\nAgent: I understand, and I appreciate your honesty. If you do not mind sharing, what rate were you offered? I would like to see if there is anything we can do to match or come close.\nCustomer: They offered me 89 dollars a month compared to the 142 I am paying with you.\nAgent: That is a significant difference. Let me review your policy to see if there are any discounts or adjustments we have not applied. I see you have a clean driving record for the past 3 years and you completed a defensive driving course last year. I can apply both of those discounts which were not on your current policy. That would bring your premium down to 96 dollars per month.\nCustomer: That is closer but still more than their offer.\nAgent: I understand. Let me also check if adjusting your coverage levels could help. And I want to mention that our claims satisfaction rating is significantly higher than the industry average, which can matter a lot when you actually need to file a claim.\nCustomer: Hmm, let me think about it. Can I call back in a day or two?\nAgent: Of course. I have noted the potential discounts on your account so they are ready to apply whenever you decide. Take your time and call us back anytime.'),

    ('Complaint',
     'Agent: Thank you for calling SecureLife Insurance. This is Tom. How may I help you?\nCustomer: I need to file a formal complaint. I had a home insurance claim denied and I believe it was handled unfairly.\nAgent: I am sorry to hear about your experience. I want to understand what happened so we can address this properly. Can you tell me about the claim?\nCustomer: I had a pipe burst in my kitchen two months ago. The damage was extensive. Your adjuster came out, took photos, and then three weeks later I got a letter saying the claim was denied due to lack of maintenance.\nAgent: I understand your frustration. Let me pull up the claim details. I see claim CLM-45678. The denial was based on the adjuster finding evidence of long-term corrosion on the pipe. However, I want to make sure this was evaluated correctly.\nCustomer: The pipe was in the wall. How am I supposed to know about corrosion inside a wall? I have maintained my home diligently.\nAgent: That is a very valid point, and I think this deserves a second review. I am going to escalate this to our senior claims review team. They will re-examine the evidence and consider factors like the accessibility of the pipe. I will also request that a second independent adjuster review the damage.\nCustomer: How long will this take? I have had contractors waiting.\nAgent: The senior review typically takes 5 to 7 business days. Given the circumstances, I am marking this as priority. I will also have a claims manager call you within 48 hours to discuss the process and timeline.\nCustomer: Fine. I expect a fair outcome this time.\nAgent: I will personally track this and follow up with you next week. You have my direct extension, 4421, if you need to reach me.'),

    ('Loan Payment Question',
     'Agent: SecureLife Financial Services. My name is Maria. How can I help you today?\nCustomer: Hi Maria. I have a personal loan with you and I want to make an extra payment toward the principal. How does that work?\nAgent: Great question. Making extra principal payments is a smart way to reduce your total interest. You can make additional payments at any time without any prepayment penalties.\nCustomer: Oh good, no penalties. If I pay an extra 500 dollars per month, how much would that shorten my loan term?\nAgent: Let me calculate that for you. Your current loan balance is 28,400 dollars at 6.5 percent interest with 36 months remaining. With an additional 500 per month, you would pay off the loan in approximately 22 months instead of 36, saving roughly 1,850 dollars in interest.\nCustomer: That is a significant savings. Can I set up automatic additional payments?\nAgent: Yes, I can set that up for you right now. The extra 500 would be drafted on the same date as your regular payment and applied entirely to principal.\nCustomer: Perfect, lets do it.'),

    ('Beneficiary Update',
     'Agent: SecureLife Insurance, this is Chris. How may I assist you?\nCustomer: I need to update the beneficiary on my life insurance policy. I recently got divorced and need to change it.\nAgent: I understand. I can help you with that. For security, can I verify your identity first? Can you provide your date of birth and the last four digits of your social?\nCustomer: December 15, 1985. Last four is 7834.\nAgent: Thank you, identity verified. I see your current beneficiary is listed as your former spouse. Who would you like to designate as the new primary beneficiary?\nCustomer: My sister, Patricia Williams. And I would like to add my mother as the contingent beneficiary.\nAgent: Of course. I will need Patricia full name, date of birth, and relationship, and the same for your mother as contingent beneficiary. Once I process this, you will receive a confirmation letter in the mail within 7 to 10 business days. I also recommend reviewing your other financial documents and any other policies for similar updates.\nCustomer: Good point. Can you check if I have any other policies that list my ex as beneficiary?\nAgent: Let me check. I see you also have a supplemental life policy. I can update that beneficiary at the same time if you would like.\nCustomer: Yes please, change both.'),

    -- NEW SCENARIOS -----------------------------------------------------
    ('Cyber Claim',
     'Agent: Thank you for calling SecureLife. I am Jennifer, your cyber insurance specialist. How can I help?\nCustomer: Jennifer, our small business was hit by a ransomware attack last night. All our files are encrypted and the attackers are demanding 50,000 dollars in Bitcoin. We have cyber insurance with you.\nAgent: I am very sorry to hear that. You have done the right thing calling us immediately. We need to act quickly. Can you tell me your policy number?\nCustomer: Its CYB-00234.\nAgent: I can see your policy. You have up to 1 million in coverage for ransomware and data breach incidents. Here is what we need to do right now. First, do not pay the ransom without consulting our incident response team. Second, I am going to connect you with our 24-hour cyber incident response hotline immediately.\nCustomer: Should we shut down all our systems?\nAgent: That is a critical question and our incident response team will advise you on that. Generally, isolating affected machines is important. They will also assess whether to involve the FBI as ransomware attacks are federal crimes.\nCustomer: This is terrifying. We have customer data on those servers.\nAgent: I understand. Our policy also covers data breach notification costs, which can be significant. Our legal team and PR crisis team are available if customer notifications are needed. I am connecting you to our incident response line right now. They operate 24/7 specifically for situations like this.\nCustomer: Thank you Jennifer. I am relieved we have coverage for this.\nAgent: That is what we are here for. Please hold and I will make sure the team is briefed before I connect you.'),

    ('Flood Claim',
     'Agent: SecureLife Insurance claims department, this is Alex. How may I help you?\nCustomer: Alex, I need to file an urgent flood claim. We had 18 inches of water in our first floor from the river overflowing last night. Everything is destroyed.\nAgent: I am so sorry. Are you and your family safe? That is the most important thing right now.\nCustomer: Yes, we got out safely. We are staying at a hotel. But our home is in terrible shape. Furniture, appliances, flooring, everything is ruined.\nAgent: I am glad you are all safe. Let me look at your policy. I see you have our comprehensive home policy with flood coverage added as a rider. Your coverage limit for flood damage is 350,000 for the dwelling and 75,000 for contents.\nCustomer: Will the hotel costs be covered too?\nAgent: Yes. Your policy includes additional living expenses up to 36 months while your home is uninhabitable. That covers hotel, meals above your normal food budget, and reasonable transportation costs. Keep all your receipts.\nCustomer: What do we do next? Can we start cleaning up?\nAgent: Document everything with photos and videos before any cleanup begins. Then you can start removing water and wet materials to prevent mold, which your policy also covers up to 15,000. I am dispatching an emergency adjuster who can be there within 4 to 6 hours. We also work with preferred contractors who specialize in flood remediation.\nCustomer: This is overwhelming but at least we have coverage.\nAgent: You have good coverage and we are going to work through this with you. I am also scheduling a check-in call with you tomorrow to make sure you have everything you need.'),

    ('Disability Claim',
     'Agent: SecureLife Insurance, disability claims. My name is Rachel. How can I help?\nCustomer: Hi Rachel. I had major surgery three weeks ago and my doctor says I will be unable to work for at least six months. I have disability insurance through SecureLife.\nAgent: I am sorry to hear about your surgery and I hope your recovery is going well. I can help you with your disability claim. Can you tell me your policy number?\nCustomer: It is DIS-77891.\nAgent: Thank you. I can see your short and long-term disability policy. Your short-term disability benefit begins after a 14-day elimination period, which you have already passed since your surgery was three weeks ago. Your benefit is 60 percent of your monthly salary.\nCustomer: So I should have already started receiving payments?\nAgent: You should have received your first payment last week. Let me check the claim status. I see your claim was filed but there is a note that we are waiting for additional medical documentation from your surgeon confirming the expected recovery timeline.\nCustomer: I gave the forms to my doctors office two weeks ago. Why is this taking so long? I have a mortgage and bills to pay.\nAgent: I completely understand the urgency. I am flagging this claim as critical right now and personally calling your surgeon office today to follow up on those forms. Additionally, given the documentation was submitted two weeks ago, I am escalating this to our expedited review team. You should receive a decision within 48 hours and if approved, a retroactive payment covering everything from the elimination period.\nCustomer: That would be a huge relief. I am really struggling financially.\nAgent: I hear you. We take our obligations to our policyholders very seriously, especially in situations like yours. I am going to make sure this gets resolved quickly.'),

    ('Cancellation Threat',
     'Agent: SecureLife Insurance, this is Patricia speaking. How may I help you today?\nCustomer: Patricia, I am extremely frustrated and I am calling to cancel all three of my policies unless something changes today.\nAgent: I am sorry to hear you are frustrated. I absolutely want to understand what has happened and do everything I can to resolve this. Can you tell me what has been going on?\nCustomer: I have been a customer for 11 years. Eleven years. In the past 8 months I have had two claims denied, been billed incorrectly three times, and spent 14 hours on hold with your call center. I am done.\nAgent: That is completely unacceptable and I sincerely apologize for everything you have experienced. Eleven years is a long and valued relationship and you deserve far better than this. Can I have your name and policy numbers so I can review everything right now?\nCustomer: My name is Thomas Webb. Policies ending in 3312, 8821, and 6654.\nAgent: Thank you Thomas. I am pulling up your account now and I can see the history. I want to address each issue you mentioned. Starting with the denied claims, I want to review both of those today to see if there are grounds for appeal.\nCustomer: The second denial was for storm damage that was clearly covered in my policy. Your adjuster said it was excluded but the exclusion does not apply to my coverage tier.\nAgent: I can see the denial on claim 45991. Looking at your policy language, you may actually be right about the exclusion not applying. I am going to have our senior claims adjuster review this as an urgent appeal today.\nCustomer: What about the billing errors? I was overbilled by 340 dollars over three months.\nAgent: I can see three billing adjustments that should have been credits on your account. I am processing a 340 dollar credit right now that will appear on your next statement. Thomas, I want to be completely transparent with you. You have been treated poorly and I want to make this right. Would you be willing to give us 48 hours to review the claim denial and have a senior manager call you with a resolution plan?\nCustomer: Fine. 48 hours. But if I do not hear back I am cancelling everything.\nAgent: You have my direct number. I will call you personally tomorrow morning with an update.'),

    ('Escalation',
     'Agent: SecureLife Insurance executive escalation team, this is Director Margaret Chen speaking. How may I help you today?\nCustomer: Director Chen, I have been escalated to you because I have been trying to resolve the same issue for four months and I am ready to file a regulatory complaint.\nAgent: I understand and I appreciate you giving us the opportunity to address this at the executive level. Before we go further, I want to assure you that I have full authority to resolve your issue today. Can you please summarize the situation for me?\nCustomer: I filed a life insurance claim after my husband passed away in February. It is now June and I still have not received the 500,000 policy benefit. I have submitted every document requested, sometimes multiple times. I have been given different information by different agents each time I call.\nAgent: I am deeply sorry for your loss and I am appalled that you are going through this during such a difficult time. Please accept my sincere condolences and apologies on behalf of SecureLife. This is not how we should treat anyone, especially someone going through grief.\nCustomer: I just want what my husband paid for all those years.\nAgent: You are absolutely right to expect that. Let me pull up your claim right now. I can see claim LIF-11234. I see the issue immediately. The claim has been stuck in document review for 67 days because of an internal processing error, not because of any deficiency in your documentation. All your documents are complete and in order.\nCustomer: So there was nothing wrong with what I submitted?\nAgent: Nothing at all. This is entirely an internal failure. I am authorizing full payment processing right now. Given the extraordinary delay, I am also approving a hardship payment of 50,000 to be processed within 24 hours while the full amount processes, which will take 3 to 5 business days. Additionally, I am waiving all processing fees and applying our maximum goodwill credit to your account.\nCustomer: I do not know what to say. Thank you.\nAgent: Please know that we take full responsibility for this failure. I will personally monitor your payment and call you when it is processed. You should never have had to wait this long.')
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS TRANSCRIPT_ID,
    c.CUSTOMER_ID,
    NULL AS INTERACTION_ID,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS CALL_DATE,
    UNIFORM(120, 1800, RANDOM()) AS DURATION_SECONDS,
    'AGT-' || LPAD(UNIFORM(100, 999, RANDOM())::VARCHAR, 3, '0') AS AGENT_ID,
    CASE MOD(UNIFORM(1, 15, RANDOM()), 15)
        WHEN 0  THEN 'Sarah Mitchell'
        WHEN 1  THEN 'Michael Torres'
        WHEN 2  THEN 'Jessica Chen'
        WHEN 3  THEN 'David Patel'
        WHEN 4  THEN 'Amanda Rodriguez'
        WHEN 5  THEN 'Robert Kim'
        WHEN 6  THEN 'Kelly Johnson'
        WHEN 7  THEN 'Tom Wilson'
        WHEN 8  THEN 'Maria Santos'
        WHEN 9  THEN 'Jennifer Park'
        WHEN 10 THEN 'Alex Nguyen'
        WHEN 11 THEN 'Rachel Lee'
        WHEN 12 THEN 'Patricia Moore'
        WHEN 13 THEN 'Margaret Chen'
        ELSE         'Chris Anderson'
    END AS AGENT_NAME,
    t.transcript AS TRANSCRIPT_TEXT,
    r.reason AS CALL_REASON,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS CREATED_AT
FROM new_customers c
CROSS JOIN reasons r
CROSS JOIN transcripts t
CROSS JOIN tran_offset o
WHERE r.reason = t.reason_match
ORDER BY RANDOM()
LIMIT 750;


-- =========================================================================
-- Verify final record counts
-- =========================================================================
SELECT 'RAW_CUSTOMERS'      AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM RAW.RAW_CUSTOMERS
UNION ALL SELECT 'RAW_POLICIES',       COUNT(*) FROM RAW.RAW_POLICIES
UNION ALL SELECT 'RAW_CLAIMS',         COUNT(*) FROM RAW.RAW_CLAIMS
UNION ALL SELECT 'RAW_LOANS',          COUNT(*) FROM RAW.RAW_LOANS
UNION ALL SELECT 'RAW_INTERACTIONS',   COUNT(*) FROM RAW.RAW_INTERACTIONS
UNION ALL SELECT 'RAW_CALL_TRANSCRIPTS', COUNT(*) FROM RAW.RAW_CALL_TRANSCRIPTS
ORDER BY 1;
