# evals/dataset.py

TEST_CASES = [
    # -----------------------------------------------------------------------
    # Answerable questions — agent must retrieve and answer correctly
    # -----------------------------------------------------------------------
    {
        "id": "pto-001",
        "question": "How many PTO days do full-time employees get per year?",
        "expected_sources": ["PTO & Leave Policy"],
        "reference_answer": "Full-time employees accrue 15 days of paid time off per calendar year.",
        "answerable": True,
    },
    {
        "id": "pto-002",
        "question": "How many sick days do employees get?",
        "expected_sources": ["PTO & Leave Policy"],
        "reference_answer": "Employees receive 10 sick days per year which do not carry over.",
        "answerable": True,
    },
    {
        "id": "pto-003",
        "question": "How much parental leave does a primary caregiver get?",
        "expected_sources": ["PTO & Leave Policy"],
        "reference_answer": "Primary caregivers receive 12 weeks of fully paid parental leave.",
        "answerable": True,
    },
    {
        "id": "deploy-001",
        "question": "Can I deploy on a Friday?",
        "expected_sources": ["Production Deployment Runbook"],
        "reference_answer": "No. Deployments are only permitted Monday through Thursday between 10am and 3pm EST.",
        "answerable": True,
    },
    {
        "id": "deploy-002",
        "question": "What is the rollback procedure for a bad deployment?",
        "expected_sources": ["Production Deployment Runbook"],
        "reference_answer": "Run 'make rollback ENV=prod' from the repo root. Page the on-call engineer if error rates do not stabilize within 10 minutes.",
        "answerable": True,
    },
    {
        "id": "deploy-003",
        "question": "How long must an engineer monitor Datadog after a deployment?",
        "expected_sources": ["Production Deployment Runbook"],
        "reference_answer": "The deploying engineer must monitor the Datadog dashboard for 30 minutes after merging.",
        "answerable": True,
    },
    {
        "id": "oncall-001",
        "question": "What is the on-call compensation for the primary engineer?",
        "expected_sources": ["On-Call Rotation Guide"],
        "reference_answer": "The primary on-call engineer receives $200 per week compensation.",
        "answerable": True,
    },
    {
        "id": "api-001",
        "question": "What HTTP status code is returned when the API rate limit is exceeded?",
        "expected_sources": ["Public API Rate Limits"],
        "reference_answer": "The API returns HTTP 429 with a Retry-After header.",
        "answerable": True,
    },
    {
        "id": "security-001",
        "question": "What is the minimum password length required?",
        "expected_sources": ["Security & Compliance"],
        "reference_answer": "Passwords must be at least 16 characters long.",
        "answerable": True,
    },
    {
        "id": "pricing-001",
        "question": "How much does the Pro plan cost per month?",
        "expected_sources": ["Pricing & Plans"],
        "reference_answer": "The Pro plan costs $49 per month per seat.",
        "answerable": True,
    },

    # -----------------------------------------------------------------------
    # Unanswerable questions — agent must abstain correctly
    # -----------------------------------------------------------------------
    {
        "id": "unanswerable-001",
        "question": "What is the company's annual revenue?",
        "expected_sources": [],
        "reference_answer": None,
        "answerable": False,
    },
    {
        "id": "unanswerable-002",
        "question": "Who is the CEO of the company?",
        "expected_sources": [],
        "reference_answer": None,
        "answerable": False,
    },
    {
        "id": "unanswerable-003",
        "question": "What is the company's office address?",
        "expected_sources": [],
        "reference_answer": None,
        "answerable": False,
    },
]