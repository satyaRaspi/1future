from __future__ import annotations

from datetime import date, datetime, time as dt_time, timedelta
import math
import re
from typing import Dict, List, Any

MASTER_NUMBERS = {11, 22, 33}
VOWELS = set("AEIOU")

ZODIAC = [
    ("Capricorn", 270), ("Aquarius", 300), ("Pisces", 330), ("Aries", 0), ("Taurus", 30), ("Gemini", 60),
    ("Cancer", 90), ("Leo", 120), ("Virgo", 150), ("Libra", 180), ("Scorpio", 210), ("Sagittarius", 240),
]
RASHIS = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)", "Karka (Cancer)", "Simha (Leo)", "Kanya (Virgo)",
    "Tula (Libra)", "Vrischika (Scorpio)", "Dhanu (Sagittarius)", "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
]
NAKSHATRAS = [
    ("Ashwini", "swift beginnings, healing impulse, fast-moving life energy"),
    ("Bharani", "intense will, endurance, deep transformation"),
    ("Krittika", "clarity, fire, decisive cutting away"),
    ("Rohini", "beauty, growth, attraction and material creation"),
    ("Mrigashira", "curiosity, search, restlessness for truth"),
    ("Ardra", "storm energy, emotional depth, rebuilding after intensity"),
    ("Punarvasu", "renewal, return, second chances and resilience"),
    ("Pushya", "nourishment, duty, protection and support"),
    ("Ashlesha", "psychological depth, strategy and hidden layers"),
    ("Magha", "ancestral force, dignity and legacy consciousness"),
    ("Purva Phalguni", "pleasure, creativity, relationship magnetism"),
    ("Uttara Phalguni", "commitment, loyalty and sustained partnership"),
    ("Hasta", "skill, cleverness, workmanship and tact"),
    ("Chitra", "design, charisma, refinement and visibility"),
    ("Swati", "independence, flexibility and wandering intelligence"),
    ("Vishakha", "goal focus, ambition and determined progress"),
    ("Anuradha", "friendship, devotion and disciplined connection"),
    ("Jyeshtha", "authority, protection and crisis maturity"),
    ("Mula", "root-seeking, radical honesty and uprooting"),
    ("Purva Ashadha", "conviction, persuasion and emotional force"),
    ("Uttara Ashadha", "lasting achievement, ethics and reputation"),
    ("Shravana", "listening, learning and social intelligence"),
    ("Dhanishta", "rhythm, performance, wealth-building and teamwork"),
    ("Shatabhisha", "healing, detachment and unconventional insight"),
    ("Purva Bhadrapada", "idealism, intensity and transformative purpose"),
    ("Uttara Bhadrapada", "depth, steadiness and inner maturity"),
    ("Revati", "guidance, protection, compassion and completion"),
]
WEEKDAY_RULERS = {
    0: ("Monday", "Moon", "emotional intelligence, responsiveness and care"),
    1: ("Tuesday", "Mars", "drive, courage, assertion and competitive energy"),
    2: ("Wednesday", "Mercury", "communication, adaptability and quick intelligence"),
    3: ("Thursday", "Jupiter", "wisdom, expansion, teaching and ethics"),
    4: ("Friday", "Venus", "love, taste, harmony and relationship sensitivity"),
    5: ("Saturday", "Saturn", "discipline, karmic lessons, patience and responsibility"),
    6: ("Sunday", "Sun", "identity, visibility, pride and leadership"),
}

