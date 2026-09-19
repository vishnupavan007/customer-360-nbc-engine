INSERT INTO CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS
WITH tran_offset AS (SELECT COALESCE(MAX(TRANSCRIPT_ID),0) AS max_id FROM CUSTOMER_360.RAW.RAW_CALL_TRANSCRIPTS),
reasons AS (
    SELECT column1 AS reason FROM VALUES
    ('Policy Renewal'),('Claim Status'),('Premium Dispute'),('Payment Issue'),
    ('Complaint'),('New Policy Inquiry'),('Cancellation Request'),('Loan Payment Question'),
    ('Cyber Claim'),('Flood Claim')
),
transcripts AS (
    SELECT column1 AS rm, column2 AS txt FROM VALUES
    ('Policy Renewal', 'Agent: Thank you for calling SecureLife. I am Sarah. How can I help?
Customer: My auto policy renewal came and the premium went up 15 percent.
Agent: Let me pull up your account. The increase is due to a rate adjustment and one claim last year. I can apply a multi-policy bundle discount bringing it down 8 percent since you have home insurance with us.
Customer: That would help. Please apply it.
Agent: Done. Your updated renewal arrives in 5 business days.
Customer: Thank you.
Agent: Thank you for being a valued customer.'),
    ('Claim Status', 'Agent: SecureLife claims, this is Michael. How may I help?
Customer: I filed a home water damage claim three weeks ago and have not heard back. This is unacceptable.
Agent: I sincerely apologize. Claim CLM-78234 was waiting for additional photos. The email must have gone to spam. I am escalating this to priority status and an adjuster will call you within 24 hours. I am also applying a goodwill credit.
Customer: Please just get it resolved.
Agent: You have my word.'),
    ('Premium Dispute', 'Agent: SecureLife, this is Jessica. How can I help?
Customer: My health insurance premium went up 25 percent and I cannot afford it. I have been with you 8 years.
Agent: I value your loyalty. I can apply a 5 percent loyalty discount and move you to our Silver tier, which combined brings your premium below your previous rate.
Customer: That sounds good. Switch me over.
Agent: Done. Confirmation arrives in 3 business days.'),
    ('Payment Issue', 'Agent: SecureLife, I am Amanda. How can I help?
Customer: My insurance payment was charged twice this month. It caused my account to overdraft.
Agent: I am very sorry. I see the duplicate charge. I am processing an immediate refund and submitting a 35 dollar reimbursement for your overdraft fee. Please email your bank statement to billing@securelife.com with your policy number.
Customer: Thank you for acting quickly.
Agent: Of course. Again I apologize for the inconvenience.'),
    ('Complaint', 'Agent: SecureLife, this is Tom. How may I help?
Customer: I am filing a formal complaint. My home claim was denied for lack of maintenance but the pipe was inside the wall.
Agent: That is a valid point. I am escalating this to our senior claims review team. A second independent adjuster will also review the damage. You should hear from a claims manager within 48 hours.
Customer: I expect a fair outcome.
Agent: Absolutely. I will personally follow up next week.'),
    ('New Policy Inquiry', 'Agent: SecureLife, this is Robert. How may I help?
Customer: I just bought a home and need homeowners insurance before closing next week.
Agent: Congratulations. For a 2200 square foot home built in 1998 with a new roof, I can offer 375000 in coverage at 98 dollars per month with a 2500 deductible. Bundle with auto for an additional 12 percent savings.
Customer: Let us do the bundle.
Agent: Excellent. I will set both up today.'),
    ('Cancellation Request', 'Agent: SecureLife, this is Kelly. How can I help?
Customer: I want to cancel my auto policy. Another company offered me 89 dollars versus your 142.
Agent: I can apply a safe driver discount and a defensive driving discount you qualified for but never received. That brings you to 96 dollars. Our claims satisfaction is also significantly higher than competitors.
Customer: Let me think about it and call back.
Agent: Of course. The discounts are noted on your account and ready to apply.'),
    ('Loan Payment Question', 'Agent: SecureLife Financial, this is Maria. How can I help?
Customer: I want to pay 500 extra per month toward my personal loan principal. Will there be penalties?
Agent: No prepayment penalties at all. With your current balance at 6.5 percent over 36 months, that extra 500 saves you 1850 in interest and cuts 14 months off your term.
Customer: Perfect, set up automatic extra payments please.
Agent: Done. The 500 will draft with your regular payment each month.'),
    ('Cyber Claim', 'Agent: SecureLife cyber specialist Jennifer speaking. How can I help?
Customer: We were hit by ransomware last night. Everything is encrypted. We have cyber insurance.
Agent: Do not pay the ransom without consulting our incident response team. I see your policy with 1 million in ransomware coverage. I am connecting you to our 24 hour cyber response hotline. Isolate affected machines if possible. Our team will also assess your breach notification obligations.
Customer: Thank you, this is terrifying.
Agent: That is exactly what your coverage is for. Please hold while I connect you.'),
    ('Flood Claim', 'Agent: SecureLife claims, this is Alex. How may I help?
Customer: We had 18 inches of water in our home from the river overflowing. Everything on the first floor is destroyed.
Agent: Are you and your family safe?
Customer: Yes we are in a hotel.
Agent: Good. Your policy covers up to 350000 for the dwelling and 75000 for contents. Hotel and meal costs are also covered under additional living expenses up to 36 months. Document everything with photos before cleanup. An emergency adjuster will be there within 4 to 6 hours.
Customer: That is a relief. Thank you.
Agent: We are going to work through this together. I will check in tomorrow.')
)
SELECT
    o.max_id + ROW_NUMBER() OVER (ORDER BY RANDOM()) AS TRANSCRIPT_ID,
    c.CUSTOMER_ID,
    NULL AS INTERACTION_ID,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS CALL_DATE,
    UNIFORM(120, 1800, RANDOM()) AS DURATION_SECONDS,
    'AGT-' || LPAD(UNIFORM(100, 999, RANDOM())::VARCHAR, 3, '0') AS AGENT_ID,
    CASE MOD(UNIFORM(1,10,RANDOM()),10)
        WHEN 0 THEN 'Sarah Mitchell' WHEN 1 THEN 'Michael Torres'
        WHEN 2 THEN 'Jessica Chen'   WHEN 3 THEN 'David Patel'
        WHEN 4 THEN 'Amanda Rodriguez' WHEN 5 THEN 'Robert Kim'
        WHEN 6 THEN 'Kelly Johnson'  WHEN 7 THEN 'Tom Wilson'
        WHEN 8 THEN 'Jennifer Park'  ELSE 'Alex Nguyen'
    END AS AGENT_NAME,
    t.txt AS TRANSCRIPT_TEXT,
    r.reason AS CALL_REASON,
    DATEADD('hour', -UNIFORM(1, 17520, RANDOM()), CURRENT_TIMESTAMP()) AS CREATED_AT
FROM CUSTOMER_360.RAW.RAW_CUSTOMERS c
CROSS JOIN reasons r
CROSS JOIN transcripts t
CROSS JOIN tran_offset o
WHERE r.reason = t.rm
ORDER BY RANDOM()
LIMIT 735
