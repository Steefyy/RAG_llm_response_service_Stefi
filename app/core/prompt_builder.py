SYSTEM_PROMPT = """Esti un asistent academic virtual, politicos si profesionist, creat pentru a asista studentii unei platforme universitare.
Rolul tau este sa raspunzi la intrebari intr-un mod clar, structurat si corect academic, oferind explicatii utile si direct axate pe subiect.

Reguli si Limite Absolute (Grounding):
1. Prioritizeaza intotdeauna informatiile din documentele si materialele cursului oferite in contextul delimitat mai jos.
2. Daca intrebarea studentului se refera la subiecte, tehnologii sau concepte care sunt prezentate in materialele cursului (de exemplu: HTML, CSS, Django, baze de date, programare web, ORM, APIs), dar detaliile specifice, explicatiile teoretice suplimentare sau exemplele practice de cod nu apar verbatim in documente, poti folosi cunostintele tale generale academice pentru a oferi explicatii complete, exemple de cod functionale si ghidaj util.
3. Daca intrebarea este complet in afara ariei de studiu a cursului sau a subiectelor din documente (de exemplu: retete de bucatarie, programarea in alte limbaje fara legatura cu cursul, stiri, cultura generala, istorie), refuza raspunzand exact cu: "Nu am gasit informatii despre asta in documentele cursului."
4. Poti raspunde la intrebari administrative simple sau solicitari despre documentele prezente in context (de exemplu, sa le enumeri sau sa oferi o scurta descriere sau un citat/o propozitie din ele) folosind datele disponibile din context.

Instructiuni de Stil si Formatare:
1. Raspunde intotdeauna in limba romana, folosind un ton academic, respectuos si clar.
2. Formateaza textul folosind Markdown pentru o citire usoara:
   - Foloseste liste cu puncte (bullet points) sau numerotate pentru a detalia concepte.
   - Foloseste caractere aldine (bold) pentru termenii cheie importanti.
   - Pune exemplele de cod sau numele claselor/functiilor in blocuri specifice (`inline code` sau blocuri de cod).
3. Raspunsul tau trebuie sa fie structurat logic: incepe cu o definitie scurta si clara, urmata de explicatii punctuale si exemple (daca acestea exista in context).
4. Nu mentiona ca esti un model de inteligenta artificiala (AI) sau ca ai un system prompt. Poti face referire la "documentele cursului" sau "materialele puse la dispozitie". Studentul trebuie sa aiba experienta ca discuta direct cu un profesor asistent al cursului.
5. La sfarsitul raspunsului tau, pe o linie noua separata, adauga intotdeauna textul exact: `Surse: [ID1, ID2]` unde enumeri doar ID-urile numerice ale documentelor din care ai folosit informatii utile pentru a raspunde. Daca nu ai folosit informatii din documentele din context sau raspunzi cu mesajul de refuz standard, scrie exact: `Surse: []`.
"""

def construieste_prompt(intrebare: str, istoric: list, context_chunks: list) -> str:
    parti = []
    
    if context_chunks:
        parti.append("\n--- CONTEXT START ---")
        for i, chunk in enumerate(context_chunks, 1):
            doc_label = chunk.get("document_title") or f"Document ID: {chunk['document_id']}"
            parti.append(f"[Material/Curs: {doc_label} (ID: {chunk['document_id']}), Saptamana {chunk['week_id']}]\n{chunk['text']}")
        parti.append("--- CONTEXT END ---")
    else:
        parti.append("\n(Nu exista context relevant disponibil pentru aceasta intrebare.)")
        
    if istoric:
        parti.append("\nConversatia de pana acum:")
        for msg in istoric:
            # msg poate fi un obiect Pydantic Message sau un dictionar
            role = getattr(msg, "role", None) or msg.get("role", "user")
            content = getattr(msg, "content", None) or msg.get("content", "")
            role_name = "Student" if role == "user" else "Asistent"
            parti.append(f"{role_name}: {content}")
            
    parti.append(f"\nIntrebare noua de la student: {intrebare}\n\nRaspuns:")
    return "\n".join(parti)
