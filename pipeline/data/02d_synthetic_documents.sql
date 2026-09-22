-- =============================================================================
-- 02d_synthetic_documents.sql - Synthetic Insurance Documents
-- Generates realistic claim forms and policy summaries referencing existing customers
-- NOTE: Customer IDs must reference actual IDs from RAW_CUSTOMERS. The IDs below
-- were sampled from the CUSTOMER_360_UNIFIED table after 02_synthetic_data.sql ran.
-- =============================================================================

USE DATABASE CUSTOMER_360;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

INSERT INTO RAW.RAW_DOCUMENTS (DOCUMENT_ID, CUSTOMER_ID, DOCUMENT_TYPE, FILE_NAME, DOCUMENT_TEXT, FILE_SIZE_BYTES)
SELECT column1, column2, column3, column4, column5, LENGTH(column5)
FROM VALUES

-- ── Claim Forms (10 documents) ──────────────────────────────────────────────

(1, 1737747, 'Claim Form', 'claim_form_CLM-2024-00142.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00142
Policy Number: POL-00023
Customer Name: Fang Mahmoud
Customer ID: 1737747
Date Filed: 2024-08-15
Claim Type: Auto
Claim Amount: $8,500.00
Status: Open

Description:
Rear-end collision on Highway 101 during evening commute. The insured vehicle (2022 Honda Civic) sustained significant rear bumper and trunk damage. Police report filed (#PR-2024-08-4521). No injuries reported. Third-party vehicle also damaged. Awaiting repair estimates from two certified body shops.

Adjuster Notes:
Liability appears clear — third party at fault. Subrogation potential high. Recommend expedited processing.'),

(2, 4527636, 'Claim Form', 'claim_form_CLM-2024-00215.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00215
Policy Number: POL-00056
Customer Name: Alexander Abdullah
Customer ID: 4527636
Date Filed: 2024-09-03
Claim Type: Home
Claim Amount: $22,750.00
Status: InReview

Description:
Water damage from burst pipe in upstairs bathroom. Flooding affected master bedroom ceiling, hallway carpet, and ground-floor living room. Emergency plumber called same day. Temporary housing required for 5 days during remediation.

Adjuster Notes:
Cause confirmed as sudden pipe burst (covered peril). No evidence of gradual leak. Customer has filed supporting receipts for temporary accommodation ($1,200). Recommend approval with standard deductible.'),

(3, 4335629, 'Claim Form', 'claim_form_CLM-2024-00318.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00318
Policy Number: POL-00112
Customer Name: Alejandro Qureshi
Customer ID: 4335629
Date Filed: 2024-07-22
Claim Type: Medical
Claim Amount: $4,200.00
Status: Approved

Description:
Emergency room visit following workplace injury — laceration to left forearm requiring 12 stitches. Follow-up visit with orthopedic specialist confirmed no fracture. Physical therapy prescribed (6 sessions).

Adjuster Notes:
Medical records verified. All charges within usual and customary rates. Approved for full claim amount minus $500 deductible. Payment issued 2024-08-10.'),

(4, 1798364, 'Claim Form', 'claim_form_CLM-2024-00401.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00401
Policy Number: POL-00178
Customer Name: Mohammed Iyer
Customer ID: 1798364
Date Filed: 2024-10-01
Claim Type: Auto
Claim Amount: $3,100.00
Status: Open

Description:
Windshield and side mirror damaged by flying debris on Interstate 35 during severe thunderstorm. Dashboard camera footage available. Vehicle is a 2023 Ford Explorer. OEM replacement parts requested.

Adjuster Notes:
Comprehensive coverage applies. No deductible for windshield in this state. Side mirror replacement quoted at $850 (OEM). Straightforward claim.'),

(5, 3589459, 'Claim Form', 'claim_form_CLM-2024-00489.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00489
Policy Number: POL-00234
Customer Name: Ling Ito
Customer ID: 3589459
Date Filed: 2024-06-18
Claim Type: Theft
Claim Amount: $15,000.00
Status: Denied

Description:
Reported theft of personal electronics and jewelry from home while on vacation. Items claimed: laptop ($2,500), camera equipment ($4,000), jewelry ($8,500). Police report filed (#PR-2024-06-9012).

Adjuster Notes:
Investigation revealed no signs of forced entry. Security system was not armed at time of reported theft. Denied due to insufficient evidence and policy exclusion for unsecured premises.'),

(6, 4484529, 'Claim Form', 'claim_form_CLM-2024-00523.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00523
Policy Number: POL-00045
Customer Name: Aria Mehta
Customer ID: 4484529
Date Filed: 2024-11-10
Claim Type: Natural Disaster
Claim Amount: $45,000.00
Status: InReview

Description:
Roof and siding damage from Category 2 hurricane. Multiple roof shingles torn off, two windows broken, garage door dented beyond repair. Flooding in basement. Tree fell on backyard fence and deck.

Adjuster Notes:
Area declared federal disaster zone. High volume of claims in region. Field inspection scheduled for 2024-11-18. Prioritize processing.'),

(7, 3007226, 'Claim Form', 'claim_form_CLM-2024-00567.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00567
Policy Number: POL-00289
Customer Name: Divya Graham
Customer ID: 3007226
Date Filed: 2024-05-30
Claim Type: Medical
Claim Amount: $12,800.00
Status: Settled

Description:
Scheduled knee replacement surgery at hospital. Pre-authorization obtained (Auth #PA-2024-0442). Includes surgeon fee, anesthesia, hospital stay (3 nights), post-operative medications, and 8 weeks of physical therapy.

Adjuster Notes:
All pre-authorization requirements met. Surgery performed by in-network provider. Settled at $11,500 after network negotiation. Customer co-pay: $1,300. Closed.'),

(8, 1051727, 'Claim Form', 'claim_form_CLM-2024-00612.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00612
Policy Number: POL-00098
Customer Name: Jackson Suzuki
Customer ID: 1051727
Date Filed: 2024-09-25
Claim Type: Property Damage
Claim Amount: $6,750.00
Status: Approved

Description:
Fire damage to kitchen caused by electrical fault in dishwasher. Fire department responded and contained fire to kitchen area. Damage includes countertops, cabinets, appliances, and smoke damage to adjacent dining room.

Adjuster Notes:
Fire marshal report on file. No negligence. Coverage confirmed. Approved at $6,750. Depreciation waived per replacement cost endorsement.'),

(9, 3309161, 'Claim Form', 'claim_form_CLM-2024-00698.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00698
Policy Number: POL-00201
Customer Name: Alexander Hayes
Customer ID: 3309161
Date Filed: 2024-08-05
Claim Type: Auto
Claim Amount: $19,500.00
Status: InReview

Description:
Total loss — vehicle (2021 BMW 3 Series) struck by uninsured driver running red light. Airbags deployed, vehicle undrivable. Insured transported to ER, treated for minor whiplash and released.

Adjuster Notes:
Uninsured motorist coverage applies. Vehicle valued at $28,000 (KBB). Salvage value $8,500. Payout calculated at $19,500. Rental car authorized for 30 days.'),

(10, 2120504, 'Claim Form', 'claim_form_CLM-2024-00745.txt',
'INSURANCE CLAIM FORM
====================
Claim Number: CLM-2024-00745
Policy Number: POL-00315
Customer Name: Henry Kobayashi
Customer ID: 2120504
Date Filed: 2024-10-20
Claim Type: Home
Claim Amount: $9,200.00
Status: Open

Description:
Sewer backup caused flooding in finished basement. Affected areas include home office, rec room, and storage area. Personal property damaged includes computer equipment, books, and furniture.

Adjuster Notes:
Sewer backup endorsement confirmed on policy. Customer has documented inventory with photos and receipts. Mold remediation company engaged — estimate pending.'),

-- ── Policy Summaries (10 documents) ─────────────────────────────────────────

(11, 1737747, 'Policy Summary', 'policy_summary_POL-00023.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00023
Customer Name: Fang Mahmoud
Customer ID: 1737747
Policy Type: Auto
Effective Date: 2024-01-15
Expiration Date: 2025-01-15
Annual Premium: $1,850.00
Coverage Amount: $75,000.00
Deductible: $500.00
Status: Active
Risk Category: Low

Coverage Details:
- Liability: $50,000/$100,000 bodily injury, $50,000 property damage
- Collision: Actual cash value, $500 deductible
- Comprehensive: Actual cash value, $250 deductible
- Uninsured Motorist: $50,000/$100,000
- Medical Payments: $5,000 per person

Underwriting Notes:
Clean driving record (5+ years). Multi-policy discount applied. Loyalty discount: 15%.'),

(12, 4527636, 'Policy Summary', 'policy_summary_POL-00056.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00056
Customer Name: Alexander Abdullah
Customer ID: 4527636
Policy Type: Home
Effective Date: 2024-03-01
Expiration Date: 2025-03-01
Annual Premium: $2,400.00
Coverage Amount: $350,000.00
Deductible: $1,000.00
Status: Active
Risk Category: Medium

Coverage Details:
- Dwelling Coverage: $350,000 (replacement cost)
- Personal Property: $175,000
- Liability: $300,000
- Sewer Backup: $25,000 (endorsement)

Underwriting Notes:
Property built 2005, well-maintained. Security system installed (5% discount). Roof replaced 2020. No prior claims in 3 years.'),

(13, 4335629, 'Policy Summary', 'policy_summary_POL-00112.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00112
Customer Name: Alejandro Qureshi
Customer ID: 4335629
Policy Type: Health
Effective Date: 2024-01-01
Expiration Date: 2024-12-31
Annual Premium: $6,200.00
Coverage Amount: $500,000.00
Deductible: $2,000.00
Status: Active
Risk Category: Low

Coverage Details:
- In-Network Deductible: $2,000 individual / $4,000 family
- Coinsurance: 80/20 after deductible
- Out-of-Pocket Maximum: $6,500 individual
- Preventive Care: 100% covered

Underwriting Notes:
Non-smoker. No pre-existing conditions. Family plan (spouse + 2 dependents).'),

(14, 1798364, 'Policy Summary', 'policy_summary_POL-00178.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00178
Customer Name: Mohammed Iyer
Customer ID: 1798364
Policy Type: Auto
Effective Date: 2024-06-01
Expiration Date: 2025-06-01
Annual Premium: $2,100.00
Coverage Amount: $100,000.00
Deductible: $500.00
Status: Active
Risk Category: Medium

Coverage Details:
- Liability: $100,000/$300,000 bodily injury, $100,000 property damage
- Collision: $500 deductible
- Comprehensive: $500 deductible
- Roadside Assistance: Included

Underwriting Notes:
One minor at-fault accident in 2022. Vehicle: 2023 Ford Explorer. Good student discount for dependent driver.'),

(15, 3589459, 'Policy Summary', 'policy_summary_POL-00234.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00234
Customer Name: Ling Ito
Customer ID: 3589459
Policy Type: Home
Effective Date: 2024-04-15
Expiration Date: 2025-04-15
Annual Premium: $3,500.00
Coverage Amount: $500,000.00
Deductible: $2,500.00
Status: Active
Risk Category: High

Coverage Details:
- Dwelling Coverage: $500,000 (replacement cost)
- Personal Property: $250,000 (actual cash value)
- Liability: $500,000
- Hurricane Deductible: 2% of dwelling coverage
- Flood: Excluded (separate NFIP policy required)

Underwriting Notes:
Coastal property — elevated hurricane risk. Property built 2010 with hurricane straps. Two prior claims in 5 years. Higher deductible to offset premium.'),

(16, 4484529, 'Policy Summary', 'policy_summary_POL-00045.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00045
Customer Name: Aria Mehta
Customer ID: 4484529
Policy Type: Home
Effective Date: 2024-02-01
Expiration Date: 2025-02-01
Annual Premium: $2,800.00
Coverage Amount: $425,000.00
Deductible: $1,000.00
Status: Active
Risk Category: Medium

Coverage Details:
- Dwelling Coverage: $425,000 (replacement cost)
- Personal Property: $212,500
- Liability: $500,000 (umbrella eligible)
- Water Backup: $25,000

Underwriting Notes:
Long-tenure customer (8+ years). Property built 1998, renovated 2019. Bundled with auto policy (12% discount). Claims-free for 4 years prior to current claim.'),

(17, 3007226, 'Policy Summary', 'policy_summary_POL-00289.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00289
Customer Name: Divya Graham
Customer ID: 3007226
Policy Type: Health
Effective Date: 2024-01-01
Expiration Date: 2024-12-31
Annual Premium: $8,400.00
Coverage Amount: $1,000,000.00
Deductible: $1,500.00
Status: Active
Risk Category: Low

Coverage Details:
- In-Network Deductible: $1,500 individual / $3,000 family
- Coinsurance: 90/10 after deductible
- Out-of-Pocket Maximum: $4,000 individual
- Specialty Rx: 20% coinsurance

Underwriting Notes:
Premium plan. Non-smoker. Pre-existing: managed hypertension (controlled). Family plan.'),

(18, 1051727, 'Policy Summary', 'policy_summary_POL-00098.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00098
Customer Name: Jackson Suzuki
Customer ID: 1051727
Policy Type: Life
Effective Date: 2023-06-01
Expiration Date: 2043-06-01
Annual Premium: $1,200.00
Coverage Amount: $500,000.00
Deductible: $0.00
Status: Active
Risk Category: Low

Coverage Details:
- Type: 20-Year Level Term Life
- Death Benefit: $500,000
- Beneficiary: Spouse (100%)
- Conversion Option: Available until year 15
- Waiver of Premium: Included (disability rider)

Underwriting Notes:
Non-smoker, excellent health. Occupation: Software Engineer (preferred class).'),

(19, 3309161, 'Policy Summary', 'policy_summary_POL-00201.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00201
Customer Name: Alexander Hayes
Customer ID: 3309161
Policy Type: Auto
Effective Date: 2024-04-01
Expiration Date: 2025-04-01
Annual Premium: $2,600.00
Coverage Amount: $100,000.00
Deductible: $500.00
Status: Active
Risk Category: Medium

Coverage Details:
- Liability: $100,000/$300,000 bodily injury, $100,000 property damage
- Collision: $500 deductible
- Comprehensive: $250 deductible
- Gap Coverage: Included (leased vehicle)
- Rental Reimbursement: $75/day, 30-day max

Underwriting Notes:
Vehicle: 2021 BMW 3 Series (leased). Gap coverage required by lessor. Clean driving record. Urban area surcharge applied.'),

(20, 2120504, 'Policy Summary', 'policy_summary_POL-00315.txt',
'INSURANCE POLICY SUMMARY
=========================
Policy Number: POL-00315
Customer Name: Henry Kobayashi
Customer ID: 2120504
Policy Type: Home
Effective Date: 2024-05-01
Expiration Date: 2025-05-01
Annual Premium: $1,950.00
Coverage Amount: $300,000.00
Deductible: $1,000.00
Status: Active
Risk Category: Low

Coverage Details:
- Dwelling Coverage: $300,000 (replacement cost)
- Personal Property: $150,000
- Liability: $300,000
- Sewer Backup: $15,000 (endorsement)
- Home Office Equipment: $10,000 (rider)

Underwriting Notes:
Property built 2015, excellent condition. Smart home monitoring (7% discount). No prior claims. Bundled with auto policy (10% discount).')

;
