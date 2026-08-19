"""
src/patient_verifier.py

Privacy-Preserving Patient Identity Verification & PII Separation Layer.

Responsible for:
1. Extracting patient identity fields locally (without LLM calls).
2. Normalizing identity fields (names, dates, IDs, gender).
3. Deterministic cross-document verification (History PDF vs PA Form PDF).
4. Age calculation from DOB & stated age discrepancy detection.
5. Discrepancy reporting.
6. Local text de-identification (stripping PII before LLM calls).
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# NORMALIZATION FUNCTIONS
# ============================================================

HEADING_METADATA_PATTERNS = [
    r'\bunstructured\s+narrative\b',
    r'\bphysician\s+clinical\s+narrative\b',
    r'\bsynthetic\s+patient\s+clinical\s+record\b',
    r'\bsynthetic\s+health\s+plan\s+[a-z0-9]+\b',
    r'\bprior\s+authorization\s+request\b',
    r'\bpatient\s+background\b',
    r'\bpatient\s+history\b',
    r'\brequest\s+narrative\b',
    r'\bclinical\s+narrative\b',
    r'\bdocument\s+status\b',
    r'\bprovider\s+request\b',
    r'\bmedical\s+record\b',
    r'\bcase\s+report\b',
    r'\bclinical\s+summary\b',
    r'\bpatient\s+record\b',
    r'\bunstructured\b',
    r'\bnarrative\b',
    r'\bbackground\b',
    r'\bhistory\b',
    r'\brecord\b',
    r'\bsummary\b',
    r'\brequest\b',
]

def clean_extracted_name(val: Optional[str]) -> Optional[str]:
    """
    Clean and validate extracted candidate patient name.
    Strips document headings, section titles, and narrative metadata artifacts.
    """
    if not val:
        return None
    cleaned = str(val).strip()
    # Strip parenthetical annotations e.g. (synthetic)
    cleaned = re.sub(r'\(.*?\)', '', cleaned).strip()
    # Strip leading/trailing non-word punctuation
    cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', cleaned).strip()

    # Iteratively remove known heading metadata terms from start of candidate name
    changed = True
    while changed:
        changed = False
        for pat in HEADING_METADATA_PATTERNS:
            m = re.match(r'^(?:' + pat + r')\s+(.+)$', cleaned, re.IGNORECASE)
            if m:
                cleaned = m.group(1).strip()
                changed = True

    # Remove trailing heading metadata terms if present
    for pat in HEADING_METADATA_PATTERNS:
        cleaned = re.sub(r'\s+' + pat + r'$', '', cleaned, flags=re.IGNORECASE).strip()

    # Reject if candidate is empty or too short
    if not cleaned or len(cleaned) < 2:
        return None

    # Disallow common placeholder words
    invalid_words = {'patient', 'name', 'n/a', 'none', 'null', 'unknown', 'the', 'member', 'background', 'narrative', 'history', 'request', 'patient name'}
    if cleaned.lower() in invalid_words:
        return None

    # Filter out non-name tokens
    words = [w for w in cleaned.split() if w.lower() not in invalid_words]
    valid_words = [w for w in words if re.match(r'^[A-Za-z\.\,\'-]+$', w)]
    if len(valid_words) < 1:
        return None

    return " ".join(valid_words)


def normalize_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize patient name:
    - lowercase
    - strip punctuation (dots, commas, hyphens)
    - normalize whitespace
    """
    if not name:
        return None
    cleaned = str(name).strip().lower()
    # Remove common prefixes/suffixes
    cleaned = re.sub(r'\b(mr|mrs|ms|dr|jr|sr|ii|iii|iv)\b', '', cleaned)
    # Remove punctuation
    cleaned = re.sub(r'[\.\,\-\_\'\"]', ' ', cleaned)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else None


def normalize_id(id_str: Optional[str]) -> Optional[str]:
    """
    Normalize strong identifiers (Member ID, Patient ID, MRN):
    - lowercase
    - strip whitespace and formatting characters (hyphens, spaces, slashes)
    """
    if not id_str:
        return None
    cleaned = str(id_str).strip().lower()
    cleaned = re.sub(r'[\s\-\_\/]', '', cleaned)
    return cleaned if cleaned else None