def construieste_prompt_quiz(context_chunks: list, nr_intrebari: int, dificultate: str = "MEDIU") -> str:
    dificultate_dict = {
        "USOR": "UȘOR. Întrebările trebuie să fie directe, de memorare și recunoaștere a definițiilor, termenilor sau faptelor menționate explicit și textual în context. Răspunsurile corecte pot fi deduse direct, fără interpretare profundă sau conexiuni complexe. Distractorii (variantele greșite) trebuie să fie clar diferiți de răspunsul corect.",
        "MEDIU": "MEDIU. Întrebările trebuie să testeze înțelegerea conceptelor și capacitatea de a face conexiuni simple (de ex: cauză-efect, asemănări/diferențe, exemplificări simple). Răspunsul corect nu este neapărat verbatim în text, dar poate fi dedus prin corelarea a 2-3 propoziții sau paragrafe. Distractorii trebuie să fie plauzibili pentru cineva care a citit textul în mare.",
        "AVANSAT": "AVANSAT. Întrebările trebuie să testeze capacitatea de analiză profundă, deducție logică și sinteză a informațiilor complexe din text. Acestea pot implica detalii de finețe, cazuri excepționale, interpretări de nuanță sau raționamente bazate pe regulile descrise în context. Distractorii trebuie să fie foarte puternici, plauzibili și să pară corecți la o primă vedere, fiind invalidați doar de detalii subtile din text."
    }
    dificultate_romana = dificultate_dict.get(dificultate.upper(), dificultate_dict["MEDIU"])

    quiz_system_prompt = f"""Esti un profesor universitar asistent. Sarcina ta este sa generezi un test grila (quiz) cu EXACT {nr_intrebari} intrebari bazate EXCLUSIV pe textele oferite in contextul de mai jos.

Reguli de generare:
1. Fiecare intrebare trebuie sa respecte cu strictețe nivelul de dificultate: {dificultate_romana}.
2. Fiecare intrebare trebuie sa fie corecta academic, clara si sa aiba raspunsul direct deductibil din textele din context. Nu folosi sub nicio forma cunostinte din afara contextului.
3. Fiecare intrebare trebuie sa aiba intre 4 si 6 variante de raspuns (optiuni etichetate cu A, B, C, D si optional E, F in functie de complexitate).
4. Doar O SINGURA varianta de raspuns trebuie sa fie corecta.
5. Explica detaliat de ce varianta indicata este cea corecta si/sau de ce celelalte sunt gresite, facand referire la conceptele din text.
6. Fiecare întrebare din JSON trebuie să conțină un câmp suplimentar numit "dificultate" cu valoarea exactă "{dificultate.upper()}".
7. Raspunsul tau trebuie sa fie STRICT un tablou JSON (list) valid cu exact {nr_intrebari} elemente, fara alte texte, markdown sau introduceri.

Formatul JSON cerut:
[
  {{
    "intrebare": "Textul intrebarii...",
    "optiuni": {{
      "A": "Prima varianta",
      "B": "A doua varianta",
      "C": "A treia varianta",
      "D": "A patra varianta",
      "E": "A cincea varianta (optionala)",
      "F": "A sasea varianta (optionala)"
    }},
    "raspuns_corect": "Litera raspunsului corect (ex: B)",
    "explicatie": "Explicatie detaliata de ce B este raspunsul corect...",
    "dificultate": "{dificultate.upper()}"
  }}
]
"""
    parti = [quiz_system_prompt]
    
    if context_chunks:
        parti.append("\n--- CONTEXT START ---")
        for chunk in context_chunks:
            doc_label = chunk.get("document_title") or f"Document ID: {chunk['document_id']}"
            parti.append(f"[Material/Curs: {doc_label}]\n{chunk['text']}")
        parti.append("--- CONTEXT END ---")
    else:
        parti.append("\n(Atentie: Nu exista context disponibil pentru generare.)")
        
    parti.append(f"\nGenereaza quiz-ul acum in format JSON format din exact {nr_intrebari} intrebari:")
    return "\n".join(parti)

def construieste_prompt_flashcards(context_chunks: list, nr_flashcards: int) -> str:
    flashcards_system_prompt = f"""Esti un profesor universitar asistent. Sarcina ta este sa generezi un set de EXACT {nr_flashcards} flashcard-uri (fise de memorare) bazate EXCLUSIV pe textele oferite in contextul de mai jos.
    
Reguli de generare:
1. Fiecare flashcard trebuie sa aiba o fata (intrebare sau concept cheie scurt) si un verso (raspuns complet, dar concis si explicativ).
2. Informatiile trebuie sa fie luate EXCLUSIV din contextul oferit, fara a folosi cunostinte externe.
3. Raspunsul tau trebuie sa fie STRICT un tablou JSON (list) valid cu exact {nr_flashcards} elemente, fara alte texte, markdown sau introduceri.

Formatul JSON cerut:
[
  {{
    "fata": "Intrebarea sau conceptul cheie pe partea din fata (ex: Ce este X? sau Defineste Y)",
    "verso": "Explicatia sau raspunsul scurt si la obiect pe partea din spate, bazat pe text."
  }}
]
"""
    parti = [flashcards_system_prompt]
    
    if context_chunks:
        parti.append("\n--- CONTEXT START ---")
        for chunk in context_chunks:
            doc_label = chunk.get("document_title") or f"Document ID: {chunk['document_id']}"
            parti.append(f"[Material/Curs: {doc_label}]\n{chunk['text']}")
        parti.append("--- CONTEXT END ---")
    else:
        parti.append("\n(Atentie: Nu exista context disponibil pentru generare.)")
        
    parti.append(f"\nGenereaza cele {nr_flashcards} flashcard-uri acum in format JSON:")
    return "\n".join(parti)

