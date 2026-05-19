# corpus.py

DOCUMENTS = [
    {
        "id": "hr-pto-001",
        "title": "PTO & Leave Policy",
        "content": """
Full-time employees accrue 15 days of paid time off (PTO) per calendar year.
PTO accrual begins on the first day of employment. Unused PTO may be carried
over up to a maximum of 5 days into the following year. Employees must request
PTO at least 3 business days in advance for absences of 3 days or more.
Sick leave is separate from PTO: employees receive 10 sick days per year which
do not carry over. Parental leave is 12 weeks fully paid for primary caregivers
and 4 weeks fully paid for secondary caregivers.
        """.strip()
    },
    {
        "id": "eng-deploy-001",
        "title": "Production Deployment Runbook",
        "content": """
All production deployments require a ticket in Linear with the 'deploy' label.
Deployments are permitted Monday through Thursday between 10am and 3pm EST only.
No deployments on Fridays or the day before a company holiday. Every deployment
must be reviewed and approved by at least one senior engineer who is not the
author. After merging, the deploying engineer must monitor the Datadog dashboard
for 30 minutes and confirm no error rate spike before closing the ticket.
Rollback procedure: run 'make rollback ENV=prod' from the repo root. This
reverts to the previous container image. Page the on-call engineer if rollback
does not stabilize error rates within 10 minutes.
        """.strip()
    },
    {
        "id": "eng-oncall-001",
        "title": "On-Call Rotation Guide",
        "content": """
The engineering on-call rotation runs weekly, Sunday to Sunday. The primary
on-call engineer is expected to respond to PagerDuty alerts within 5 minutes
during business hours (9am-6pm local time) and within 15 minutes outside
business hours. A secondary on-call engineer serves as backup and must be
reachable at all times. On-call compensation is $200 per week for primary and
$100 per week for secondary. Engineers are not expected to carry an on-call
shift more than once every 6 weeks. After any major incident, a blameless
post-mortem must be filed within 48 hours.
        """.strip()
    },
    {
        "id": "product-api-001",
        "title": "Public API Rate Limits",
        "content": """
The public REST API enforces rate limits per API key. Free tier accounts are
limited to 100 requests per minute and 10,000 requests per day. Pro tier
accounts are limited to 1,000 requests per minute and 500,000 requests per day.
Enterprise accounts have custom rate limits negotiated in their contract.
Rate limit headers are returned on every response: X-RateLimit-Limit,
X-RateLimit-Remaining, and X-RateLimit-Reset. When the limit is exceeded, the
API returns HTTP 429 with a Retry-After header indicating seconds to wait.
Burst requests up to 2x the per-minute limit are permitted for up to 10 seconds.
        """.strip()
    },
    {
        "id": "product-pricing-001",
        "title": "Pricing & Plans",
        "content": """
We offer three plans: Free, Pro, and Enterprise. The Free plan costs $0/month
and includes 1 user seat, 5GB storage, and basic API access. The Pro plan costs
$49/month per seat and includes unlimited users, 100GB storage, priority support,
and advanced API access. The Enterprise plan has custom pricing and includes
SSO, audit logs, dedicated support, SLA guarantees, and custom integrations.
Annual billing provides a 20% discount on Pro plans. All plans include a 14-day
free trial. Downgrading from Pro to Free results in immediate loss of Pro features.
        """.strip()
    },
    {
        "id": "security-001",
        "title": "Security & Compliance",
        "content": """
All employee laptops must have full-disk encryption enabled and be enrolled in
our MDM solution (Jamf for Mac, Intune for Windows). Employees must use the
company VPN when accessing internal resources from outside the office. Passwords
must be at least 16 characters and stored in the company-approved password
manager (1Password). Multi-factor authentication (MFA) is mandatory for all
company accounts. Security incidents must be reported to security@company.com
within 1 hour of discovery. The company undergoes annual SOC 2 Type II audits.
Employee access is reviewed quarterly and revoked within 24 hours of offboarding.
        """.strip()
    },
]