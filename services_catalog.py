"""Neural Cloud Enterprise's 22 official service lines — single source of truth.

Used by:
  - enrich.py       to classify every lead into a service and estimate its value
  - app.py/Settings  to let the user pick which services NCE currently offers
                     (an inactive service is excluded from classification and
                     from the combined keyword filters below)
  - sources/*.py     to build each source's default topic keywords, so a
                     "network engineer" job pulled from GoZambiaJobs and a
                     "network infrastructure" tender pulled from ZPPA land in
                     the same category.

Keywords are deliberately multi-word phrases, not bare short words/acronyms
(no bare "ai", "bi", "it", "os", "ui" — those are substrings of ordinary
words like "email", "build", "with", "cost", "quick" and produced real false
positives earlier in this project with "ict"/"gis"/"mis").
"""

SERVICES = {
    "custom_software": {
        "name": "Custom Software Development",
        "value_range": (15000, 100000),
        "keywords": [
            "custom software", "software development", "web application development",
            "business system", "internal platform", "enterprise software",
            "crm system", "erp system", "saas product", "saas platform",
            "workflow automation system", "customer portal", "self-service platform",
            "admin dashboard", "management platform", "api development",
            "system integration", "legacy system", "system modernization",
            "system modernisation", "hospital management system", "pharmacy management system",
            "claims platform", "call center system", "school management system",
            "university platform", "e-commerce platform", "marketplace platform",
            "logistics system", "fleet management system", "loan management system",
            "collections system", "survey platform", "business process management",
            "software developer", "software engineer", "web developer", "systems analyst",
            "database administrator",
        ],
    },
    "ai_automation": {
        "name": "AI Solutions & Intelligent Automation",
        "value_range": (10000, 80000),
        "keywords": [
            "artificial intelligence", "ai strategy", "ai chatbot", "chatbot development",
            "ai assistant", "ai copilot", "document intelligence", "ocr workflow",
            "optical character recognition", "ai customer support", "ai knowledge base",
            "retrieval augmented", "call center ai", "predictive analytics",
            "forecasting model", "recommendation engine", "workflow automation",
            "natural language processing", "voice ai", "conversational ai",
            "ai-powered", "ai-enabled", "machine learning", "generative ai",
            "ai decision support", "ai engineer", "machine learning engineer",
        ],
    },
    "data_analytics": {
        "name": "Data Analytics, BI & Research Services",
        "value_range": (8000, 55000),
        "keywords": [
            "data analysis", "business intelligence", "executive reporting",
            "management dashboard", "data visualization", "data visualisation",
            "kpi reporting", "performance reporting", "operational analytics",
            "customer analytics", "sales analytics", "financial analytics",
            "market research", "business research", "survey data analysis",
            "monitoring and evaluation", "m&e", "data cleaning", "data transformation",
            "data pipeline", "reporting automation", "decision-support reporting",
            "survey design", "kobo toolbox", "odk", "data collection system",
            "field data", "research data management", "data entry", "data validation",
            "baseline survey", "endline survey", "midline survey", "impact measurement",
            "impact assessment", "donor reporting", "program reporting", "community research",
            "statistician", "power bi", "tableau", "data analyst", "business intelligence analyst",
            "m&e officer", "research analyst", "geographic information system",
            "information communication technology",
        ],
    },
    "cloud_infrastructure": {
        "name": "Cloud, Hosting & Infrastructure Services",
        "value_range": (3000, 30000),
        "keywords": [
            "cloud architecture", "server setup", "cloud server", "vps hosting",
            "application hosting", "domain and dns", "dns support", "database hosting",
            "backup and recovery", "infrastructure monitoring", "linux server administration",
            "self-hosted platform", "email hosting", "web hosting", "infrastructure advisory",
            "cloud migration", "cloud deployment", "server administration",
            "systems administrator", "cloud engineer", "devops engineer", "linux administrator",
        ],
    },
    "voip_callcenter": {
        "name": "Call Center, VoIP & Communication Systems",
        "value_range": (10000, 70000),
        "keywords": [
            "call center system", "contact center", "vicidial", "pbx system",
            "voip platform", "agent dashboard", "call management system",
            "campaign management system", "call reporting", "softphone", "telephony",
            "ivr system", "call center crm", "collections call", "ai-enhanced call center",
            "call center agent", "telephony engineer",
        ],
    },
    "healthtech": {
        "name": "Healthcare & Pharmacy Technology Solutions",
        "value_range": (15000, 90000),
        "keywords": [
            "pharmacy management", "hospital management system", "clinic management system",
            "patient record", "electronic health record", "billing system for healthcare",
            "prescription and dispensing", "healthcare crm", "health reporting dashboard",
            "multi-branch healthcare", "patient communication system", "healthcare analytics",
            "pharmacy inventory", "pharmacy stock",
        ],
    },
    "insurtech": {
        "name": "Insurance Technology Solutions",
        "value_range": (20000, 120000),
        "keywords": [
            "insurance crm", "policy administration", "claims workflow",
            "claims processing system", "agent management platform", "premium collection",
            "claims analytics", "underwriting", "broker portal", "insurance call center",
            "digital insurance", "insurance onboarding", "insurtech", "insurance", "insurer",
            "reinsurance",
        ],
    },
    "automation_transformation": {
        "name": "Business Process Automation & Digital Transformation",
        "value_range": (8000, 60000),
        "keywords": [
            "process automation", "approval system", "leave management system",
            "hr workflow", "procurement system", "document approval system",
            "asset tracking system", "inventory tracking system", "finance operations workflow",
            "digital transformation", "internal admin system", "process mapping",
            "process digitization", "process digitisation", "business analyst", "process analyst",
        ],
    },
    "web_mobile_dev": {
        "name": "Web & Mobile App Development",
        "value_range": (5000, 45000),
        "keywords": [
            "website design", "website development", "landing page design",
            "e-commerce website", "cms website", "website maintenance",
            "website optimization", "website optimisation", "android app development",
            "ios app development", "cross-platform app", "mobile app development",
            "mobile data collection app", "booking app", "marketplace app",
            "mobile developer", "app developer",
        ],
    },
    "design_ux": {
        "name": "UI/UX Design & Product Experience",
        "value_range": (3000, 25000),
        "keywords": [
            "ui/ux design", "user interface design", "user experience design",
            "product wireframing", "prototyping", "dashboard design", "design system",
            "front-end redesign", "conversion-focused design", "user journey design",
            "design cleanup",
        ],
    },
    "networking_connectivity": {
        "name": "Networking, Connectivity & Managed IT Solutions",
        "value_range": (5000, 40000),
        "keywords": [
            "network design", "office wi-fi", "lan deployment", "firewall setup",
            "access point setup", "connectivity consulting", "mesh network",
            "campus network", "isp support", "telecom support system",
            "rural connectivity", "business internet solution", "managed it services",
            "it support services", "network engineer", "network administrator",
        ],
    },
    "training_support": {
        "name": "Training, Support & Capacity Building",
        "value_range": (2000, 18000),
        "keywords": [
            "staff onboarding", "user training", "admin training", "data literacy training",
            "digital operations training", "technical documentation", "sop development",
            "support retainer", "helpdesk support", "capacity building", "product adoption support",
            "trainer", "training officer",
        ],
    },
    "contact_centre_cx": {
        "name": "Contact Centre and Customer Experience",
        "value_range": (15000, 150000),
        "keywords": [
            "inbound customer support", "outbound call centre", "outbound call center",
            "customer acquisition", "customer retention", "win-back campaign",
            "customer verification call", "welcome call campaign", "helpdesk operations",
            "complaint management", "telemarketing", "contact centre operations",
            "contact center operations", "24/7 contact centre", "24/7 contact center",
            "customer experience", "customer care",
        ],
    },
    "bpo": {
        "name": "Business Process Outsourcing",
        "value_range": (15000, 150000),
        "keywords": [
            "back-office processing", "back office processing", "merchant onboarding",
            "know your customer", "kyc verification", "data entry and validation",
            "data cleansing", "transaction processing", "application processing",
            "dispute management", "case management", "document digitisation",
            "document digitization", "administrative process outsourcing",
            "business process outsourcing",
        ],
    },
    "sales_field_ops": {
        "name": "Sales, Trade and Field Operations",
        "value_range": (10000, 100000),
        "keywords": [
            "merchant acquisition", "agent acquisition", "mass-market onboarding",
            "field sales force", "territory management", "route management",
            "merchant activation", "merchant reactivation", "retail audit",
            "outlet verification", "branding audit", "visibility audit",
            "liquidity monitoring", "field compliance", "mystery shopping",
            "market mapping", "census exercise",
        ],
    },
    "research_insights": {
        "name": "Research and Customer Insights",
        "value_range": (5000, 50000),
        "keywords": [
            "market research", "customer satisfaction survey", "net promoter score",
            "computer-assisted telephone interviewing", "computer-assisted personal interviewing",
            "qualitative research", "quantitative research", "customer sentiment analysis",
            "closed-loop customer recovery", "competitor intelligence", "market intelligence",
        ],
    },
    "data_mis": {
        "name": "Data Analytics and MIS",
        "value_range": (5000, 40000),
        "keywords": [
            "real-time performance reporting", "campaign analytics", "workforce reporting",
            "productivity reporting", "sales conversion analysis", "customer segmentation",
            "data reconciliation", "data quality assurance", "executive reports",
            "management reports", "operational forecasting", "business intelligence dashboard",
        ],
    },
    "debt_collection": {
        "name": "Debt Collection and Revenue Recovery",
        "value_range": (8000, 80000),
        "keywords": [
            "debt collection", "early-stage collections", "payment reminder",
            "arrears follow-up", "debt rehabilitation", "field collections",
            "promise-to-pay", "recovery performance reporting", "revenue recovery",
        ],
    },
    "payroll_workforce": {
        "name": "Payroll and Workforce Administration",
        "value_range": (5000, 45000),
        "keywords": [
            "outsourced payroll", "attendance management", "timesheet management",
            "contractor payment administration", "field-force payment", "commission calculation",
            "incentive calculation", "payroll analytics", "employee records administration",
            "statutory payroll",
        ],
    },
    "tech_digital_solutions": {
        "name": "Technology and Digital Solutions",
        "value_range": (10000, 90000),
        "keywords": [
            "customer relationship management system", "call centre dialler", "call center dialer",
            "workflow platform", "case-management platform", "bulk payment solution",
            "digital onboarding system", "business workspace platform", "learning management system",
            "expo academy", "automation of manual business processes",
        ],
    },
    "it_infrastructure_support": {
        "name": "IT Infrastructure and Support",
        "value_range": (5000, 50000),
        "keywords": [
            "network management", "server management", "contact centre technology deployment",
            "hardware support", "software support", "user access administration",
            "security administration", "it asset management", "it inventory management",
            "system troubleshooting", "firewall management", "endpoint security management",
        ],
    },
    "data_protection_compliance": {
        "name": "Data Protection, Quality and Compliance Support",
        "value_range": (5000, 40000),
        "keywords": [
            "data privacy implementation", "information security controls",
            "quality assurance call monitoring", "call monitoring", "process audit",
            "regulatory compliance support", "operational compliance support",
            "secure data handling", "standard operating procedure development",
            "sop development",
        ],
    },
}

ALL_KEYS = list(SERVICES.keys())


def active_keys(settings: dict) -> list[str]:
    """Which service keys the user currently wants leads classified/filtered against.

    Defaults to all 22 if unset, empty, or every listed key is unrecognized
    (e.g. stale keys from a renamed service) — never silently classifies
    against an empty set.
    """
    raw = (settings or {}).get("active_services", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = [k for k in keys if k in SERVICES]
    return valid or ALL_KEYS


def combined_keywords(keys=None) -> list[str]:
    """Flat, de-duplicated keyword list across the given (or all) service keys."""
    keys = keys or ALL_KEYS
    seen = []
    for k in keys:
        svc = SERVICES.get(k)
        if not svc:
            continue
        for kw in svc["keywords"]:
            if kw not in seen:
                seen.append(kw)
    return seen
