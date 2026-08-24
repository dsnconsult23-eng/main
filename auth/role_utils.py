ALLOWED_ROLES = {
    "admin",
    "users_create",
    "aso_reports",
    "provizia",
    "ponuda",
    "matematicka_rezerva",
    "reo",
    "report_udel",
    "finansii",
    "finansiski_izvestai",
    "finance",
    "izvestuvanja",
    "aml",
    "mesh",
    "claim_notify",
    "kolektivno_uu",
    "report_fakturi",
    "kontrola_polisi",
    "promena_premija",
    "sms_log",
}

ROLE_OPTIONS = [
    ("admin", "admin - сите страници"),
    ("users_create", "креирање и уредување корисници"),
    ("aso_reports", "АСО извештаи"),
    ("provizia", "Провизија"),
    ("ponuda", "Импорт на понуда"),
    ("matematicka_rezerva", "Математичка резерва"),
    ("reo", "REO"),
    ("report_udel", "Преглед на удели"),
    ("finansii", "Финансии - салдирање"),
    ("finansiski_izvestai", "Финансиски извештаи"),
    ("aml", "AML"),
    ("izvestuvanja", "Известувања"),
    ("finance", "finance - финансии пакет"),
    ("mesh", "Mesh интеграција"),
    ("claim_notify", "Claim notify - поставки за известување на штети"),
    ("kolektivno_uu", "Колективно УУ - усогласување на уплати"),
    ("report_fakturi", "Преглед на фактури"),
    ("kontrola_polisi", "Контрола на полиси - откуп/капитализација/фактури"),
    ("promena_premija", "Промена на премија на фактура Колективно"),
    ("sms_log", "SMS известувања - лог и извоз"),
]


def normalize_roles(role_value):
    if isinstance(role_value, (list, tuple, set)):
        raw_roles = role_value
    else:
        raw_roles = str(role_value or "").split(",")

    roles = []
    for role in raw_roles:
        normalized = str(role).strip().lower()
        if normalized and normalized not in roles:
            roles.append(normalized)
    return roles


def has_any_role(user, *role_names):
    roles = normalize_roles(user.get("roles") or user.get("role"))
    return "admin" in roles or any(role_name in roles for role_name in role_names)