NAME_MEANINGS: Dict[str, Dict[str, str]] = {
    "aarav": {"meaning": "peaceful, calm, melodious", "origin": "Sanskrit / Indian", "commonness": "Very common modern Indian first name"},
    "aditya": {"meaning": "sun; descendant of Aditi", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "ananya": {"meaning": "unique, matchless, without another", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "arjun": {"meaning": "bright, white, clear; heroic archer from the Mahabharata", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "ashwin": {"meaning": "light, horse-tamer; linked with the Ashwini twins", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "deepak": {"meaning": "lamp, light", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "divya": {"meaning": "divine, heavenly, brilliant", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "kavya": {"meaning": "poetry, poetic expression", "origin": "Sanskrit / Indian", "commonness": "Common South Indian / Indian first name"},
    "lakshmi": {"meaning": "auspiciousness, prosperity; goddess of wealth", "origin": "Sanskrit / Indian", "commonness": "Very common Indian feminine name and name element"},
    "mahesh": {"meaning": "great lord; a name of Shiva", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "meera": {"meaning": "devotional, ocean/limit in some interpretations; associated with Mirabai", "origin": "Indian / Sanskrit-Hindi usage", "commonness": "Common Indian first name"},
    "priya": {"meaning": "beloved, dear", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "rahul": {"meaning": "efficient, conqueror of miseries; also Buddha’s son", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "ravi": {"meaning": "sun", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "sanjay": {"meaning": "victorious, triumphant", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "satya": {"meaning": "truth, reality, sincerity", "origin": "Sanskrit / Indian", "commonness": "Recognised Indian name; moderately common as first name and name element"},
    "savitri": {"meaning": "solar, life-giving; associated with the Savitri tradition", "origin": "Sanskrit / Indian", "commonness": "Traditional Indian name; moderately common among older generations"},
    "shreya": {"meaning": "auspicious, excellent, fortunate", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
    "srinivasan": {"meaning": "one in whom Lakshmi resides; a name associated with Vishnu", "origin": "Sanskrit / South Indian", "commonness": "Very common South Indian family name / given name element"},
    "vijay": {"meaning": "victory", "origin": "Sanskrit / Indian", "commonness": "Very common Indian first name"},
    "vikram": {"meaning": "valour, stride, courage", "origin": "Sanskrit / Indian", "commonness": "Common Indian first name"},
}

LUCKY_PROFILE_BY_NUMBER: Dict[int, Dict[str, str]] = {
    1: {"color": "gold / sunrise orange", "fruit": "mango", "day": "Sunday", "number": "1"},
    2: {"color": "pearl white / soft cream", "fruit": "lychee", "day": "Monday", "number": "2"},
    3: {"color": "yellow / saffron", "fruit": "banana", "day": "Thursday", "number": "3"},
    4: {"color": "deep blue / graphite", "fruit": "jamun", "day": "Saturday", "number": "4"},
    5: {"color": "green / emerald", "fruit": "guava", "day": "Wednesday", "number": "5"},
    6: {"color": "rose pink / ivory", "fruit": "pomegranate", "day": "Friday", "number": "6"},
    7: {"color": "violet / indigo", "fruit": "fig", "day": "Monday", "number": "7"},
    8: {"color": "navy / black", "fruit": "black grapes", "day": "Saturday", "number": "8"},
    9: {"color": "red / coral", "fruit": "apple", "day": "Tuesday", "number": "9"},
    11: {"color": "silver / electric blue", "fruit": "pear", "day": "Monday", "number": "11"},
    22: {"color": "royal blue / bronze", "fruit": "coconut", "day": "Saturday", "number": "22"},
    33: {"color": "white / lotus pink", "fruit": "sweet lime", "day": "Friday", "number": "33"},
}

PROMPT_OPTIONS: Dict[str, Dict[str, str]] = {
    "life_path": {
        "title": "The Decoder of the Life Path",
        "short": "Deep personality, strengths, weaknesses and destiny map.",
        "prompt": "I want you to act as a decoder of my life path. I’ll give you my date of birth: [insert date]. Analyze it using psychology, numerological logic, and life patterns to reveal my deepest personality traits, hidden strengths, weaknesses, and my destiny map. Be brutally honest and deliver an analysis so precise that it feels like you’ve known me forever. Highlight the most important purpose I must pursue in this life.",
    },
    "soul_purpose": {
        "title": "The Discoverer of the Soul's Purpose",
        "short": "Central mission, life lessons and contribution to the world.",
        "prompt": "Using my date of birth [insert date], act as my guide to the soul's purpose. Reveal the central mission of my life, the lessons I am destined to learn, and the contribution I came to make to the world. Don't just describe: give me clear guidance and actions.",
    },
    "professional_destiny": {
        "title": "The Professional Destiny Detector",
        "short": "Talent pattern, decision style, best careers and one field to avoid.",
        "prompt": "You are my professional mentor of the future. Using my date of birth [insert date], analyze my natural talents, my decision-making style, and my hidden motivations. Then reveal the 3 career or business paths where I am destined to achieve extraordinary success, along with the one field I should avoid at all costs.",
    },
    "relationships": {
        "title": "The Destiny Map in Relationships",
        "short": "Compatibility, love lessons and ideal partner profile.",
        "prompt": "I will give you my date of birth [insert date]. Based on it, discover what type of people I am most compatible with, the love lessons I must learn, and the role that relationships play in my life path. Give me an exact description of the type of partner who will help me become my best version.",
    },
    "wealth_abundance": {
        "title": "The Code of Wealth and Abundance",
        "short": "Financial personality, money blockers and wealth strategy.",
        "prompt": "Using my date of birth [insert date], decipher the exact way in which I am destined to attract wealth, opportunities, and abundance. Reveal my natural financial personality, the mistakes that are blocking my economic growth, and the wealth strategy that truly fits me, not generic advice.",
    },
    "future_timeline": {
        "title": "The Future Timeline Guide",
        "short": "Past, present and next 5-year roadmap.",
        "prompt": "I want you to use my date of birth [insert date] as a timeline map. Show me the key turning points in my life (past, present, and future), the stages of growth and difficulty, and the exact path of the next 5 years. Write it as a clear roadmap so I can see where I'm headed.",
    },
    "compatibility": {
        "title": "Partner Compatibility Report",
        "short": "Two-person love, marriage and emotional fit analysis.",
        "prompt": "Compare two people using DOB, name, life-path and South Indian style indicators.",
    },
    "children_family": {
        "title": "Children & Family Outlook",
        "short": "Family patterns, children themes and care style.",
        "prompt": "Interpret family, children and home patterns from the birth profile.",
    },
    "name_suggestion": {
        "title": "Name Correction & Lucky Name",
        "short": "Name meaning, spelling options and lucky signals.",
        "prompt": "Evaluate name meaning, spelling and numerology-style resonance.",
    },
    "business_name": {
        "title": "Business Name Numerology",
        "short": "Brand/name fit, number resonance and positioning.",
        "prompt": "Evaluate business name fit using readability, trust and numerology-style resonance.",
    },
}


def parse_dob(raw: str) -> date:
    if not raw or not raw.strip():
        raise ValueError("Date of birth is required.")
    s = raw.strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            dob = datetime.strptime(s, fmt).date()
            if dob > date.today():
                raise ValueError("Date of birth cannot be in the future.")
            return dob
        except ValueError:
            continue
    raise ValueError("Please enter the date as YYYY-MM-DD or DD-MM-YYYY.")


def parse_birth_time(raw: str | None) -> dt_time | None:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    for fmt in ["%H:%M", "%H:%M:%S"]:
        try:
            return datetime.strptime(s, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    raise ValueError("Birth time must be in HH:MM 24-hour format.")


def digital_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def reduce_number(n: int, keep_master: bool = True) -> int:
    while n > 9:
        if keep_master and n in MASTER_NUMBERS:
            return n
        n = digital_sum(n)
    return n


def reduce_digits_string(s: str, keep_master: bool = True) -> int:
    total = sum(int(ch) for ch in s if ch.isdigit())
    return reduce_number(total, keep_master=keep_master)


def pythagorean_letter_value(ch: str) -> int:
    ch = ch.upper()
    if "A" <= ch <= "Z":
        return ((ord(ch) - ord("A")) % 9) + 1
    return 0


def name_numbers(name: str) -> Dict[str, int]:
    letters = [c.upper() for c in name if c.isalpha()]
    total = sum(pythagorean_letter_value(c) for c in letters)
    vowels = sum(pythagorean_letter_value(c) for c in letters if c in VOWELS)
    consonants = sum(pythagorean_letter_value(c) for c in letters if c not in VOWELS)
    return {
        "expression": reduce_number(total),
        "soul_urge": reduce_number(vowels),
        "personality": reduce_number(consonants),
        "raw_expression_total": total,
    }


LIFE_PATHS: Dict[int, Dict[str, Any]] = {
    1: {"title": "The Independent Initiator", "core": "You are wired to start, decide, lead and move first. Your strongest pattern is self-direction.", "strengths": ["decisiveness", "originality", "courage under pressure", "ability to open doors where others wait"], "weaknesses": ["impatience", "difficulty taking advice", "loneliness from trying to carry everything", "ego bruising when outcomes are slow"], "purpose": "Build something with your name, judgment and courage on it — and learn leadership without becoming isolated.", "shadow": "You can mistake independence for emotional distance. The lesson is to lead without making every relationship a chain of command.", "work": "Founder, operator, senior owner, product head, strategy lead, crisis lead, public-facing champion."},
    2: {"title": "The Diplomatic Connector", "core": "You are tuned to nuance, emotional signals and cooperation. You read rooms faster than people realise.", "strengths": ["patience", "partnership", "mediation", "loyalty", "quiet influence"], "weaknesses": ["over-accommodation", "avoidance of conflict", "taking moods personally", "waiting too long to claim credit"], "purpose": "Create trust, partnership and emotional safety — while learning not to disappear inside other people’s needs.", "shadow": "You may call it peacekeeping when it is actually self-silencing. Your growth comes from honest boundaries.", "work": "People leadership, client relations, HR, partnerships, counselling, negotiation, community building."},
    3: {"title": "The Expressive Communicator", "core": "You are designed to translate experience into words, performance, humour, story and human connection.", "strengths": ["communication", "creativity", "social warmth", "optimism", "quick ideation"], "weaknesses": ["scattered focus", "unfinished work", "masking pain with wit", "needing applause to feel safe"], "purpose": "Turn your voice into value — teach, entertain, write, present or create in a way that makes people feel alive.", "shadow": "Your charisma can hide inconsistency. Talent is not the problem; disciplined completion is.", "work": "Branding, media, writing, teaching, sales, consulting, design, public speaking, content creation."},
    4: {"title": "The System Builder", "core": "You are built for structure, discipline, process and practical reliability. You convert ideas into working reality.", "strengths": ["consistency", "operational discipline", "loyalty", "risk control", "craftsmanship"], "weaknesses": ["rigidity", "overwork", "fear of instability", "resentment when others are careless"], "purpose": "Build durable systems, assets and institutions — and learn that flexibility is not weakness.", "shadow": "You may cling to control because uncertainty feels unsafe. Your breakthrough is trusting adaptability without abandoning standards.", "work": "Operations, engineering, compliance, finance control, project management, architecture, administration."},
    5: {"title": "The Freedom Strategist", "core": "You are energised by movement, change, variety and experience. You learn by testing life directly.", "strengths": ["adaptability", "persuasion", "fast learning", "commercial instinct", "comfort with change"], "weaknesses": ["restlessness", "over-promising", "boredom with routine", "escaping when depth is required"], "purpose": "Use freedom responsibly — create routes, markets, messages and experiences that expand possibilities for others.", "shadow": "You may call something ‘freedom’ when it is actually avoidance of commitment. Mastery begins when you choose a direction and stay long enough to win.", "work": "Sales, travel, growth, marketing, product launches, entrepreneurship, trading, field operations."},
    6: {"title": "The Responsible Protector", "core": "You are pulled toward service, family, care, beauty and responsibility. People often expect you to hold things together.", "strengths": ["care", "accountability", "mentoring", "aesthetic sense", "community commitment"], "weaknesses": ["rescuing people", "guilt", "perfectionism", "controlling through concern"], "purpose": "Create harmony, protection and responsible leadership — while learning that love does not mean carrying everyone’s burden.", "shadow": "Your help can become invisible control. The lesson is to support without owning the other person’s life.", "work": "Education, healthcare, governance, hospitality, design, social impact, family business leadership."},
    7: {"title": "The Seeker Analyst", "core": "You are oriented toward depth, research, truth and private understanding. You need meaning, not just noise.", "strengths": ["analysis", "intuition", "deep study", "spiritual curiosity", "independent thinking"], "weaknesses": ["overthinking", "withdrawal", "skepticism", "difficulty trusting simple happiness"], "purpose": "Find truth, master a knowledge domain and become a trusted interpreter of complexity.", "shadow": "You can hide behind analysis when life asks for participation. Wisdom must eventually come out of the cave.", "work": "Research, analytics, technology, investigation, strategy, writing, philosophy, risk advisory."},
    8: {"title": "The Power Architect", "core": "You are built around ambition, execution, material impact and authority. You notice leverage and hierarchy quickly.", "strengths": ["enterprise thinking", "financial instinct", "resilience", "executive presence", "large-scale execution"], "weaknesses": ["workaholism", "control issues", "impatience with weakness", "measuring worth only through achievement"], "purpose": "Build power ethically — wealth, institutions, influence and systems that produce measurable results.", "shadow": "You may confuse control with safety. Your life improves when success includes trust, generosity and emotional maturity.", "work": "Business leadership, finance, governance, law, real estate, operations, large programs, negotiations."},
    9: {"title": "The Humanitarian Integrator", "core": "You are broad-hearted, idealistic and often older than your years. You see the human story behind events.", "strengths": ["compassion", "big-picture thinking", "artistic sensitivity", "forgiveness", "global perspective"], "weaknesses": ["emotional exhaustion", "idealising people", "difficulty letting go", "taking on collective pain"], "purpose": "Serve a cause larger than yourself — but with boundaries, not martyrdom.", "shadow": "You can stay loyal to expired chapters. Your destiny opens when you stop confusing endings with failure.", "work": "Public service, teaching, consulting, art, NGOs, policy, healing professions, leadership with social purpose."},
    11: {"title": "The Intuitive Messenger", "core": "You combine sensitivity with inspiration. You are here to notice patterns others miss and give them language.", "strengths": ["intuition", "vision", "inspiration", "emotional intelligence", "creative perception"], "weaknesses": ["nervous intensity", "self-doubt", "high sensitivity", "inconsistent grounding"], "purpose": "Turn intuition into guidance, art, teaching or leadership that awakens people.", "shadow": "Your insight is wasted if it never becomes disciplined work. Ground the vision or it stays a mood.", "work": "Coaching, writing, design, teaching, spiritual leadership, strategy, innovation, change programs."},
    22: {"title": "The Master Builder", "core": "You carry the builder energy of 4 at a larger scale: institutions, platforms, infrastructure and social impact.", "strengths": ["vision with execution", "systems leadership", "practical ambition", "large-scale responsibility"], "weaknesses": ["pressure overload", "fear of failing big", "controlling every detail", "delaying action until conditions are perfect"], "purpose": "Build something useful, durable and bigger than personal comfort.", "shadow": "Because the assignment feels large, you may postpone the first brick. The antidote is structured action now.", "work": "Enterprise building, infrastructure, governance, product platforms, social architecture, major programs."},
    33: {"title": "The Master Teacher", "core": "You carry the service energy of 6 at a wider human level: guidance, healing, responsibility and moral influence.", "strengths": ["teaching", "compassion", "protective leadership", "high responsibility", "moral courage"], "weaknesses": ["self-sacrifice", "burden addiction", "emotional exhaustion", "expecting impossible maturity from yourself"], "purpose": "Teach, heal or guide in a way that raises the standard of care around you.", "shadow": "You can make service your identity and forget to receive. Your work is strongest when it is not powered by guilt.", "work": "Teaching, public service, caregiving leadership, counselling, social reform, cultural leadership."},
}

NUMBER_STYLE: Dict[int, str] = {
    1: "assertive, self-starting and direct", 2: "sensitive, cooperative and relational", 3: "expressive, playful and communicative",
    4: "stable, structured and duty-oriented", 5: "adaptive, curious and freedom-seeking", 6: "responsible, protective and harmony-seeking",
    7: "reflective, analytical and inward-looking", 8: "ambitious, executive and results-driven", 9: "idealistic, compassionate and broad-minded",
    11: "intuitive, intense and visionary", 22: "practical, powerful and institution-building", 33: "nurturing, teaching-oriented and service-driven",
}
MONTH_PATTERNS: Dict[int, str] = {
    1: "You tend to start cycles strongly but can lose patience with slow systems.", 2: "You are affected by emotional climate and may perform best in trusted environments.",
    3: "Communication, humour and creativity are major recovery mechanisms for you.", 4: "You need order, predictability and evidence before committing fully.",
    5: "You dislike being boxed in; variety renews your energy.", 6: "Responsibility, family and reputation carry unusual weight in your decisions.",
    7: "You need solitude to metabolise life; too much noise weakens your clarity.", 8: "You are sensitive to status, progress, money and competence.",
    9: "You often think in endings, meaning, memory and legacy.", 10: "You combine initiative with a need to prove competence through results.",
    11: "You may feel emotionally intense and unusually aware of hidden dynamics.", 12: "You often balance social warmth with a private need to close chapters cleanly.",
}
COMPATIBILITY: Dict[int, str] = {
    1: "independent, self-respecting partners who admire leadership but do not surrender their own identity",
    2: "emotionally steady, loyal and communicative people who value trust over drama",
    3: "warm, expressive and creative people who enjoy conversation, humour and social energy",
    4: "reliable, grounded and consistent people who keep promises and respect routines",
    5: "curious, adventurous and flexible people who give space without becoming detached",
    6: "family-oriented, responsible and emotionally mature people who understand care without dependency",
    7: "thoughtful, private and intellectually honest people who respect silence and depth",
    8: "ambitious, capable and emotionally strong people who can handle power without power games",
    9: "compassionate, worldly and purpose-led people who understand endings, healing and reinvention",
    11: "sensitive, intuitive and grounded partners who can hold intensity without chaos",
    22: "builders, organisers and long-range thinkers who respect scale, duty and execution",
    33: "nurturing, wise and service-oriented people who give love without guilt or control",
}
CAREER_BUCKETS: Dict[int, List[str]] = {
    1: ["Founder-led venture, product ownership, or independent consulting", "Crisis leadership, operations command, or transformation programs", "Public-facing leadership, sales leadership, or political/advocacy work"],
    2: ["Partnerships, client success, HR, or people advisory", "Negotiation, mediation, counselling, or community design", "Executive coordination roles where trust and nuance decide outcomes"],
    3: ["Branding, media, content, public speaking, or education", "Sales, marketing campaigns, events, or creator-led business", "Consulting roles where storytelling turns complexity into buy-in"],
    4: ["Operations, project/program management, engineering, or compliance", "Finance control, administration, infrastructure, or quality systems", "Asset-building businesses where discipline compounds over time"],
    5: ["Growth, sales, market expansion, travel, or field operations", "Entrepreneurship around platforms, distribution, brokerage, or trade", "Product launches, marketing experiments, or commercial strategy"],
    6: ["Education, healthcare, hospitality, governance, or social impact", "Design, family business leadership, community platforms, or mentoring", "Trust-based service businesses that improve daily life for families"],
    7: ["Research, analytics, technology, investigation, or strategy", "Writing, knowledge products, philosophy, risk advisory, or audit", "Specialist consulting where depth matters more than noise"],
    8: ["Business leadership, finance, real estate, or enterprise operations", "Large program management, governance, law, or negotiation-heavy work", "Institution-building ventures with measurable commercial outcomes"],
    9: ["Public service, policy, education, NGO, consulting, or social leadership", "Creative or cultural work with a human message", "Global, humanitarian, or legacy-oriented businesses"],
    11: ["Coaching, teaching, writing, design, or inspirational leadership", "Innovation, transformation, change communication, or culture building", "Advisory work where intuition and pattern recognition create breakthroughs"],
    22: ["Infrastructure-scale ventures, institutions, platforms, or civic programs", "Enterprise architecture, governance, program leadership, or real estate", "Large consulting or implementation businesses that need vision plus discipline"],
    33: ["Education, healing, mentoring, social impact, or community leadership", "Purpose-led brands, training institutions, or family welfare platforms", "High-trust advisory work where people need both truth and compassion"],
}


def life_path_number(dob: date) -> int:
    return reduce_digits_string(dob.strftime("%d%m%Y"), keep_master=True)


def age_on_today(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def birth_day_number(dob: date) -> int:
    return reduce_number(dob.day, keep_master=True)


def attitude_number(dob: date) -> int:
    return reduce_number(dob.day + dob.month, keep_master=True)


def personal_year_number(dob: date, year: int | None = None) -> int:
    year = year or date.today().year
    return reduce_number(dob.day + dob.month + digital_sum(year), keep_master=False)


def personal_year_theme(num: int) -> str:
    return {
        1: "new beginnings, decision and identity reset", 2: "partnership, patience and careful alignment", 3: "visibility, communication and creative output",
        4: "systems, discipline and foundation-building", 5: "change, movement and calculated risk", 6: "family, responsibility and relationship repair",
        7: "study, reflection and inner clarity", 8: "career, money, authority and measurable outcomes", 9: "completion, release and transition into a new cycle",
    }.get(num, "personal recalibration")


def stage_for_age(age: int) -> str:
    if age <= 20:
        return "Foundation Stage"
    if age <= 35:
        return "Launch Stage"
    if age <= 50:
        return "Consolidation Stage"
    return "Legacy Stage"


def stage_guidance(age: int, lp: int) -> str:
    title = stage_for_age(age)
    if title == "Foundation Stage":
        return "Your early task is identity formation: learning what is yours versus what was assigned by family, school and circumstance."
    if title == "Launch Stage":
        return "Your task is to choose a direction, test ambition in the real world and build credibility without copying someone else’s life."
    if title == "Consolidation Stage":
        return "Your task is to turn talent into assets: reputation, process, wealth, relationships and a body of work that can survive pressure."
    return "Your task is legacy: simplifying what matters, mentoring others and converting experience into durable contribution."


def normalised_number(num: int) -> int:
    return num if num in NUMBER_STYLE else reduce_number(num, keep_master=False)


def place_line(place: str | None, latitude: float | None, longitude: float | None) -> str:
    if not place:
        return "Birth place was not supplied, so the report uses date and name patterns only."
    if latitude is None or longitude is None:
        return f"Birth place captured as {place}. Latitude and longitude were not resolved, so no geographic anchor is used."
    ns = "northern" if latitude >= 0 else "southern"
    ew = "eastern" if longitude >= 0 else "western"
    return f"Birth place captured as {place} at {latitude:.6f}, {longitude:.6f}. The report records this as a {ns}/{ew} geographic anchor for identity reference."


def decision_style(att: int, bd: int) -> str:
    return f"Your first response style is {NUMBER_STYLE.get(normalised_number(att), 'adaptive')}, while your birth-day talent pattern is {NUMBER_STYLE.get(normalised_number(bd), 'practical')}. This means you usually decide best when the emotional impulse and the practical evidence are both visible."


def avoid_field(lp: int, expression: int) -> str:
    if lp in (1, 5, 8, 22):
        return "Avoid low-autonomy roles where every decision needs permission and the reward for competence is only more control from above."
    if lp in (2, 6, 9, 33):
        return "Avoid emotionally exploitative environments where care, loyalty or service are used to keep you underpaid or over-responsible."
    if lp in (3, 11):
        return "Avoid silent back-office roles with no room for communication, creativity, visibility or human influence."
    if lp in (4, 7):
        return "Avoid chaotic trend-chasing roles where depth, documentation and method are treated as obstacles."
    return "Avoid work that rewards your weakest habit and gives no outlet to your strongest talent."


def wealth_strategy(lp: int, expression: int, soul: int) -> List[str]:
    lp_norm = normalised_number(lp)
    if lp_norm in (1, 8):
        base = [
            "Build wealth through ownership, leadership and high-accountability decisions, not passive dependence on salary alone.",
            "Use negotiation, pricing power and asset creation; your money grows when you take clear responsibility for outcomes.",
            "Install emotional controls around impatience, dominance and risky overconfidence.",
        ]
    elif lp_norm in (4, 22):
        base = [
            "Build wealth through systems, property, infrastructure, process discipline and long compounding cycles.",
            "Document repeatable methods; the more reliable your operating model, the stronger your earning power.",
            "Do not become so risk-averse that opportunity expires before you act.",
        ]
    elif lp_norm in (3, 5):
        base = [
            "Build wealth through communication, markets, sales, distribution, media, travel, launches or audience-based work.",
            "Convert your energy into products, offers and channels instead of scattering it across unfinished ideas.",
            "Set financial rules before excitement enters; freedom needs a structure to protect it.",
        ]
    elif lp_norm in (2, 6, 9, 33):
        base = [
            "Build wealth through trust, relationships, service, reputation and community-oriented value.",
            "Charge properly for care, wisdom and reliability; generosity without pricing becomes resentment.",
            "Avoid rescuing people financially or professionally at the cost of your own foundation.",
        ]
    else:
        base = [
            "Build wealth through expertise, research, insight, advisory work, technology or knowledge assets.",
            "Your money grows when you become hard to replace, not when you become constantly available.",
            "Do not overanalyse every opportunity until the timing has passed.",
        ]
    base.append(f"Your name expression adds a {NUMBER_STYLE.get(normalised_number(expression))} style, so your best wealth channel should visibly use that operating mode.")
    base.append(f"Your soul urge is {NUMBER_STYLE.get(normalised_number(soul))}; your money decisions must respect that private motivation or you will sabotage success after achieving it.")
    return base


def next_five_years(dob: date, start_year: int) -> List[Dict[str, str]]:
    rows = []
    for year in range(start_year, start_year + 5):
        py = personal_year_number(dob, year)
        rows.append({"year": str(year), "number": str(py), "theme": personal_year_theme(py), "guidance": timeline_year_guidance(py)})
    return rows


def timeline_year_guidance(py: int) -> str:
    return {
        1: "Start decisively. Choose identity, direction and leadership instead of waiting for consensus.",
        2: "Slow down and align. Partnerships, patience and diplomacy matter more than speed.",
        3: "Become visible. Speak, publish, present, reconnect and convert ideas into expression.",
        4: "Build the base. Systems, contracts, discipline, health routines and financial order are the work.",
        5: "Move intelligently. Change, travel, market testing and calculated risk open the next door.",
        6: "Repair and take responsibility. Family, trust, home, care and reputation need attention.",
        7: "Study and refine. Reduce noise, learn deeply and make decisions from evidence, not pressure.",
        8: "Execute for results. Career, money, authority and measurable outcomes come to the front.",
        9: "Complete and release. Close loops, forgive what is over and prepare for the next cycle.",
    }.get(py, "Recalibrate and simplify.")


def make_brutal_line(lp: int, expression: int, age: int) -> str:
    lines = {
        1: "The uncomfortable truth: if you wait for approval, you will resent the people you asked permission from.",
        2: "The uncomfortable truth: being liked is not the same as being respected; your boundaries decide the difference.",
        3: "The uncomfortable truth: your gifts will not save you from the consequences of inconsistency.",
        4: "The uncomfortable truth: your need for control can become the very thing that blocks growth.",
        5: "The uncomfortable truth: freedom without discipline turns into repeated starting over.",
        6: "The uncomfortable truth: not everyone you rescue is grateful, and not every burden is yours.",
        7: "The uncomfortable truth: analysis can become a beautiful prison if you use it to avoid risk.",
        8: "The uncomfortable truth: achievement can become an addiction if you do not define enough.",
        9: "The uncomfortable truth: your compassion is powerful, but your life cannot be a museum of unfinished endings.",
        11: "The uncomfortable truth: intuition is not enough; your sensitivity needs structure or it becomes anxiety.",
        22: "The uncomfortable truth: the scale of your potential can scare you into planning forever.",
        33: "The uncomfortable truth: service becomes unhealthy when it is secretly powered by guilt.",
    }
    base = lines.get(lp, lines[reduce_number(lp, keep_master=False)])
    if expression in (4, 8, 22) and lp not in (4, 8, 22):
        base += " Your name pattern adds a stronger executive/building drive than your birth path alone suggests."
    elif expression in (3, 5) and lp not in (3, 5):
        base += " Your name pattern adds restlessness and communication energy, so routine must serve a larger story."
    return base


def destiny_map(lp: int, age: int) -> List[Dict[str, str]]:
    archetype = LIFE_PATHS[lp]
    return [
        {"stage": "0–20: Conditioning and early imprint", "focus": "Learning the emotional script you inherited and where you first felt capable or constrained.", "watchout": "Do not let early labels become permanent limits."},
        {"stage": "21–35: Testing and self-definition", "focus": f"Experimenting until the {archetype['title'].lower()} pattern finds a field where it can win.", "watchout": "Avoid copying external success markers that do not fit your temperament."},
        {"stage": "36–50: Authority and consequence", "focus": "Turning experience into authority, assets and a repeatable operating model.", "watchout": "What you tolerate in this phase becomes the culture around you."},
        {"stage": "51+: Legacy and simplification", "focus": "Teaching, mentoring, investing and making your work outlive your daily effort.", "watchout": "Release battles that no longer deserve your energy."},
    ]


def _norm_deg(v: float) -> float:
    return v % 360.0


def _julian_day(dt_utc: datetime) -> float:
    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24.0
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


def _approx_utc_offset_hours(longitude: float | None, birth_place: str | None) -> float:
    place = (birth_place or "").lower()
    if place and any(k in place for k in ["india", "karnataka", "bengaluru", "bangalore", "mysuru", "chennai", "hyderabad", "mumbai", "delhi", "kerala", "tamil nadu", "andhra", "telangana"]):
        return 5.5
    if longitude is None:
        return 0.0
    return round(longitude / 15.0 * 2) / 2


def _sun_longitude(jd: float) -> float:
    d = jd - 2451545.0
    g = math.radians(_norm_deg(357.529 + 0.98560028 * d))
    q = _norm_deg(280.459 + 0.98564736 * d)
    L = q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)
    return _norm_deg(L)


def _moon_longitude(jd: float) -> float:
    d = jd - 2451545.0
    L0 = _norm_deg(218.316 + 13.176396 * d)
    Mm = math.radians(_norm_deg(134.963 + 13.064993 * d))
    Ms = math.radians(_norm_deg(357.529 + 0.98560028 * d))
    D = math.radians(_norm_deg(297.850 + 12.190749 * d))
    lon = L0 + 6.289 * math.sin(Mm) + 1.274 * math.sin(2 * D - Mm) + 0.658 * math.sin(2 * D) + 0.214 * math.sin(2 * Mm) - 0.186 * math.sin(Ms)
    return _norm_deg(lon)


def _ayanamsa_approx(dt_utc: datetime) -> float:
    return 23.85675 + 0.013968 * ((dt_utc.year - 2000) + (dt_utc.timetuple().tm_yday / 365.25))


def _zodiac_name(lon: float) -> str:
    idx = int(_norm_deg(lon) // 30)
    return ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][idx]


def astronomy_snapshot(dob: date, birth_time: dt_time | None, latitude: float | None, longitude: float | None, birth_place: str | None) -> Dict[str, Any]:
    local_dt = datetime.combine(dob, birth_time or dt_time(12, 0))
    offset = _approx_utc_offset_hours(longitude, birth_place)
    dt_utc = local_dt - timedelta(hours=offset)
    jd = _julian_day(dt_utc)
    sun_lon = _sun_longitude(jd)
    moon_lon = _moon_longitude(jd)
    ayan = _ayanamsa_approx(dt_utc)
    sidereal_moon = _norm_deg(moon_lon - ayan)
    sidereal_sun = _norm_deg(sun_lon - ayan)
    moon_rashi_idx = int(sidereal_moon // 30)
    sun_rashi_idx = int(sidereal_sun // 30)
    nak_idx = int(sidereal_moon // (360 / 27))
    nak_name, nak_quality = NAKSHATRAS[nak_idx]
    elong = _norm_deg(moon_lon - sun_lon)
    phase = 0.5 * (1 - math.cos(math.radians(elong)))
    tithi_num = int(elong // 12) + 1
    paksha = "Shukla Paksha" if tithi_num <= 15 else "Krishna Paksha"
    tithi_in_half = tithi_num if tithi_num <= 15 else tithi_num - 15
    weekday_name, ruler, ruler_meaning = WEEKDAY_RULERS[dob.weekday()]
    return {
        "birth_time": birth_time.strftime("%H:%M") if birth_time else None,
        "used_default_time": birth_time is None,
        "weekday": weekday_name,
        "weekday_ruler": ruler,
        "weekday_ruler_meaning": ruler_meaning,
        "sun_sign": _zodiac_name(sun_lon),
        "sidereal_sun_rashi": RASHIS[sun_rashi_idx],
        "moon_rashi": RASHIS[moon_rashi_idx],
        "nakshatra": nak_name,
        "nakshatra_quality": nak_quality,
        "moon_phase": "Waxing" if phase < 0.5 and tithi_num <= 15 else ("Full Moon phase" if abs(phase - 1) < 0.07 else ("Waning" if tithi_num > 15 else "Waxing near Full Moon")),
        "illumination_pct": round(phase * 100, 1),
        "tithi": f"{paksha} · Tithi {tithi_in_half}",
        "summary": f"Approximate Vedic-style snapshot: Moon in {RASHIS[moon_rashi_idx]}, Nakshatra {nak_name}, {paksha} Tithi {tithi_in_half}. Western Sun sign: {_zodiac_name(sun_lon)}.",
        "calculation_note": "Astronomy/constellation items are approximated from date, time and place for readable interpretation, not a certified astrological chart.",
    }


def birthday_uniqueness(dob: date, birth_time: dt_time | None, astro: Dict[str, Any]) -> List[str]:
    day_of_year = dob.timetuple().tm_yday
    leap = "a leap year" if (dob.year % 4 == 0 and (dob.year % 100 != 0 or dob.year % 400 == 0)) else "a common year"
    digits = [c for c in dob.strftime("%d%m%Y") if c.isdigit()]
    freq = {d: digits.count(d) for d in sorted(set(digits))}
    dominant = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[0]
    seasonal_points = [(date(dob.year, 3, 20), "March equinox"), (date(dob.year, 6, 21), "June solstice"), (date(dob.year, 9, 22), "September equinox"), (date(dob.year, 12, 21), "December solstice")]
    nearest = min(seasonal_points, key=lambda p: abs((dob - p[0]).days))
    days_from = abs((dob - nearest[0]).days)
    lines = [
        f"You were born on a {astro['weekday']} — traditionally linked with {astro['weekday_ruler']} and themes of {astro['weekday_ruler_meaning']}.",
        f"Your birthday was the {day_of_year}{'st' if day_of_year % 10 == 1 and day_of_year % 100 != 11 else 'nd' if day_of_year % 10 == 2 and day_of_year % 100 != 12 else 'rd' if day_of_year % 10 == 3 and day_of_year % 100 != 13 else 'th'} day of {leap}.",
        f"Your date carries a strong digit signature around '{dominant[0]}', appearing {dominant[1]} times, which intensifies that number’s symbolic tone in numerology.",
        f"Seasonally, your birth was {days_from} day(s) from the {nearest[1]}, giving the day a clear transition-season imprint.",
    ]
    if birth_time:
        lines.append(f"The recorded time of birth, {birth_time.strftime('%H:%M')}, gives a more personalised constellation snapshot than date-only analysis.")
    return lines


def relationship_windows(dob: date, start_year: int | None = None) -> List[str]:
    start_year = start_year or date.today().year
    wins = []
    for year in range(start_year, start_year + 8):
        py = personal_year_number(dob, year)
        if py in (2, 6, 9):
            label = {2: "partnership formation", 6: "commitment / family decisions", 9: "closure or karmic relationship reset"}[py]
            wins.append(f"{year} (Personal Year {py}: {label})")
    return wins[:4]


def love_life_prediction(profile: Dict[str, Any], astro: Dict[str, Any]) -> str:
    lp = profile["life_path"]
    soul = profile["soul"]
    base = {
        1: "You love intensely when respect is present, but you withdraw fast when control or dependency appears.",
        2: "You are a bond-builder; love deepens when emotional steadiness and reassurance are present.",
        3: "Your love life thrives on conversation, playfulness and visible affection.",
        4: "You take time to trust, but once committed you value loyalty, rhythm and reliability.",
        5: "You need chemistry plus space. Possessiveness is usually the fastest way to cool your interest.",
        6: "You naturally move toward family-minded love, care and emotional responsibility.",
        7: "You need privacy, honesty and mental depth more than surface romance.",
        8: "You are drawn to strong partners, but real love begins only when power stops becoming a test.",
        9: "You often experience love as a path of healing, endings and expansion of compassion.",
        11: "Your love life can feel fated or unusually intense; grounding and emotional safety are essential.",
        22: "You often build love slowly through shared goals, reliability and long-range trust.",
        33: "You love with enormous care, but must avoid turning devotion into self-erasure.",
    }[lp]
    return base + f" Your private emotional driver is {NUMBER_STYLE.get(soul)}, so your deepest attachments must honour that inner need."


def marriage_prediction(profile: Dict[str, Any], astro: Dict[str, Any]) -> Dict[str, Any]:
    lp = profile["life_path"]
    wins = relationship_windows(profile["dob"])
    tendencies = {
        1: "Marriage works best for you when there is mutual respect, separate dignity and no emotional power struggle.",
        2: "Marriage is one of your main life classrooms; communication and emotional steadiness determine its quality.",
        3: "Marriage needs warmth, humour and active friendship, not only duty.",
        4: "Marriage tends to stabilise you when routines, trust and accountability are strong.",
        5: "Marriage must leave room for individuality, movement and reinvention or you will feel caged.",
        6: "Marriage is strongly emphasised in your pattern and often links directly with life purpose, family and responsibility.",
        7: "Marriage succeeds when your inner space is respected and emotional honesty is clean.",
        8: "Marriage is likely to test power, money and trust; mature partnership makes you stronger, ego contests make it heavy.",
        9: "Marriage may come after major emotional lessons; when it works, it has a healing and expansive quality.",
        11: "Marriage can feel unusually karmic or fated; strong boundaries keep intensity from becoming instability.",
        22: "Marriage tends to become part of a larger life-building mission: home, assets, institution or legacy.",
        33: "Marriage works best when compassion is balanced by boundaries and shared service, not martyrdom.",
    }[lp]
    return {
        "body": tendencies,
        "bullets": [
            f"South Indian / Vedic-style read: Moon in {astro['moon_rashi']} and Nakshatra {astro['nakshatra']} suggest a relational style marked by {astro['nakshatra_quality']}.",
            "The strongest marriage windows are usually activated in Personal Years 2, 6 and 9.",
            f"Your next likely relationship activation windows: {', '.join(wins) if wins else 'watch the next 2, 6 or 9 personal years.'}",
        ],
    }


def _first_name(name: str) -> str:
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    return parts[0] if parts else name


def name_insight(name: str, expression: int, soul: int) -> Dict[str, Any]:
    first = _first_name(name)
    key = re.sub(r"[^a-z]", "", first.lower())
    known = NAME_MEANINGS.get(key)
    if known:
        meaning = known["meaning"]
        origin = known["origin"]
        commonness = known["commonness"]
        confidence = "High"
    else:
        # Fallback: useful when the exact name is not in the embedded database.
        meaning = (
            f"No exact dictionary meaning is available in the offline name database for '{first}'. "
            f"The app therefore reads the name through numerology: Expression {expression} suggests a {NUMBER_STYLE.get(normalised_number(expression))} outer signature, "
            f"while Soul Urge {soul} suggests a {NUMBER_STYLE.get(normalised_number(soul))} inner motivation."
        )
        origin = "Not confirmed by offline database"
        commonness = _commonness_from_name_shape(first)
        confidence = "Estimated"
    return {
        "display_name": first,
        "meaning": meaning,
        "origin": origin,
        "commonness": commonness,
        "confidence": confidence,
        "name_number_read": f"Name Expression {expression} gives the name a {NUMBER_STYLE.get(normalised_number(expression))} public tone; Soul Urge {soul} adds a {NUMBER_STYLE.get(normalised_number(soul))} private driver.",
    }


def _commonness_from_name_shape(first: str) -> str:
    clean = re.sub(r"[^A-Za-z]", "", first or "")
    if not clean:
        return "Unknown"
    if len(clean) <= 4:
        return "Likely short and memorable; exact commonness not available offline"
    if clean.lower().endswith(("an", "ya", "vi", "sh", "raj", "deep", "kumar")):
        return "Likely familiar in Indian naming patterns; exact ranking not available offline"
    if len(clean) >= 9:
        return "Likely less common as a short everyday name; exact ranking not available offline"
    return "Moderately familiar sounding; exact ranking not available offline"


def lucky_profile(lp: int, birth_day: int, nakshatra: str) -> Dict[str, str]:
    base = LUCKY_PROFILE_BY_NUMBER.get(lp) or LUCKY_PROFILE_BY_NUMBER.get(normalised_number(lp), LUCKY_PROFILE_BY_NUMBER[1])
    # Keep the result readable and stable. The life path controls the main lucky set;
    # birth day and nakshatra add a secondary cue without making the output noisy.
    return {
        "lucky_color": base["color"],
        "lucky_fruit": base["fruit"],
        "lucky_day": base["day"],
        "lucky_number": base["number"],
        "secondary_number": str(normalised_number(birth_day)),
        "why": f"Primary lucky items are mapped from Life Path {lp}; secondary number {normalised_number(birth_day)} comes from the birth day. Nakshatra cue used: {nakshatra}.",
    }


def children_prediction(profile: Dict[str, Any], astro: Dict[str, Any]) -> str:
    lp = profile["life_path"]
    mode = {
        1: "You are likely to parent by teaching independence and courage.",
        2: "You are likely to create a highly responsive emotional bond with children.",
        3: "You tend to connect with children through humour, stories and expressive warmth.",
        4: "You often show care through structure, reliability and practical protection.",
        5: "You may raise children to be adaptable, curious and confident with change.",
        6: "Children and family themes are strongly highlighted; nurturing and responsibility are major lessons here.",
        7: "You may be selective or later in family timing, but likely to parent with depth and thoughtful guidance.",
        8: "You tend to emphasise security, competence and resilience in children.",
        9: "Your child-bond pattern is compassionate and mentoring; you may influence children beyond only your own family line.",
        11: "Children can deepen your spiritual and emotional maturity; sensitivity must be handled gently.",
        22: "You often parent through long-range planning, provision and legacy building.",
        33: "Your nurturing force is naturally strong; children may become one of the ways your teaching nature expresses itself.",
    }[lp]
    return mode + " This forecast includes biological, adopted or mentorship-style child bonds, because your chart primarily describes the pattern of care and legacy rather than only one family model."


def build_common_profile(name: str, dob_raw: str, birth_place: str | None = None, latitude: float | None = None, longitude: float | None = None, birth_time_raw: str | None = None) -> Dict[str, Any]:
    clean_name = re.sub(r"\s+", " ", (name or "").strip())
    if len(clean_name) < 2:
        raise ValueError("Name must contain at least 2 characters.")
    dob = parse_dob(dob_raw)
    birth_time = parse_birth_time(birth_time_raw)
    today = date.today()
    age = age_on_today(dob, today)
    lp = life_path_number(dob)
    bd = birth_day_number(dob)
    att = attitude_number(dob)
    py = personal_year_number(dob, today.year)
    nn = name_numbers(clean_name)
    archetype = LIFE_PATHS.get(lp, LIFE_PATHS[reduce_number(lp, keep_master=False)])
    expression = normalised_number(nn["expression"])
    soul = normalised_number(nn["soul_urge"])
    personality = normalised_number(nn["personality"])
    astro = astronomy_snapshot(dob, birth_time, latitude, longitude, birth_place)
    name_meta = name_insight(clean_name, expression, soul)
    lucky_meta = lucky_profile(lp, bd, astro["nakshatra"])

    psychology_profile = [
        f"Your life-path pattern is {archetype['title']}: {archetype['core']}",
        f"Your name expression number suggests an outer operating style that is {NUMBER_STYLE.get(expression)}.",
        f"Your soul-urge pattern points to a private motivation that is {NUMBER_STYLE.get(soul)}.",
        f"Your social/personality number suggests people may first experience you as {NUMBER_STYLE.get(personality)}.",
        MONTH_PATTERNS[dob.month],
        place_line(birth_place, latitude, longitude),
        astro["summary"],
    ]
    hidden_strengths = archetype["strengths"] + [f"ability to use your {stage_for_age(age).lower()} experience as leverage", f"a name-pattern advantage in {NUMBER_STYLE.get(expression, 'self-expression')}"]
    weaknesses = archetype["weaknesses"] + ["believing that your strongest trait should solve every problem", "staying too long in patterns that are familiar but no longer useful"]
    purpose_sentence = f"The most important purpose to pursue is this: {archetype['purpose']} Do it through a field where your {NUMBER_STYLE.get(expression)} style can create visible, useful results."
    return {
        "clean_name": clean_name, "dob": dob, "birth_time": birth_time, "today": today, "age": age, "life_path": lp, "birth_day": bd,
        "attitude": att, "personal_year": py, "name_numbers": nn, "archetype": archetype, "expression": expression, "soul": soul,
        "personality": personality, "psychology_profile": psychology_profile, "hidden_strengths": hidden_strengths, "weaknesses": weaknesses,
        "purpose_sentence": purpose_sentence, "birth_place": birth_place, "latitude": latitude, "longitude": longitude,
        "astro": astro, "birthday_unique": birthday_uniqueness(dob, birth_time, astro),
        "name_insight": name_meta, "lucky_profile": lucky_meta,
    }


def section(title: str, body: str | None = None, bullets: List[str] | None = None, table: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    return {"title": title, "body": body or "", "bullets": bullets or [], "table": table or []}


def build_sections(profile: Dict[str, Any], analysis_type: str) -> List[Dict[str, Any]]:
    lp = profile["life_path"]
    archetype = profile["archetype"]
    expression = profile["expression"]
    soul = profile["soul"]
    age = profile["age"]
    dob = profile["dob"]
    today = profile["today"]
    weaknesses = profile["weaknesses"]
    strengths = profile["hidden_strengths"]
    astro = profile["astro"]
    marriage = marriage_prediction(profile, astro)
    children = children_prediction(profile, astro)
    love = love_life_prediction(profile, astro)
    name_meta = profile["name_insight"]
    lucky = profile["lucky_profile"]
    time_label = profile["birth_time"].strftime("%H:%M") if profile.get("birth_time") else "not supplied"
    place_label = profile["birth_place"] or "not supplied"
    coord_label = (
        f"{profile['latitude']:.6f}, {profile['longitude']:.6f}"
        if profile.get("latitude") is not None and profile.get("longitude") is not None
        else "not resolved"
    )
    common_intro = [
        section("Personalised Input Signature", bullets=[
            f"This report is generated for {profile['clean_name']} using DOB {dob.strftime('%d %B %Y')} and time of birth {time_label}.",
            f"Birth place anchor: {place_label}; latitude/longitude used: {coord_label}.",
            f"Core calculation mix: Life Path {lp}, Birth Day {profile['birth_day']}, Attitude {profile['attitude']}, Name Expression {expression}, Soul Urge {soul}.",
            f"Sky calculation mix: {astro['weekday']} / {astro['weekday_ruler']}, Moon Rashi {astro['moon_rashi']}, Nakshatra {astro['nakshatra']}, Tithi {astro['tithi']}.",
        ]),
        section("Name Meaning & Commonness", bullets=[
            f"Best meaning for {name_meta['display_name']}: {name_meta['meaning']}",
            f"Likely origin: {name_meta['origin']}",
            f"How common: {name_meta['commonness']}",
            f"Confidence: {name_meta['confidence']}",
            f"Personal name-number read for {profile['clean_name']}: {name_meta['name_number_read']}",
        ]),
        section("Lucky Signals", bullets=[
            f"Lucky color: {lucky['lucky_color']} — selected from Life Path {lp}, then checked against Nakshatra {astro['nakshatra']}.",
            f"Lucky fruit: {lucky['lucky_fruit']} — used as a symbolic abundance cue, not a medical or dietary recommendation.",
            f"Lucky day: {lucky['lucky_day']} — compared with actual birth weekday {astro['weekday']}.",
            f"Lucky number: {lucky['lucky_number']} with secondary number {lucky['secondary_number']} from birth day {profile['birth_day']}.",
            lucky["why"],
        ]),
    ]

    if analysis_type == "soul_purpose":
        actions = [
            "Name the one contribution you want your work to be remembered for and build weekly activity around it.",
            "Stop confusing duty with destiny; duty drains when it has no chosen meaning behind it.",
            "Turn your strongest trait into a serviceable craft, not just a personality habit.",
            "Choose one audience, community or problem where your life experience gives you unusual authority.",
            "Build a repeatable body of work: writing, systems, mentorship, products, institutions or service platforms.",
        ]
        return common_intro + [
            section("Central Mission", f"Your central mission carries the tone of {archetype['title']}. {archetype['purpose']}"),
            section("Lessons You Are Here to Learn", bullets=[archetype["shadow"], *weaknesses[:4]]),
            section("Contribution to the World", f"Your contribution is strongest when {NUMBER_STYLE.get(expression)} becomes useful to others. You are not here merely to survive your pattern; you are here to refine it until it becomes value."),
            section("South Indian Reflection Layer", bullets=[f"Janma Nakshatra: {astro['nakshatra']} — {astro['nakshatra_quality']}", f"Moon Rashi: {astro['moon_rashi']}", f"Tithi and lunar tone: {astro['tithi']} · illumination {astro['illumination_pct']}%"]),
            section("Clear Guidance", bullets=actions),
            section("Purpose Statement", profile["purpose_sentence"]),
        ]

    if analysis_type == "professional_destiny":
        careers = CAREER_BUCKETS.get(lp, CAREER_BUCKETS[reduce_number(lp, keep_master=False)])
        return common_intro + [
            section("Natural Talents", bullets=strengths[:6]),
            section("Decision-Making Style", decision_style(profile["attitude"], profile["birth_day"])),
            section("Hidden Motivations", f"Privately, you are motivated by a {NUMBER_STYLE.get(soul)} inner need. You will not stay committed to work that violates this, even if it looks impressive externally."),
            section("3 Career or Business Paths for Extraordinary Success", bullets=careers),
            section("South Indian Career Signal", bullets=[f"Birth weekday ruler: {astro['weekday_ruler']} — {astro['weekday_ruler_meaning']}", f"Nakshatra {astro['nakshatra']} adds a tone of {astro['nakshatra_quality']}", f"Moon Rashi: {astro['moon_rashi']}"]),
            section("Field to Avoid", avoid_field(lp, expression)),
            section("Professional Warning", make_brutal_line(lp, expression, age)),
        ]

    if analysis_type == "relationships":
        compatible = COMPATIBILITY.get(lp, COMPATIBILITY[reduce_number(lp, keep_master=False)])
        partner = f"The partner who helps you become your best version is emotionally mature, respects your {NUMBER_STYLE.get(expression)} operating style, and does not punish you for the core rhythm of {archetype['title'].lower()}. They should be strong enough to challenge your blind spots, warm enough to make honesty safe, and stable enough that love does not become a performance."
        return common_intro + [
            section("Most Compatible People", f"You are most compatible with {compatible}."),
            section("Love Life Prediction", love),
            section("Marriage Prediction", marriage["body"], bullets=marriage["bullets"]),
            section("Children Prediction", children),
            section("Love Lessons", bullets=[archetype["shadow"], *weaknesses[:4]]),
            section("Role of Relationships in Your Life Path", "Relationships are not a side chapter for you; they are the mirror that reveals whether your strongest trait is becoming wisdom or becoming defence."),
            section("South Indian Compatibility Layer", bullets=[f"Moon Rashi: {astro['moon_rashi']}", f"Janma Nakshatra: {astro['nakshatra']} — {astro['nakshatra_quality']}", astro['calculation_note']]),
            section("Exact Partner Description", partner),
            section("Relationship Warning", make_brutal_line(lp, expression, age)),
        ]

    if analysis_type == "wealth_abundance":
        strategy = wealth_strategy(lp, expression, soul)
        blockers = [f"Overusing the shadow side of {archetype['title'].lower()}: {archetype['shadow']}", *weaknesses[:4], "Making money decisions from fear, guilt, impatience or the need to prove worth."]
        return common_intro + [
            section("Natural Financial Personality", f"Your wealth pattern is shaped by {archetype['title']}. You attract abundance when your work creates visible value through {NUMBER_STYLE.get(expression)} execution."),
            section("How You Attract Wealth", bullets=strategy[:3]),
            section("Mistakes Blocking Economic Growth", bullets=blockers),
            section("South Indian Abundance Layer", bullets=[f"Birth weekday ruler: {astro['weekday_ruler']}", f"Moon Rashi: {astro['moon_rashi']}", f"Nakshatra: {astro['nakshatra']} — {astro['nakshatra_quality']}"]),
            section("Wealth Strategy That Fits You", bullets=strategy[3:]),
            section("Abundance Rule", "The right wealth path should make you more disciplined and more alive at the same time. If it gives money but destroys your nature, you will eventually resist it."),
        ]

    if analysis_type == "future_timeline":
        next_years = next_five_years(dob, today.year)
        return common_intro + [
            section("Past Pattern", "The early years were about conditioning: learning what the world rewarded, what it punished, and which part of your nature had to become stronger to survive."),
            section("Present Stage", f"You are in the {stage_for_age(age)}. {stage_guidance(age, lp)}"),
            section("Key Turning Points", bullets=[
                "0–20: identity imprint, family scripts, education and first confidence wounds or wins.",
                "21–35: experimentation, career identity, independence and the first serious consequences of choices.",
                "36–50: authority, assets, reputation, relationships and the pressure to stop wasting talent.",
                "51+: legacy, simplification, mentoring, selective battles and contribution beyond daily ambition.",
            ]),
            section("Love, Marriage and Family Timeline", bullets=[f"Love life signature: {love}", f"Marriage focus: {marriage['body']}", f"Likely relationship activation windows: {', '.join(relationship_windows(dob, today.year))}", f"Children theme: {children}"]),
            section("Next 5 Years Roadmap", table=next_years),
            section("Sky Pattern at Birth", bullets=[f"Sun Sign: {astro['sun_sign']}", f"Moon Rashi: {astro['moon_rashi']}", f"Nakshatra: {astro['nakshatra']} — {astro['nakshatra_quality']}", f"Tithi: {astro['tithi']}"]),
            section("Roadmap Warning", make_brutal_line(lp, expression, age)),
        ]

    return common_intro + [
        section("Core Personality", f"For {profile['clean_name']}, the core pattern is {archetype['title']}: {archetype['core']} This is modified by Name Expression {expression}, Birth Day {profile['birth_day']} and Nakshatra {astro['nakshatra']}.",),
        section("Psychological Pattern", bullets=profile["psychology_profile"]),
        section("Hidden Strengths", bullets=[*strengths, f"Personal modifier: {profile['clean_name']} combines Life Path {lp} with Name Expression {expression}, so the strengths show best when {NUMBER_STYLE.get(expression)} behaviour is used deliberately."]),
        section("Weaknesses & Blind Spots", bullets=[*weaknesses, f"Personal watchout: in Personal Year {profile['personal_year']}, the current pressure point is {personal_year_theme(profile['personal_year'])}."]),
        section("What Was Unique About Your Birthday", bullets=profile["birthday_unique"]),
        section("South Indian Prediction Logic", bullets=[f"Janma Nakshatra: {astro['nakshatra']} — {astro['nakshatra_quality']}", f"Moon Rashi: {astro['moon_rashi']}", f"Sidereal Sun Rashi: {astro['sidereal_sun_rashi']}", f"Birth weekday ruler: {astro['weekday_ruler']} — {astro['weekday_ruler_meaning']}", f"Tithi / Moon phase: {astro['tithi']} · {astro['moon_phase']} ({astro['illumination_pct']}% illumination)", astro['calculation_note']]),
        section("Readable Constellation Snapshot", astro["summary"]),
        section("Love Life Prediction", love),
        section("Marriage Prediction", marriage["body"], bullets=marriage["bullets"]),
        section("Children Prediction", children),
        section("Brutally Honest Mirror", make_brutal_line(lp, expression, age)),
        section("Destiny Map", table=destiny_map(lp, age)),
        section("Most Important Purpose to Pursue", profile["purpose_sentence"]),
        section("Best Work Direction", archetype["work"]),
    ]


def build_full_text(profile: Dict[str, Any], prompt_meta: Dict[str, str], analysis_type: str, sections: List[Dict[str, Any]]) -> str:
    dob = profile["dob"]
    nn = profile["name_numbers"]
    astro = profile["astro"]
    lines = [
        f"{prompt_meta['title'].upper()}", "",
        f"Name: {profile['clean_name']}",
        f"Date of Birth: {dob.strftime('%d %B %Y')}",
        f"Time of Birth: {astro['birth_time'] or 'Not supplied (defaulted to midday for astronomy snapshot)'}",
        f"Age: {profile['age']}",
        f"Birth Place: {profile['birth_place'] or 'Not supplied'}",
    ]
    if profile["latitude"] is not None and profile["longitude"] is not None:
        lines.append(f"Latitude / Longitude: {profile['latitude']:.6f}, {profile['longitude']:.6f}")
    lines.extend([
        f"Life Path Number: {profile['life_path']} — {profile['archetype']['title']}",
        f"Birth Day Number: {profile['birth_day']}",
        f"Attitude Number: {profile['attitude']}",
        f"Name Expression Number: {nn['expression']}",
        f"Soul Urge Number: {nn['soul_urge']}",
        f"Personality Number: {nn['personality']}",
        f"Name Meaning: {profile['name_insight']['meaning']}",
        f"Name Commonness: {profile['name_insight']['commonness']}",
        f"Lucky Color / Fruit / Day / Number: {profile['lucky_profile']['lucky_color']} / {profile['lucky_profile']['lucky_fruit']} / {profile['lucky_profile']['lucky_day']} / {profile['lucky_profile']['lucky_number']}",
        f"Personal Year {profile['today'].year}: {profile['personal_year']} — {personal_year_theme(profile['personal_year'])}",
        f"Nakshatra / Moon Rashi: {astro['nakshatra']} / {astro['moon_rashi']}",
        f"Tithi / Moon Phase: {astro['tithi']} / {astro['moon_phase']} ({astro['illumination_pct']}% illuminated)",
        "",
    ])
    for s in sections:
        lines.append(s["title"])
        if s.get("body"):
            lines.append(s["body"])
        for bullet in s.get("bullets", []):
            lines.append(f"- {bullet}")
        if s.get("table"):
            for row in s["table"]:
                if "year" in row:
                    lines.append(f"- {row['year']} | Personal Year {row['number']} | {row['theme']} | {row['guidance']}")
                else:
                    lines.append("- " + " | ".join(str(v) for v in row.values()))
        lines.append("")
    lines.append("Note")
    lines.append("This is a reflective interpretation generated from numerology-style logic, personality patterning and approximate astronomy-inspired / South Indian style symbolism. It is not a scientific, medical, psychological, legal or financial assessment.")
    return "\n".join(lines).strip()


def build_report(name: str, dob_raw: str, analysis_type: str = "life_path", birth_place: str | None = None, latitude: float | None = None, longitude: float | None = None, birth_time: str | None = None) -> Dict[str, Any]:
    analysis_type = (analysis_type or "life_path").strip()
    if analysis_type not in PROMPT_OPTIONS:
        raise ValueError("Unknown analysis type selected.")
    profile = build_common_profile(name, dob_raw, birth_place=birth_place, latitude=latitude, longitude=longitude, birth_time_raw=birth_time)
    prompt_meta = PROMPT_OPTIONS[analysis_type]
    sections = build_sections(profile, analysis_type)
    full_text = build_full_text(profile, prompt_meta, analysis_type, sections)
    nn = profile["name_numbers"]
    astro = profile["astro"]
    return {
        "input": {
            "name": profile["clean_name"], "dob": profile["dob"].isoformat(), "birth_time": astro["birth_time"],
            "birth_place": profile["birth_place"], "latitude": profile["latitude"], "longitude": profile["longitude"], "analysis_type": analysis_type,
        },
        "prompt": {"title": prompt_meta["title"], "short": prompt_meta.get("short", "")},
        "calculations": {
            "age": profile["age"], "life_path": profile["life_path"], "life_path_title": profile["archetype"]["title"],
            "birth_day": profile["birth_day"], "attitude": profile["attitude"], "personal_year": profile["personal_year"],
            "personal_year_theme": personal_year_theme(profile["personal_year"]), "name_expression": nn["expression"],
            "soul_urge": nn["soul_urge"], "personality": nn["personality"], "nakshatra": astro["nakshatra"], "moon_rashi": astro["moon_rashi"],
            "sun_sign": astro["sun_sign"], "tithi": astro["tithi"],
            "name_meaning": profile["name_insight"]["meaning"], "name_commonness": profile["name_insight"]["commonness"],
            "lucky_color": profile["lucky_profile"]["lucky_color"], "lucky_fruit": profile["lucky_profile"]["lucky_fruit"],
            "lucky_day": profile["lucky_profile"]["lucky_day"], "lucky_number": profile["lucky_profile"]["lucky_number"],
        },
        "report": {
            "title": prompt_meta["title"], "sections": sections, "core_personality": profile["archetype"]["core"],
            "psychology_profile": profile["psychology_profile"], "hidden_strengths": profile["hidden_strengths"], "weaknesses": profile["weaknesses"],
            "shadow": profile["archetype"]["shadow"], "brutal_honesty": make_brutal_line(profile["life_path"], profile["expression"], profile["age"]),
            "destiny_map": destiny_map(profile["life_path"], profile["age"]), "current_stage": {"title": stage_for_age(profile["age"]), "guidance": stage_guidance(profile["age"], profile["life_path"])},
            "purpose": profile["purpose_sentence"], "best_work_direction": profile["archetype"]["work"], "full_text": full_text,
            "astronomy": astro, "birthday_unique": profile["birthday_unique"],
            "name_insight": profile["name_insight"], "lucky_profile": profile["lucky_profile"],
        },
        "disclaimer": "Reflective/entertainment use only. Not scientific or deterministic.",
    }
