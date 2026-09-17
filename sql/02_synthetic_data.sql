-- =============================================================================
-- 02_synthetic_data.sql - Referentially Consistent Synthetic Data Generation
-- Generates realistic insurance/lending customer data with call transcripts
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- =========================================================================
-- 1. RAW_CUSTOMERS (500 rows)
-- =========================================================================
INSERT INTO RAW.RAW_CUSTOMERS
WITH first_names AS (
    SELECT column1 AS name FROM VALUES
    ('James'),('Mary'),('Robert'),('Patricia'),('John'),('Jennifer'),('Michael'),('Linda'),
    ('David'),('Elizabeth'),('William'),('Barbara'),('Richard'),('Susan'),('Joseph'),('Jessica'),
    ('Thomas'),('Sarah'),('Christopher'),('Karen'),('Charles'),('Lisa'),('Daniel'),('Nancy'),
    ('Matthew'),('Betty'),('Anthony'),('Margaret'),('Mark'),('Sandra'),('Donald'),('Ashley'),
    ('Steven'),('Dorothy'),('Paul'),('Kimberly'),('Andrew'),('Emily'),('Joshua'),('Donna'),
    ('Raj'),('Priya'),('Amit'),('Sakura'),('Kenji'),('Wei'),('Mei'),('Omar'),('Fatima'),('Carlos')
),
last_names AS (
    SELECT column1 AS name FROM VALUES
    ('Smith'),('Johnson'),('Williams'),('Brown'),('Jones'),('Garcia'),('Miller'),('Davis'),
    ('Rodriguez'),('Martinez'),('Hernandez'),('Lopez'),('Gonzalez'),('Wilson'),('Anderson'),
    ('Thomas'),('Taylor'),('Moore'),('Jackson'),('Martin'),('Lee'),('Perez'),('Thompson'),
    ('White'),('Harris'),('Sanchez'),('Clark'),('Ramirez'),('Lewis'),('Robinson'),
    ('Patel'),('Singh'),('Kumar'),('Chen'),('Wang'),('Tanaka'),('Kim'),('Nguyen'),('Ali'),('Santos')
),
segments AS (
    SELECT column1 AS seg, column2 AS weight FROM VALUES
    ('Basic', 30), ('Standard', 40), ('Premium', 20), ('VIP', 10)
),
countries AS (
    SELECT column1 AS country, column2 AS state_name, column3 AS city FROM VALUES
    ('USA','California','Los Angeles'),('USA','California','San Francisco'),('USA','California','San Diego'),
    ('USA','New York','New York City'),('USA','New York','Buffalo'),
    ('USA','Texas','Houston'),('USA','Texas','Dallas'),('USA','Texas','Austin'),
    ('USA','Florida','Miami'),('USA','Florida','Orlando'),
    ('USA','Illinois','Chicago'),('USA','Pennsylvania','Philadelphia'),
    ('USA','Massachusetts','Boston'),('USA','Washington','Seattle'),
    ('USA','Colorado','Denver'),('USA','Georgia','Atlanta'),
    ('UK','England','London'),('UK','England','Manchester'),('UK','England','Birmingham'),
    ('UK','Scotland','Edinburgh'),
    ('Canada','Ontario','Toronto'),('Canada','British Columbia','Vancouver'),
    ('India','Maharashtra','Mumbai'),('India','Karnataka','Bangalore'),
    ('Singapore','SG','Singapore'),
    ('Australia','NSW','Sydney'),('Australia','VIC','Melbourne')
),
emp_statuses AS (
    SELECT column1 AS status FROM VALUES ('Employed'),('Self-Employed'),('Retired'),('Unemployed')
),
base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY RANDOM()) AS CUSTOMER_ID,
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
    ORDER BY RANDOM()
    LIMIT 500
)
SELECT
    b.CUSTOMER_ID,
    b.FIRST_NAME,
    b.LAST_NAME,
    LOWER(b.FIRST_NAME || '.' || b.LAST_NAME || b.CUSTOMER_ID || '@' ||
        CASE MOD(b.CUSTOMER_ID, 4)
            WHEN 0 THEN 'gmail.com'
            WHEN 1 THEN 'outlook.com'
            WHEN 2 THEN 'yahoo.com'
            ELSE 'company.com'
        END) AS EMAIL,
    '+1-' || LPAD(UNIFORM(200, 999, RANDOM())::VARCHAR, 3, '0') || '-' ||
        LPAD(UNIFORM(1000, 9999, RANDOM())::VARCHAR, 4, '0') AS PHONE,
    DATEADD('day', -UNIFORM(7300, 25550, RANDOM()), CURRENT_DATE()) AS DOB,
    UNIFORM(100, 9999, RANDOM())::VARCHAR || ' ' ||
        CASE MOD(b.CUSTOMER_ID, 5) WHEN 0 THEN 'Main St' WHEN 1 THEN 'Oak Ave' WHEN 2 THEN 'Park Rd' WHEN 3 THEN 'Elm Blvd' ELSE 'Cedar Ln' END AS ADDRESS,
    b.CITY,
    b.STATE,
    b.COUNTRY,
    b.CUSTOMER_SEGMENT,
    CASE b.CUSTOMER_SEGMENT
        WHEN 'VIP' THEN UNIFORM(750, 850, RANDOM())
        WHEN 'Premium' THEN UNIFORM(700, 800, RANDOM())
        WHEN 'Standard' THEN UNIFORM(620, 750, RANDOM())
        ELSE UNIFORM(500, 680, RANDOM())
    END AS CREDIT_SCORE,
    CASE b.CUSTOMER_SEGMENT
        WHEN 'VIP' THEN UNIFORM(150000, 500000, RANDOM())
        WHEN 'Premium' THEN UNIFORM(80000, 200000, RANDOM())
        WHEN 'Standard' THEN UNIFORM(40000, 100000, RANDOM())
        ELSE UNIFORM(20000, 60000, RANDOM())
    END::NUMBER(12,2) AS ANNUAL_INCOME,
    b.EMPLOYMENT_STATUS,
    CASE WHEN UNIFORM(1, 100, RANDOM()) <= 85 THEN TRUE ELSE FALSE END AS IS_ACTIVE,
    DATEADD('day', -UNIFORM(30, 1095, RANDOM()), CURRENT_DATE()) AS CREATED_AT,
    DATEADD('day', -UNIFORM(0, 30, RANDOM()), CURRENT_DATE()) AS UPDATED_AT
