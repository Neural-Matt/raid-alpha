"""Neural Cloud Enterprise's 12 official service lines — single source of truth.

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
}

ALL_KEYS = list(SERVICES.keys())


def active_keys(settings: dict) -> list[str]:
    """Which service keys the user currently wants leads classified/filtered against.

    Defaults to all 12 if unset, empty, or every listed key is unrecognized
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