def normalize_gender(gender_str: Optional[str]) -> Optional[str]:
    """
    Normalize gender values:
    M, Male, male -> male
    F, Female, female -> female
    """
    if not gender_str:
        return None
    val = str(gender_str).strip().lower()
    if val in ('m', 'male', 'man', 'boy'):
        return 'male'
    if val in ('f', 'female', 'woman', 'girl'):
        return 'female'
    if val in ('other', 'non-binary', 'nonbinary'):
        return 'other'
    return val


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Convert supported date formats to YYYY-MM-DD.
    Supported formats:
    - YYYY-MM-DD, YYYY/MM/DD
    - DD/MM/YYYY, DD-MM-YYYY (e.g. 15/04/1980, 15-04-1980)
    - MM/DD/YYYY, MM-DD-YYYY (e.g. 04/15/1980)
    - DD-Mon-YYYY, DD Mon YYYY, DD Month YYYY (e.g. 15-Apr-1980, 15 April 1980)
    - Month DD, YYYY, Mon DD, YYYY (e.g. April 15, 1980, Apr 15, 1980)
    """
    if not date_str:
        return None

    raw = str(date_str).strip()

    # Pattern 1: YYYY-MM-DD or YYYY/MM/DD
    m1 = re.match(r'^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$', raw)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            pass

    # Pattern 2: DD/MM/YYYY or MM/DD/YYYY
    m2 = re.match(r'^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$', raw)
    if m2:
        n1, n2, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        # If n1 > 12, it must be DD/MM/YYYY
        if n1 > 12:
            d, m = n1, n2
        elif n2 > 12:
            m, d = n1, n2
        else:
            # Default to DD/MM/YYYY standard if ambiguous
            d, m = n1, n2
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            try:
                return date(y, n2, n1).isoformat()
            except ValueError:
                pass

    # Pattern 3: Month DD, YYYY or Mon DD YYYY or DD Mon YYYY
    months = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }

    # "15-Apr-1980" or "15 April 1980"
    m3 = re.match(r'^(\d{1,2})[\s\-]+([A-Za-z]+)[\s\-]+(\d{4})$', raw)
    if m3:
        d, mon_str, y = int(m3.group(1)), m3.group(2).lower(), int(m3.group(3))
        if mon_str in months:
            try:
                return date(y, months[mon_str], d).isoformat()
            except ValueError:
                pass

    # "April 15, 1980" or "Apr 15 1980"
    m4 = re.match(r'^([A-Za-z]+)[\s\-]+(\d{1,2})[\,\s\-]+(\d{4})$', raw)
    if m4:
        mon_str, d, y = m4.group(1).lower(), int(m4.group(2)), int(m4.group(3))
        if mon_str in months:
            try:
                return date(y, months[mon_str], d).isoformat()
            except ValueError:
                pass

    # Fallback to dateutil if available
    try:
        from dateutil import parser
        parsed = parser.parse(raw, dayfirst=True)
        return parsed.date().isoformat()
    except Exception:
        pass

    return raw


# ============================================================
# LOCAL EXTRACTION (NO LLM)
# ============================================================

def extract_identity_fields_locally(text: str) -> Dict[str, Any]:
    """
    Extract identity fields from document text using deterministic regex patterns.
    Supports structured forms, JSON formats, tabular PDFs, and unstructured narrative text.
    Does NOT call any LLM.
    """
    if not text:
        return {
            "patient_id": None,
            "member_id": None,
            "date_of_birth": None,
            "name": None,
            "gender": None,
            "phone": None,
            "email": None,
            "address": None,
            "stated_age": None,
        }

    # 1. Name extraction
    name = None
    # JSON pattern first
    m_json_name = re.search(r'\"(?:patient_name|full_name|name)\"\s*:\s*\"([^\"]+)\"', text, re.IGNORECASE)
    if m_json_name:
        cleaned = clean_extracted_name(m_json_name.group(1).strip())
        if cleaned:
            name = cleaned

    if not name:
        name_patterns_structured = [
            r'(?:Patient\s*Name|Full\s*Name|Member\s*Name|Subscriber\s*Name)\s*[:\n\t]+\s*([A-Za-z\s\.\,\-]+)',
            r'Patient\s*:\s*([A-Za-z\s\.\,\-]+)',
            r'Name\s*:\s*([A-Za-z\s\.\,\-]+)',
        ]
        for pat in name_patterns_structured:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                val = re.split(r'\b(?:DOB|Date|Age|Gender|Sex|ID|MRN|Member|Phone|Email|Address|Payer|Insurance|Chief):', val, flags=re.IGNORECASE)[0].strip()
                val = re.sub(r'[\,\.\:\;\#]', '', val).strip()
                cleaned = clean_extracted_name(val)
                if cleaned:
                    name = cleaned
                    break

    if not name:
        # Tabular pattern (Label on one line, Value on next line)
        m_tab = re.search(r'(?:Patient\s*Name|Name)\s*[\n\r]+\s*([A-Za-z\s\.\,\-\(\)]+)', text, re.IGNORECASE)
        if m_tab:
            val = m_tab.group(1).strip().split('\n')[0].strip()
            cleaned = clean_extracted_name(val)
            if cleaned:
                name = cleaned

    if not name:
        narrative_name_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:is|was)\s+a\s+(?:\d{1,3}[\-\s]*year[\-\s]*old\s+)?(?:Female|Male|female|male)',
            r'(?:for|member|patient)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}),?\s+a\s+\d{1,3}[\-\s]*year[\-\s]*old',
            r'(?:The\s+patient,?\s+|\bPatient,?\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}),?\s+(?:is|was|\d{1,3}[\-\s]*year|a\s+)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}),\s+born\s+on',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}),?\s+a\s+\d{1,3}[\-\s]*year[\-\s]*old',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+\((?:DOB|MRN|Age|Gender)',
        ]
        for pat in narrative_name_patterns:
            m = re.search(pat, text)
            if m:
                val = m.group(1).strip()
                cleaned = clean_extracted_name(val)
                if cleaned:
                    name = cleaned
                    break

    # 2. Date of birth
    dob = None
    m_json_dob = re.search(r'\"(?:dob|date_of_birth|birth_date)\"\s*:\s*\"([^\"]+)\"', text, re.IGNORECASE)
    if m_json_dob:
        val = m_json_dob.group(1).strip()
        if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
            dob = val

    if not dob:
        dob_patterns = [
            r'(?:Date\s*of\s*Birth|DOB|Birth\s*Date|Birthdate)\s*[:\n\t]+\s*([0-9A-Za-z\/\-\,\s]+)',
            r'\bborn\s+(?:on\s+)?([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',
            r'\bdate\s+of\s+birth\s+(?:is\s+)?([A-Za-z0-9\/\-\,\s]+)',
        ]
        for pat in dob_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                val = re.split(r'\b(?:Age|Gender|Sex|ID|MRN|Member|Phone|Email|Address|Payer|Chief):', val, flags=re.IGNORECASE)[0].strip()
                if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                    dob = val
                    break

    if not dob:
        m_tab_dob = re.search(r'Date\s*of\s*Birth\s*[\n\r]+\s*([0-9A-Za-z\/\-\,\s]+)', text, re.IGNORECASE)
        if m_tab_dob:
            val = m_tab_dob.group(1).strip().split('\n')[0].strip()
            if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                dob = val

    # 3. Patient ID / MRN
    patient_id = None
    m_json_pid = re.search(r'\"(?:patient_id|mrn|medical_record_number)\"\s*:\s*\"([^\"]+)\"', text, re.IGNORECASE)
    if m_json_pid:
        val = m_json_pid.group(1).strip()
        if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
            patient_id = val

    if not patient_id:
        pid_patterns = [
            r'(?:MRN\s*/?\s*Patient\s*ID|Patient\s*ID|MRN|Medical\s*Record\s*(?:Number|#)?|Patient\s*#)\s*[:\n\t]+\s*([A-Za-z0-9\-\_]+)',
            r'\bmedical\s+record\s+number\s+(?:is\s+)?([A-Za-z0-9\-\_]+)',
            r'\bMRN\s*#?\s*:?\s*([A-Za-z0-9\-\_]+)',
            r'\bpatient\s+identifier\s+(?:is\s+)?([A-Za-z0-9\-\_]+)',
        ]
        for pat in pid_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                    patient_id = val
                    break

    if not patient_id:
        m_tab_pid = re.search(r'(?:MRN\s*/?\s*Patient\s*ID|Patient\s*ID|MRN)\s*[\n\r]+\s*([A-Za-z0-9\-\_]+)', text, re.IGNORECASE)
        if m_tab_pid:
            val = m_tab_pid.group(1).strip().split('\n')[0].strip()
            if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                patient_id = val

    # 4. Member ID
    member_id = None
    m_json_mem = re.search(r'\"(?:member_id|subscriber_id|insurance_id|policy_id)\"\s*:\s*\"([^\"]+)\"', text, re.IGNORECASE)
    if m_json_mem:
        val = m_json_mem.group(1).strip()
        if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
            member_id = val

    if not member_id:
        mem_patterns = [
            r'(?:Member\s*ID|Subscriber\s*ID|Insurance\s*ID|Policy\s*ID|Member\s*#)\s*[:\n\t]+\s*([A-Za-z0-9\-\_]+)',
            r'\bmember\s+ID\s+(?:is\s+)?([A-Za-z0-9\-\_]+)',
            r'\bsubscriber\s+ID\s+(?:is\s+)?([A-Za-z0-9\-\_]+)',
        ]
        for pat in mem_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                    member_id = val
                    break

    if not member_id:
        m_tab_mem = re.search(r'Member\s*ID\s*[\n\r]+\s*([A-Za-z0-9\-\_]+)', text, re.IGNORECASE)
        if m_tab_mem:
            val = m_tab_mem.group(1).strip().split('\n')[0].strip()
            if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                member_id = val

    # 5. Gender
    gender = None
    m_json_gen = re.search(r'\"gender\"\s*:\s*\"([^\"]+)\"', text, re.IGNORECASE)
    if m_json_gen:
        val = m_json_gen.group(1).strip()
        if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
            gender = val

    if not gender:
        gender_patterns = [
            r'(?:Gender|Sex)\s*[:\n\t]+\s*([A-Za-z]+)',
            r'\b\d{1,3}[\-\s]*year[\-\s]*old\s+(Female|Male|female|male)\b',
            r'\bis\s+a\s+(Female|Male|female|male)\b',
            r'\b(female|male)\s+patient\b',
        ]
        for pat in gender_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                    gender = val
                    break

    if not gender:
        m_tab_gen = re.search(r'Gender\s*[\n\r]+\s*([A-Za-z]+)', text, re.IGNORECASE)
        if m_tab_gen:
            val = m_tab_gen.group(1).strip()
            if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                gender = val

    # 6. Stated Age
    stated_age = None
    m_json_age = re.search(r'\"age\"\s*:\s*(\d{1,3})', text, re.IGNORECASE)
    if m_json_age:
        try:
            stated_age = int(m_json_age.group(1))
        except ValueError:
            pass

    if stated_age is None:
        age_patterns = [
            r'(?:Age)\s*[:\n\t]+\s*(\d{1,3})',
            r'\b(\d{1,3})[\-\s]*year[\-\s]*old\b',
            r'\b(\d{1,3})\s*(?:yo|y\/o|years\s*old)\b',
            r'\bage[d]?\s+(\d{1,3})\b',
        ]
        for pat in age_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    stated_age = int(m.group(1))
                    break
                except ValueError:
                    pass

    if stated_age is None:
        m_tab_age = re.search(r'Age\s*[\n\r]+\s*(\d{1,3})', text, re.IGNORECASE)
        if m_tab_age:
            try:
                stated_age = int(m_tab_age.group(1))
            except ValueError:
                pass

    def search_simple(patterns: List[str]) -> Optional[str]:
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip().split('\n')[0].strip()
                if val and val.lower() not in ('n/a', 'none', 'null', 'unknown'):
                    return val
        return None

    phone = search_simple([
        r'\"phone\"\s*:\s*\"([^\"]+)\"',
        r'(?:Phone|Tel|Telephone|Cell)\s*[:\n\t]+\s*([0-9\-\(\)\s\+\.]+)'
    ])
    email = search_simple([
        r'\"email\"\s*:\s*\"([^\"]+)\"',
        r'(?:Email|E-mail)\s*[:\n\t]+\s*([A-Za-z0-9\.\_\%\+\-]+@[A-Za-z0-9\.\-]+\.[A-Za-z]{2,})'
    ])
    address = search_simple([
        r'\"address\"\s*:\s*\"([^\"]+)\"',
        r'(?:Address)\s*[:\n\t]+\s*([^\n]+)'
    ])

    return {
        "patient_id": patient_id,
        "member_id": member_id,
        "date_of_birth": dob,
        "name": name,
        "gender": gender,
        "phone": phone,
        "email": email,
        "address": address,
        "stated_age": stated_age,
    }


def normalize_identity_record(identity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all fields in an extracted identity record.
    """
    raw_name = identity.get("name")
    cleaned_name = clean_extracted_name(raw_name) if raw_name else None
    return {
        "patient_id": normalize_id(identity.get("patient_id")),
        "member_id": normalize_id(identity.get("member_id")),
        "date_of_birth": normalize_date(identity.get("date_of_birth")),
        "name": normalize_name(identity.get("name")),
        "gender": normalize_gender(identity.get("gender")),
        "phone": normalize_id(identity.get("phone")),
        "email": identity.get("email").strip().lower() if identity.get("email") else None,
        "address": normalize_name(identity.get("address")),
        "stated_age": identity.get("stated_age"),
        "patient_name": cleaned_name or raw_name,
        "raw_name": raw_name,
        "raw": identity,
    }


