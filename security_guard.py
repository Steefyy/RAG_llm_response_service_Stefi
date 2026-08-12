import re

# Cuvinte cheie folosite frecvent in atacurile de tip Prompt Injection / Jailbreak / System Extraction
SUSPICIOUS_KEYWORDS = [
    # Română - Ignorare reguli & Prompt Injection
    "ignora regulile", "ignora instructiunile", "ignoră regulile", "ignoră instrucțiunile",
    "regulile anterioare", "instructiunile anterioare", "instrucțiunile anterioare",
    "acum esti un", "acum ești un", "noua ta instructiune", "noua ta instrucțiune",
    "ignora restrictiile", "ignora restricțiile", "fara filtre", "fără filtre",
    "mod dezvoltator", "mod depanare", "fără restricții", "fara restrictii",
    
    # Engleză - Core Jailbreak & Persona Takeover
    "forget instructions", "forget rules", "ignore system prompt", "jailbreak prompt",
    "forget about", "ignore the above", "you are now a", "bypass filters", "prompt injection",
    "dan mode", "developer mode", "do anything now", "unrestricted mode", "debug mode",
    "override system", "disregard previous", "disregard instructions", "system override",
    "pretend you are", "act as a", "act as if", "roleplay as",
    
    # Tentative de extragere a Prompt-ului de Sistem (System Leakage)
    "show system prompt", "print system prompt", "what is your system prompt",
    "arata instructiunile", "arată instrucțiunile", "spune-mi regulile",
    "arata-mi promptul", "arată-mi promptul", "reveal instructions", "repeat the system prompt",
    
    # Tentative de injection cu script-uri sau comenzi
    "<script>", "eval(", "exec(", "import os", "system(", "sudo "
]

# Expresii regulate pentru a prinde tentative de manipulare a promptului (imperative de sistem)
SUSPICIOUS_PATTERNS = [
    # Imperative de ignorare
    r"(ignora|ignoră|forget|override|delete|reset|disregard)\s+(toate|all|the)?\s*(instructiunile|instrucțiunile|regulile|rules|prompt|instructions)",
    
    # Schimbare de rol / Persona takeover
    r"(you are now|acum esti|acum ești|de acum vei fi|act as|pretend to be|comportă-te ca|comporta-te ca)\s+(a|an|un|o)?\s*(developer|translator|calculator|hacker|altceva|poem|poetry|robot|asistent|pirat|evil)",
    
    # Extragere a promptului de sistem
    r"(arată|arata|show|print|display|reveal|expose|spune)\s+(mi|-mi)?\s*(sistem|system|prompt|regulile|instructions|instructiunile|instrucțiunile)",
    
    # Restriction Bypasses
    r"(ignore|omite)\s+(the|toate)?\s*(context|sursele|restricțiile|restrictiile)",
    
    # Raspuns forțat la format fix
    r"(raspunzi|răspunzi)\s+doar\s+cu",
    r"answer\s+only\s+with"
]

class GuardStatus:
    def __init__(self, safe: bool, reason: str = ""):
        self.safe = safe
        self.reason = reason

def valideaza_intrebare(intrebare: str) -> GuardStatus:
    """
    Verifica daca intrebarea studentului contine
    tentative de Prompt Injection / Jailbreak, extractie de prompt sau manipulare a instructiunilor.
    """
    if not intrebare or not intrebare.strip():
        return GuardStatus(safe=True)

    text_lower = intrebare.lower().strip()

    # 1. Verificare cuvinte suspecte (Blacklist)
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in text_lower:
            return GuardStatus(
                safe=False, 
                reason=f"Detectat cuvânt cheie suspect sau tentativă de Prompt Injection: '{keyword}'"
            )

    # 2. Verificare pattern-uri Regex complexe
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text_lower):
            return GuardStatus(
                safe=False,
                reason="Detectat tipar de instrucțiuni imperative care încearcă să ignore sau să extragă regulile de sistem."
            )

    # 3. Verificăm lungimea extremă a mesajului (prevenire buffer/payload attack)
    if len(intrebare) > 1000:
        return GuardStatus(
            safe=False,
            reason="Mesaj prea lung (peste 1000 caractere). Posibilă tentativă de încărcare a unui payload masiv de jailbreak."
        )

    return GuardStatus(safe=True)