FROM base b;


-- =========================================================================
-- 2. RAW_POLICIES (800 rows, 1-3 policies per customer)
-- =========================================================================
INSERT INTO RAW.RAW_POLICIES
WITH policy_types AS (
    SELECT column1 AS pt FROM VALUES ('Auto'),('Home'),('Life'),('Health'),('Travel')
),
policy_statuses AS (
    SELECT column1 AS ps, column2 AS weight FROM VALUES
    ('Active', 60), ('Renewed', 15), ('Lapsed', 15), ('Cancelled', 10)
)
SELECT
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS POLICY_ID,
    c.CUSTOMER_ID,
    pt.pt AS POLICY_TYPE,
    ps.ps AS POLICY_STATUS,
    CASE pt.pt
        WHEN 'Auto' THEN UNIFORM(500, 3000, RANDOM())
        WHEN 'Home' THEN UNIFORM(800, 5000, RANDOM())
        WHEN 'Life' THEN UNIFORM(200, 2000, RANDOM())
        WHEN 'Health' THEN UNIFORM(300, 1500, RANDOM())
        ELSE UNIFORM(100, 800, RANDOM())
    END::NUMBER(12,2) AS PREMIUM_AMOUNT,
    CASE pt.pt
        WHEN 'Auto' THEN UNIFORM(15000, 100000, RANDOM())
        WHEN 'Home' THEN UNIFORM(100000, 500000, RANDOM())
        WHEN 'Life' THEN UNIFORM(50000, 1000000, RANDOM())
        WHEN 'Health' THEN UNIFORM(25000, 200000, RANDOM())
        ELSE UNIFORM(5000, 50000, RANDOM())
    END::NUMBER(14,2) AS COVERAGE_AMOUNT,
    UNIFORM(250, 5000, RANDOM())::NUMBER(10,2) AS DEDUCTIBLE_AMOUNT,
    DATEADD('day', -UNIFORM(30, 730, RANDOM()), CURRENT_DATE()) AS START_DATE,
    DATEADD('day', UNIFORM(30, 365, RANDOM()), CURRENT_DATE()) AS END_DATE,
    DATEADD('day', UNIFORM(30, 365, RANDOM()), CURRENT_DATE()) AS RENEWAL_DATE,
    UNIFORM(30, 100, RANDOM())::NUMBER(5,2) AS UNDERWRITING_SCORE,
    CASE
        WHEN UNIFORM(1, 100, RANDOM()) <= 50 THEN 'Low'
        WHEN UNIFORM(1, 100, RANDOM()) <= 80 THEN 'Medium'
        ELSE 'High'
    END AS RISK_CATEGORY,
    DATEADD('day', -UNIFORM(30, 730, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM RAW.RAW_CUSTOMERS c
CROSS JOIN policy_types pt
CROSS JOIN policy_statuses ps
ORDER BY RANDOM()
LIMIT 800;


-- =========================================================================
-- 3. RAW_CLAIMS (300 rows)
-- =========================================================================
INSERT INTO RAW.RAW_CLAIMS
WITH claim_types AS (
    SELECT column1 AS ct FROM VALUES ('Accident'),('Theft'),('Natural Disaster'),('Medical'),('Property Damage'),('Liability')
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
    ('Roof leak discovered after prolonged rain, ceiling damage')
)
SELECT
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS CLAIM_ID,
    p.POLICY_ID,
    p.CUSTOMER_ID,
    ct.ct AS CLAIM_TYPE,
    cs.cs AS CLAIM_STATUS,
    UNIFORM(500, 50000, RANDOM())::NUMBER(12,2) AS CLAIM_AMOUNT,
    CASE WHEN cs.cs IN ('Approved', 'Settled')
        THEN UNIFORM(400, 45000, RANDOM())::NUMBER(12,2)
        ELSE NULL
    END AS SETTLEMENT_AMOUNT,
    DATEADD('day', -UNIFORM(7, 365, RANDOM()), CURRENT_DATE()) AS FILED_DATE,
    CASE WHEN cs.cs IN ('Approved', 'Denied', 'Settled')
        THEN DATEADD('day', -UNIFORM(0, 60, RANDOM()), CURRENT_DATE())
        ELSE NULL
    END AS RESOLVED_DATE,
    cd.descr AS DESCRIPTION,
    DATEADD('day', -UNIFORM(7, 365, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM RAW.RAW_POLICIES p
CROSS JOIN claim_types ct
CROSS JOIN claim_statuses cs
CROSS JOIN claim_descriptions cd
ORDER BY RANDOM()
LIMIT 300;


-- =========================================================================
-- 4. RAW_LOANS (400 rows)
-- =========================================================================
INSERT INTO RAW.RAW_LOANS
WITH loan_types AS (
    SELECT column1 AS lt FROM VALUES ('Mortgage'),('Auto'),('Personal'),('Business')
),
loan_statuses AS (
    SELECT column1 AS ls FROM VALUES ('Active'),('PaidOff'),('Default'),('Delinquent')
)
SELECT
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS LOAN_ID,
    c.CUSTOMER_ID,
    lt.lt AS LOAN_TYPE,
    ls.ls AS LOAN_STATUS,
    CASE lt.lt
        WHEN 'Mortgage' THEN UNIFORM(100000, 800000, RANDOM())
        WHEN 'Auto' THEN UNIFORM(10000, 60000, RANDOM())
        WHEN 'Personal' THEN UNIFORM(5000, 50000, RANDOM())
        ELSE UNIFORM(25000, 500000, RANDOM())
    END::NUMBER(14,2) AS PRINCIPAL_AMOUNT,
    UNIFORM(250, 1200, RANDOM()) / 100.0 AS INTEREST_RATE,
    CASE lt.lt
        WHEN 'Mortgage' THEN UNIFORM(800, 4000, RANDOM())
        WHEN 'Auto' THEN UNIFORM(200, 900, RANDOM())
        WHEN 'Personal' THEN UNIFORM(100, 800, RANDOM())
        ELSE UNIFORM(500, 3000, RANDOM())
    END::NUMBER(10,2) AS MONTHLY_PAYMENT,
    CASE ls.ls
        WHEN 'PaidOff' THEN 0
        ELSE UNIFORM(1000, 700000, RANDOM())
    END::NUMBER(14,2) AS OUTSTANDING_BALANCE,
    DATEADD('day', -UNIFORM(90, 1825, RANDOM()), CURRENT_DATE()) AS ORIGINATION_DATE,
    DATEADD('day', UNIFORM(365, 10950, RANDOM()), CURRENT_DATE()) AS MATURITY_DATE,
    CASE ls.ls
        WHEN 'Delinquent' THEN UNIFORM(30, 180, RANDOM())
        WHEN 'Default' THEN UNIFORM(180, 365, RANDOM())
        ELSE 0
    END AS DAYS_PAST_DUE,
    DATEADD('day', -UNIFORM(90, 1825, RANDOM()), CURRENT_DATE()) AS CREATED_AT
FROM RAW.RAW_CUSTOMERS c
CROSS JOIN loan_types lt
CROSS JOIN loan_statuses ls
ORDER BY RANDOM()
LIMIT 400;


-- =========================================================================
-- 5. RAW_INTERACTIONS (1200 rows)
-- =========================================================================
INSERT INTO RAW.RAW_INTERACTIONS
WITH channels AS (
    SELECT column1 AS ch FROM VALUES ('Email'),('Phone'),('Chat'),('Branch'),('Web'),('Mobile')
),
types AS (
    SELECT column1 AS tp FROM VALUES ('Inquiry'),('Complaint'),('ServiceRequest'),('PolicyChange'),('ClaimUpdate'),('Payment')
),
subjects AS (
    SELECT column1 AS sub FROM VALUES
    ('Policy renewal inquiry'),('Premium payment question'),('Claim status update request'),
    ('Coverage change request'),('Billing discrepancy complaint'),('New policy quote request'),
    ('Beneficiary change request'),('Deductible clarification'),('Loan payment schedule inquiry'),
    ('Interest rate adjustment request'),('Account access issue'),('Document submission confirmation'),
    ('Cancellation request'),('Refund inquiry'),('Complaint about service delay'),
    ('Request for coverage explanation'),('Emergency contact update'),('Address change notification'),
    ('Payment method update'),('Feedback on recent claim experience')
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
    ('Complaint about long wait times on phone. Offered callback service for future calls.')
),
resolutions AS (
    SELECT column1 AS res FROM VALUES ('Resolved'),('Pending'),('Escalated')
)
SELECT
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS INTERACTION_ID,
    c.CUSTOMER_ID,
    ch.ch AS CHANNEL,
    tp.tp AS INTERACTION_TYPE,
    sub.sub AS SUBJECT,
    n.note AS NOTES,
    r.res AS RESOLUTION_STATUS,
    'AGT-' || LPAD(UNIFORM(100, 999, RANDOM())::VARCHAR, 3, '0') AS AGENT_ID,
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()) AS INTERACTION_DATE,
    CASE ch.ch
        WHEN 'Phone' THEN UNIFORM(120, 1800, RANDOM())
        WHEN 'Chat' THEN UNIFORM(300, 2400, RANDOM())
        WHEN 'Branch' THEN UNIFORM(600, 3600, RANDOM())
        ELSE NULL
    END AS DURATION_SECONDS,
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()) AS CREATED_AT
FROM RAW.RAW_CUSTOMERS c
CROSS JOIN channels ch
CROSS JOIN types tp
CROSS JOIN subjects sub
CROSS JOIN notes n
CROSS JOIN resolutions r
ORDER BY RANDOM()
LIMIT 1200;


-- =========================================================================
-- 6. RAW_CALL_TRANSCRIPTS (250 rows with realistic multi-turn conversations)
-- =========================================================================
INSERT INTO RAW.RAW_CALL_TRANSCRIPTS
WITH reasons AS (
    SELECT column1 AS reason FROM VALUES
    ('Policy Renewal'),('Claim Status'),('Premium Dispute'),('Coverage Change'),
    ('Payment Issue'),('New Policy Inquiry'),('Cancellation Request'),('Complaint'),
    ('Loan Payment Question'),('Beneficiary Update')
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
     'Agent: SecureLife Insurance, this is Chris. How may I assist you?\nCustomer: I need to update the beneficiary on my life insurance policy. I recently got divorced and need to change it.\nAgent: I understand. I can help you with that. For security, can I verify your identity first? Can you provide your date of birth and the last four digits of your social?\nCustomer: December 15, 1985. Last four is 7834.\nAgent: Thank you, identity verified. I see your current beneficiary is listed as your former spouse. Who would you like to designate as the new primary beneficiary?\nCustomer: My sister, Patricia Williams. And I would like to add my mother as the contingent beneficiary.\nAgent: Of course. I will need Patricia full name, date of birth, and relationship, and the same for your mother as contingent beneficiary. Once I process this, you will receive a confirmation letter in the mail within 7 to 10 business days. I also recommend reviewing your other financial documents and any other policies for similar updates.\nCustomer: Good point. Can you check if I have any other policies that list my ex as beneficiary?\nAgent: Let me check. I see you also have a supplemental life policy. I can update that beneficiary at the same time if you would like.\nCustomer: Yes please, change both.')
)
SELECT
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS TRANSCRIPT_ID,
    c.CUSTOMER_ID,
    NULL AS INTERACTION_ID,
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()) AS CALL_DATE,
    UNIFORM(180, 1200, RANDOM()) AS DURATION_SECONDS,
    'AGT-' || LPAD(UNIFORM(100, 999, RANDOM())::VARCHAR, 3, '0') AS AGENT_ID,
    CASE MOD(UNIFORM(1, 10, RANDOM()), 10)
        WHEN 0 THEN 'Sarah Mitchell'
        WHEN 1 THEN 'Michael Torres'
        WHEN 2 THEN 'Jessica Chen'
        WHEN 3 THEN 'David Patel'
        WHEN 4 THEN 'Amanda Rodriguez'
        WHEN 5 THEN 'Robert Kim'
        WHEN 6 THEN 'Kelly Johnson'
        WHEN 7 THEN 'Tom Wilson'
        WHEN 8 THEN 'Maria Santos'
        ELSE 'Chris Anderson'
    END AS AGENT_NAME,
    t.transcript AS TRANSCRIPT_TEXT,
    r.reason AS CALL_REASON,
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()) AS CREATED_AT
FROM RAW.RAW_CUSTOMERS c
CROSS JOIN reasons r
CROSS JOIN transcripts t
WHERE r.reason = t.reason_match
ORDER BY RANDOM()
LIMIT 250;


-- =========================================================================
-- Verify data generation
-- =========================================================================
SELECT 'RAW_CUSTOMERS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM RAW.RAW_CUSTOMERS
UNION ALL SELECT 'RAW_POLICIES', COUNT(*) FROM RAW.RAW_POLICIES
UNION ALL SELECT 'RAW_CLAIMS', COUNT(*) FROM RAW.RAW_CLAIMS
UNION ALL SELECT 'RAW_LOANS', COUNT(*) FROM RAW.RAW_LOANS
UNION ALL SELECT 'RAW_INTERACTIONS', COUNT(*) FROM RAW.RAW_INTERACTIONS
UNION ALL SELECT 'RAW_CALL_TRANSCRIPTS', COUNT(*) FROM RAW.RAW_CALL_TRANSCRIPTS;