# ============================================================
# AGE CALCULATION & DISCREPANCY DETECTION
# ============================================================

def calculate_age_from_dob(dob_str: Optional[str], ref_date: Optional[date] = None) -> Optional[int]:
    """
    Calculate patient age in years programmatically from DOB (YYYY-MM-DD format).
    """
    if not dob_str:
        return None

    normalized_dob = normalize_date(dob_str)
    if not normalized_dob or not re.match(r'^\d{4}-\d{2}-\d{2}$', normalized_dob):
        return None

    try:
        dob_obj = date.fromisoformat(normalized_dob)
    except ValueError:
        return None

    if ref_date is None:
        ref_date = date.today()

    age = ref_date.year - dob_obj.year - ((ref_date.month, ref_date.day) < (dob_obj.month, dob_obj.day))
    return age if age >= 0 else None


# ============================================================
# DETERMINISTIC PATIENT VERIFICATION ENGINE
# ============================================================

def verify_patient_documents(
    history_identity: Dict[str, Any],
    pa_identity: Dict[str, Any],
    ref_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Compare identity extracted from History PDF vs PA Form PDF based on AVAILABLE fields.
    Deterministic verification rules:
    1. Mismatch in any present strong identifier (patient_id, member_id, date_of_birth, name), gender, or age forces MISMATCH.
    2. Missing secondary/optional fields (phone, email, member_id, gender) do NOT by themselves cause failure.
    3. Patient ID/MRN match + DOB (or age) match -> VERIFIED.
    4. Patient ID/MRN match + Name match -> VERIFIED.
    5. Name + DOB (or age) match -> VERIFIED.
    6. Any matching strong identifier without conflicts -> VERIFIED.
    """
    norm_hist = normalize_identity_record(history_identity)
    norm_pa = normalize_identity_record(pa_identity)

    compared_fields = ["name", "date_of_birth", "member_id", "patient_id", "gender", "phone", "email"]
    strong_fields = ["patient_id", "member_id", "date_of_birth", "name"]

    field_results = {}
    discrepancies = []
    matches_count = 0
    mismatches_count = 0
    present_compared_count = 0

    for field in compared_fields:
        h_val = norm_hist.get(field)
        p_val = norm_pa.get(field)

        if h_val is None or p_val is None:
            field_results[field] = "UNAVAILABLE"
        elif h_val == p_val:
            field_results[field] = "MATCH"
            matches_count += 1
            present_compared_count += 1
        else:
            field_results[field] = "MISMATCH"
            mismatches_count += 1
            present_compared_count += 1

            field_labels = {
                "date_of_birth": "Date of Birth",
                "member_id": "Member ID",
                "patient_id": "Patient ID"
            }
            field_label = field_labels.get(field, field.replace('_', ' ').title())
            h_raw = history_identity.get(field) or norm_hist.get(field)
            p_raw = pa_identity.get(field) or norm_pa.get(field)
            discrepancies.append(f"{field_label} does not match (History: '{h_raw}' vs PA Form: '{p_raw}')")

    # Age calculation & Stated Age Check
    calc_age_hist = calculate_age_from_dob(norm_hist.get("date_of_birth"), ref_date)
    calc_age_pa = calculate_age_from_dob(norm_pa.get("date_of_birth"), ref_date)
    calc_age = calc_age_hist if calc_age_hist is not None else calc_age_pa

    stated_hist_age = norm_hist.get("stated_age")
    stated_pa_age = norm_pa.get("stated_age")

    eff_age_hist = calc_age_hist if calc_age_hist is not None else stated_hist_age
    eff_age_pa = calc_age_pa if calc_age_pa is not None else stated_pa_age

    if eff_age_hist is not None and eff_age_pa is not None:
        if abs(eff_age_hist - eff_age_pa) <= 1:
            field_results["age"] = "MATCH"
            matches_count += 1
            present_compared_count += 1
        else:
            field_results["age"] = "MISMATCH"
            mismatches_count += 1
            present_compared_count += 1
            discrepancies.append(f"Age does not match (History: '{eff_age_hist}' vs PA Form: '{eff_age_pa}')")
    elif eff_age_hist is not None or eff_age_pa is not None:
        field_results["age"] = "UNAVAILABLE"

    # Evaluate overall status
    has_strong_mismatch = any(field_results.get(f) == "MISMATCH" for f in strong_fields)
    has_gender_mismatch = field_results.get("gender") == "MISMATCH"
    has_age_mismatch = field_results.get("age") == "MISMATCH"
    has_any_mismatch = mismatches_count > 0

    if has_strong_mismatch or has_gender_mismatch or has_age_mismatch or has_any_mismatch:
        verified = False
        status = "MISMATCH"
    else:
        pid_match = field_results.get("patient_id") == "MATCH" or field_results.get("member_id") == "MATCH"
        dob_match = field_results.get("date_of_birth") == "MATCH" or field_results.get("age") == "MATCH"
        name_match = field_results.get("name") == "MATCH"

        has_hist_info = any(norm_hist.get(k) is not None for k in ["patient_id", "member_id", "date_of_birth", "name", "stated_age"])
        has_pa_info = any(norm_pa.get(k) is not None for k in ["patient_id", "member_id", "date_of_birth", "name", "stated_age"])

        if (pid_match and dob_match) or (pid_match and name_match) or (name_match and dob_match) or (matches_count >= 1 and (has_hist_info or has_pa_info)):
            verified = True
            status = "MATCH"
        elif (has_hist_info and not has_pa_info) or (has_pa_info and not has_hist_info):
            verified = True
            status = "MATCH"
        else:
            verified = False
            status = "INSUFFICIENT_DATA"
            discrepancies.append("Complete identity fields were not available for cross-document matching.")

    if verified:
        score = 100 if present_compared_count == 0 else max(80, int((matches_count / max(1, present_compared_count)) * 100))
    else:
        if status == "INSUFFICIENT_DATA":
            score = 0
        elif present_compared_count > 0:
            score = min(50, int((matches_count / present_compared_count) * 100))
        else:
            score = 0

    age_warnings = []
    if calc_age is not None:
        if stated_hist_age is not None and abs(stated_hist_age - calc_age) > 1:
            age_warnings.append(f"AGE DISCREPANCY: History stated age ({stated_hist_age}) differs from calculated age from DOB ({calc_age}).")
        if stated_pa_age is not None and abs(stated_pa_age - calc_age) > 1:
            age_warnings.append(f"AGE DISCREPANCY: PA Form stated age ({stated_pa_age}) differs from calculated age from DOB ({calc_age}).")
    if stated_hist_age is not None and stated_pa_age is not None and abs(stated_hist_age - stated_pa_age) > 1:
        age_warnings.append(f"AGE DISCREPANCY: Stated age in History ({stated_hist_age}) differs from PA Form ({stated_pa_age}).")

    final_calc_age = calc_age if calc_age is not None else (eff_age_hist if eff_age_hist is not None else eff_age_pa)

    return {
        "verified": verified,
        "status": status,
        "score": score,
        "fields": field_results,
        "discrepancies": discrepancies,
        "age_warnings": age_warnings,
        "calculated_age": final_calc_age,
        "history_identity": norm_hist,
        "pa_identity": norm_pa,
    }


# ============================================================
# LOCAL DE-IDENTIFICATION (PII STRIPPING)
# ============================================================

def deidentify_text(
    text: str,
    identity_data: Dict[str, Any],
    calculated_age: Optional[int] = None
) -> str:
    """
    Remove all PII tokens (Name, DOB, Patient ID, Member ID, Phone, Email, Address)
    from text before passing to the LLM.
    """
    if not text:
        return ""

    deidentified = text

    # Extract all raw/normalized PII strings to redact
    pii_values = []
    for k in ["name", "date_of_birth", "patient_id", "member_id", "phone", "email", "address"]:
        val = identity_data.get(k)
        if val and isinstance(val, str) and len(val.strip()) > 1:
            pii_values.append(val.strip())

    # Add raw values if available
    raw = identity_data.get("raw") or {}
    for k in ["name", "date_of_birth", "patient_id", "member_id", "phone", "email", "address"]:
        val = raw.get(k)
        if val and isinstance(val, str) and len(val.strip()) > 1:
            pii_values.append(val.strip())

    # Sort PII strings by length descending to replace longer phrases first
    pii_values = sorted(list(set(pii_values)), key=len, reverse=True)

    for pii in pii_values:
        pattern = re.escape(pii)
        deidentified = re.sub(pattern, "[REDACTED_PII]", deidentified, flags=re.IGNORECASE)

    # Redact common PII label patterns
    deidentified = re.sub(
        r'(?:Patient\s*Name|Name|Full\s*Name):\s*[^\n]+',
        'Patient Name: [REDACTED_NAME]',
        deidentified, flags=re.IGNORECASE
    )

    if calculated_age is not None:
        deidentified = re.sub(
            r'(?:Date\s*of\s*Birth|DOB|Birth\s*Date):\s*[^\n]+',
            f'Age: {calculated_age}',
            deidentified, flags=re.IGNORECASE
        )
    else:
        deidentified = re.sub(
            r'(?:Date\s*of\s*Birth|DOB|Birth\s*Date):\s*[^\n]+',
            'Date of Birth: [REDACTED_DOB]',
            deidentified, flags=re.IGNORECASE
        )

    deidentified = re.sub(
        r'(?:Patient\s*ID|MRN|Medical\s*Record\s*(?:Number|#)?):\s*[^\n]+',
        'Patient ID: [REDACTED_ID]',
        deidentified, flags=re.IGNORECASE
    )

    deidentified = re.sub(
        r'(?:Member\s*ID|Subscriber\s*ID|Insurance\s*ID|Policy\s*ID|Member\s*#):\s*[^\n]+',
        'Member ID: [REDACTED_MEMBER_ID]',
        deidentified, flags=re.IGNORECASE
    )

    deidentified = re.sub(
        r'(?:Phone|Tel|Telephone):\s*[^\n]+',
        'Phone: [REDACTED_PHONE]',
        deidentified, flags=re.IGNORECASE
    )

    deidentified = re.sub(
        r'(?:Email|E-mail):\s*[^\n]+',
        'Email: [REDACTED_EMAIL]',
        deidentified, flags=re.IGNORECASE
    )

    deidentified = re.sub(
        r'(?:Address):\s*[^\n]+',
        'Address: [REDACTED_ADDRESS]',
        deidentified, flags=re.IGNORECASE
    )

    return deidentified
