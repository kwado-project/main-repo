"""Seed reference data and clearly-labelled SAMPLE learning content.

    python manage.py seed            # idempotent
    python manage.py seed --admin you@example.com

All seeded questions are original Kwado practice questions (not official past
questions) and are marked as sample content in their `source` field.
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import StudentProfile, User
from apps.ai_tutor.models import AIConfig
from apps.examinations.models import Examination, ExamSubject, Subject, Topic
from apps.gamification.models import Badge, Mission, Streak
from apps.learning.models import LearningPath, LearningPathNode, Lesson
from apps.questions.models import AnswerKey, Question, QuestionOption
from apps.wallet.models import ActivityPricing, CreditPackage
from apps.wallet.services import DEFAULT_PRICING, get_wallet

from .seed_content import HANDWRITTEN, LESSONS

SAMPLE_SOURCE = "Kwado original practice question (sample content)"

SUBJECTS = {
    "English Language": ("languages", "#0EA5E9", ["Comprehension", "Summary Writing", "Lexis and Structure",
                                                 "Concord", "Oral English", "Figures of Speech"]),
    "Mathematics": ("sigma", "#16A34A", ["Number Bases", "Indices and Logarithms", "Quadratic Equations",
                                         "Percentages and Ratios", "Simultaneous Equations", "Statistics",
                                         "Probability", "Mensuration"]),
    "Physics": ("atom", "#8B5CF6", ["Motion", "Newton's Laws", "Work, Energy and Power", "Waves",
                                    "Current Electricity", "Heat Energy"]),
    "Chemistry": ("flask-conical", "#F59E0B", ["Atomic Structure", "Chemical Bonding", "Stoichiometry",
                                               "Acids, Bases and Salts", "Organic Chemistry", "Electrolysis"]),
    "Biology": ("leaf", "#22C55E", ["Cell Biology", "Nutrition", "Genetics", "Ecology", "Reproduction",
                                    "Transport Systems"]),
    "Economics": ("trending-up", "#EF4444", ["Demand and Supply", "Elasticity", "Production", "Money and Banking",
                                             "Market Structures", "National Income"]),
    "Government": ("landmark", "#6366F1", ["Constitution", "Federalism", "Arms of Government", "Electoral Systems"]),
    "Literature in English": ("book-open", "#EC4899", ["Drama", "Prose", "Poetry", "Literary Devices"]),
    "Geography": ("globe", "#14B8A6", ["Map Reading", "Climate", "Population", "Rocks and Landforms"]),
    "Commerce": ("store", "#F97316", ["Trade", "Banking", "Insurance", "Transportation"]),
    "Agricultural Science": ("sprout", "#65A30D", ["Soil Science", "Crop Production", "Animal Husbandry"]),
    "Civic Education": ("users", "#0891B2", ["Citizenship", "Human Rights", "Rule of Law"]),
    "Further Mathematics": ("pi", "#15803D", ["Sets and Logic", "Matrices", "Calculus"]),
    "Christian Religious Studies": ("church", "#A855F7", ["Old Testament", "New Testament"]),
    "Islamic Studies": ("moon-star", "#059669", ["Qur'an", "Hadith"]),
    "Financial Accounting": ("calculator", "#DC2626", ["Double Entry", "Final Accounts", "Bank Reconciliation"]),
}

SCIENCE = ["Physics", "Chemistry", "Biology", "Further Mathematics", "Agricultural Science", "Geography"]
ARTS = ["Literature in English", "Government", "Christian Religious Studies", "Islamic Studies", "Civic Education"]
COMMERCIAL = ["Economics", "Commerce", "Financial Accounting"]
ALL_ELECTIVES = SCIENCE + ARTS + COMMERCIAL

EXAMS = [
    # code, name, full name, min, max, compulsory, color, mock minutes, note
    ("jamb", "JAMB UTME", "Unified Tertiary Matriculation Examination", 4, 4, ["English Language"], "#16A34A", 120,
     "Use of English plus three subjects relevant to your course."),
    ("waec", "WAEC WASSCE", "West African Senior School Certificate Examination", 7, 9,
     ["English Language", "Mathematics", "Civic Education"], "#0EA5E9", 180,
     "English, Mathematics and Civic Education are compulsory."),
    ("neco", "NECO SSCE", "National Examinations Council SSCE", 7, 9,
     ["English Language", "Mathematics", "Civic Education"], "#8B5CF6", 180,
     "English, Mathematics and Civic Education are compulsory."),
    ("gce", "GCE", "WAEC GCE (Private Candidates)", 7, 9, ["English Language", "Mathematics"], "#F59E0B", 180,
     "English and Mathematics are compulsory."),
    ("nabteb", "NABTEB", "National Business and Technical Examinations Board", 7, 9,
     ["English Language", "Mathematics"], "#EF4444", 180, "English and Mathematics are compulsory."),
    ("post-utme", "Post-UTME", "University Post-UTME Screening", 4, 4, ["English Language"], "#14532D", 60,
     "Matches your UTME subject combination. Format varies by institution."),
]

PACKAGES = [("Starter", 100, 1000, ""), ("Basic", 250, 2500, ""), ("Standard", 500, 5000, "Most popular"),
            ("Advanced", 1000, 10000, ""), ("Premium", 2500, 25000, "Best for full prep")]

BADGES = [
    ("first-steps", "First Steps", "Complete your first quiz.", "footprints", "bronze", {"type": "quizzes", "value": 1}, 20),
    ("lesson-learner", "Lesson Learner", "Complete 5 lessons.", "book-open-check", "bronze", {"type": "lessons", "value": 5}, 30),
    ("seven-day-streak", "Seven-Day Streak", "Learn 7 days in a row.", "flame", "silver", {"type": "streak", "value": 7}, 70),
    ("quiz-champion", "Quiz Champion", "Score 100% on 3 quizzes.", "trophy", "silver", {"type": "perfect_quizzes", "value": 3}, 80),
    ("mathematics-master", "Mathematics Master", "Master 5 topics.", "sigma", "gold", {"type": "mastered_topics", "value": 5}, 120),
    ("consistency-king", "Consistency King", "Learn 30 days in a row.", "crown", "gold", {"type": "streak", "value": 30}, 200),
    ("xp-1000", "Rising Star", "Earn 1,000 XP.", "star", "silver", {"type": "xp", "value": 1000}, 50),
    ("exam-ready", "Exam Ready", "Score 70%+ on a full mock exam.", "graduation-cap", "emerald", {"type": "mock_score", "value": 70}, 250),
]

MISSIONS = [
    ("daily-lesson", "Complete one lesson", "daily", "lessons_completed", 1, 15, "book-open"),
    ("daily-15-questions", "Answer 15 questions", "daily", "questions_answered", 15, 20, "list-checks"),
    ("daily-weak-topic", "Revise a weak topic", "daily", "weak_topic_practice", 1, 20, "target"),
    ("daily-tutor", "Ask the AI tutor one question", "daily", "tutor_questions", 1, 10, "sparkles"),
    ("weekly-quizzes", "Complete 10 quizzes", "weekly", "quizzes_completed", 10, 100, "trophy"),
    ("weekly-xp", "Earn 500 XP", "weekly", "xp_earned", 500, 80, "zap"),
]


def math_generators(topic_name):
    """Questions that are correct by construction (answers computed, not guessed)."""
    r = random.Random(sum(map(ord, topic_name)))
    out = []
    if topic_name == "Quadratic Equations":
        for _ in range(16):
            a, b = r.sample(range(-9, 10), 2)
            if 0 in (a, b):
                continue
            s, p = -(a + b), a * b
            def term(c, x):
                return "" if c == 0 else (f" + {c}{x}" if c > 0 else f" - {-c}{x}")
            eq = f"x^2{term(s, 'x')}{term(p, '')} = 0".replace(" 1x", " x")
            correct = f"$x = {min(a, b)}$ or $x = {max(a, b)}$"
            wrongs = {f"$x = {-max(a, b)}$ or $x = {-min(a, b)}$", f"$x = {min(a, b) - 1}$ or $x = {max(a, b) + 1}$",
                      f"$x = {a * 2}$ or $x = {b}$"} - {correct}
            out.append((f"Solve the equation ${eq}$.", correct, list(wrongs)[:3],
                        f"Factorise: $(x {'-' if a > 0 else '+'} {abs(a)})(x {'-' if b > 0 else '+'} {abs(b)}) = 0$, "
                        f"so $x = {a}$ or $x = {b}$.",
                        [f"Find two numbers that multiply to {p} and add to {s}: they are {-a} and {-b}.",
                         f"Write the factors $(x {'-' if a > 0 else '+'} {abs(a)})(x {'-' if b > 0 else '+'} {abs(b)})$.",
                         "Set each factor to zero and solve."]))
    elif topic_name == "Percentages and Ratios":
        for _ in range(14):
            price = r.choice([2000, 2500, 4000, 5000, 8000, 12000, 15000])
            pct = r.choice([5, 10, 12, 15, 20, 25, 30])
            ans = price * (100 - pct) // 100
            out.append((f"A bag costs ₦{price:,}. It is sold at a discount of {pct}%. What is the selling price?",
                        f"₦{ans:,}", [f"₦{price * pct // 100:,}", f"₦{price * (100 + pct) // 100:,}", f"₦{ans - 100:,}"],
                        f"Discount = {pct}% of ₦{price:,} = ₦{price * pct // 100:,}. Selling price = ₦{price:,} − ₦{price * pct // 100:,} = ₦{ans:,}.",
                        [f"Find {pct}% of {price}.", "Subtract the discount from the original price."]))
    elif topic_name == "Indices and Logarithms":
        for _ in range(14):
            base = r.choice([2, 3, 5])
            m, n = r.randint(2, 5), r.randint(1, 4)
            out.append((f"Simplify ${base}^{{{m}}} \\times {base}^{{{n}}} \\div {base}^{{{n}}}$.",
                        f"${base}^{{{m}}}$", [f"${base}^{{{m + n}}}$", f"${base}^{{{m * n}}}$", f"${base}^{{{m + 2 * n}}}$"],
                        f"Add indices when multiplying and subtract when dividing: ${m} + {n} - {n} = {m}$.",
                        ["$a^m \\times a^n = a^{m+n}$", "$a^m \\div a^n = a^{m-n}$"]))
    elif topic_name == "Simultaneous Equations":
        for _ in range(14):
            x, y = r.randint(-5, 8), r.randint(-5, 8)
            a1, b1, a2, b2 = r.randint(1, 4), r.randint(1, 4), r.randint(1, 4), -r.randint(1, 4)
            c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
            out.append((f"Solve: ${a1}x + {b1}y = {c1}$ and ${a2}x - {-b2}y = {c2}$.",
                        f"$x = {x}, y = {y}$", [f"$x = {y}, y = {x}$" if x != y else f"$x = {x + 1}, y = {y}$",
                                                f"$x = {x + 1}, y = {y - 1}$", f"$x = {-x}, y = {y}$" if x else f"$x = 2, y = {y + 2}$"],
                        f"Eliminating one variable gives $x = {x}$; substituting back gives $y = {y}$.",
                        ["Multiply the equations so one variable has equal coefficients.", "Add or subtract to eliminate it.",
                         "Substitute the value back into either equation."]))
    elif topic_name == "Number Bases":
        for _ in range(14):
            n = r.randint(9, 60)
            b = r.choice([2, 5, 8])
            digits, k = "", n
            while k:
                digits = str(k % b) + digits
                k //= b
            out.append((f"Convert ${n}_{{10}}$ to base {b}.", f"${digits}_{{{b}}}$",
                        [f"${digits[::-1]}_{{{b}}}$" if digits[::-1] != digits else f"${int(digits) + 1}_{{{b}}}$",
                         f"${int(digits) + 10}_{{{b}}}$", f"${n}_{{{b}}}$"],
                        f"Divide {n} repeatedly by {b} and read the remainders from the bottom up: ${digits}_{{{b}}}$.",
                        [f"Divide by {b} and record each remainder.", "Read remainders from last to first."]))
    elif topic_name == "Statistics":
        for _ in range(14):
            data = sorted(r.sample(range(2, 30), 5))
            mean = sum(data) / 5
            if mean != int(mean):
                data[-1] += 5 - (sum(data) % 5)
                mean = sum(data) / 5
            out.append((f"Find the mean of {', '.join(map(str, data))}.", f"{int(mean)}",
                        [str(data[2]) if data[2] != mean else str(int(mean) + 2), str(int(mean) + 1), str(sum(data))],
                        f"Mean = sum ÷ number of values = {sum(data)} ÷ 5 = {int(mean)}.",
                        ["Add all the values.", "Divide by how many values there are."]))
    return out


class Command(BaseCommand):
    help = "Seed reference data and sample content"

    def add_arguments(self, parser):
        parser.add_argument("--admin", help="Email to make an admin")
        parser.add_argument("--content-manager", help="Email to make a content manager")

    @transaction.atomic
    def handle(self, *args, **opts):
        reviewer, _ = User.objects.get_or_create(
            email="content-bot@kwado.ai",
            defaults={"role": "content_manager", "full_name": "Kwado Content Team", "canonical_email": "content-bot@kwado.ai"})
        subjects, topics = {}, {}
        for name, (icon, color, tnames) in SUBJECTS.items():
            s, _ = Subject.objects.update_or_create(slug=slugify(name), defaults={"name": name, "icon": icon, "color": color})
            subjects[name] = s
            for i, tn in enumerate(tnames):
                t, _ = Topic.objects.update_or_create(subject=s, slug=slugify(tn),
                                                      defaults={"name": tn, "order": i, "weight": 3 if i < 3 else 2})
                topics[(name, tn)] = t
        for order, (code, name, full, mn, mx, comp, color, mins, note) in enumerate(EXAMS):
            e, _ = Examination.objects.update_or_create(code=code, defaults={
                "name": name, "full_name": full, "min_subjects": mn, "max_subjects": mx, "color": color,
                "mock_duration_minutes": mins, "rules_note": note, "order": order,
                "description": full})
            offered = set(comp) | {"Mathematics"} | set(ALL_ELECTIVES)
            for sn in offered:
                ExamSubject.objects.update_or_create(examination=e, subject=subjects[sn],
                                                     defaults={"is_compulsory": sn in comp})

        for i, (n, c, price, label) in enumerate(PACKAGES):
            CreditPackage.objects.update_or_create(slug=slugify(n), defaults={
                "name": n, "credits": c, "price_kobo": price * 100, "bonus_label": label, "order": i,
                "is_featured": n == "Standard"})
        for key, (label, credits) in DEFAULT_PRICING.items():
            ActivityPricing.objects.get_or_create(key=key, defaults={"label": label, "credits": credits})
        for i, (slug, name, desc, icon, tier, crit, xp) in enumerate(BADGES):
            Badge.objects.update_or_create(slug=slug, defaults={"name": name, "description": desc, "icon": icon,
                                                                "tier": tier, "criteria": crit, "xp_reward": xp, "order": i})
        for slug, title, period, metric, target, xp, icon in MISSIONS:
            Mission.objects.update_or_create(slug=slug, defaults={"title": title, "period": period, "metric": metric,
                                                                  "target": target, "xp_reward": xp, "icon": icon})
        for purpose in ("tutor_chat", "topic_explanation", "practice_set", "document_analysis", "roadmap"):
            AIConfig.objects.get_or_create(purpose=purpose)

        created = 0
        jamb = Examination.objects.get(code="jamb")

        def add_q(subject, topic, text, correct, wrongs, explanation, steps=(), difficulty=2, passage=None):
            nonlocal created
            if Question.objects.filter(subject=subject, text=text).exists():
                return
            q = Question.objects.create(subject=subject, topic=topic, text=text, explanation=explanation,
                                        solution_steps=list(steps), difficulty=difficulty, source=SAMPLE_SOURCE,
                                        status="published", published_at=timezone.now(), created_by=reviewer,
                                        reviewed_by=reviewer, passage=passage)
            uniq = []
            for w in wrongs:
                if w != correct and w not in uniq:
                    uniq.append(w)
            if len(uniq) < 3:
                q.delete()
                return
            options = [correct] + uniq[:3]
            order = list(range(len(options)))
            random.Random(text).shuffle(order)
            correct_opt = None
            for pos, idx in enumerate(order):
                o = QuestionOption.objects.create(question=q, label="ABCD"[pos], text=options[idx], order=pos)
                if idx == 0:
                    correct_opt = o
            AnswerKey.objects.create(question=q, correct_option=correct_opt, verified_by=reviewer,
                                     verified_at=timezone.now(), verification_source="Computed / reviewed sample")
            created += 1

        for tn in SUBJECTS["Mathematics"][2]:
            for text, correct, wrongs, expl, steps in math_generators(tn):
                add_q(subjects["Mathematics"], topics[("Mathematics", tn)], text, correct, wrongs, expl, steps)
        for (sn, tn), items in HANDWRITTEN.items():
            for item in items:
                add_q(subjects[sn], topics[(sn, tn)], item[0], item[1], item[2], item[3],
                      item[4] if len(item) > 4 else ())

        for (sn, tn), lessons in LESSONS.items():
            for i, l in enumerate(lessons):
                Lesson.objects.update_or_create(topic=topics[(sn, tn)], slug=slugify(l["title"]), defaults={
                    "title": l["title"], "objective": l["objective"], "estimated_minutes": l.get("minutes", 8),
                    "content": l["content"], "order": i, "is_published": True, "xp_reward": 20})

        for sn, s in subjects.items():
            path, _ = LearningPath.objects.update_or_create(subject=s, examination=None,
                                                            defaults={"title": f"{sn} journey"})
            path.nodes.all().delete()
            order = 0
            for i, t in enumerate(Topic.objects.filter(subject=s, parent__isnull=True).order_by("order")):
                for l in t.lessons.filter(is_published=True).order_by("order"):
                    LearningPathNode.objects.create(path=path, order=order, kind="lesson", title=l.title, lesson=l, topic=t)
                    order += 1
                LearningPathNode.objects.create(path=path, order=order, kind="challenge", title=f"{t.name} challenge", topic=t)
                order += 1
                if (i + 1) % 3 == 0:
                    LearningPathNode.objects.create(path=path, order=order, kind="boss", title=f"Boss: {t.name}",
                                                    topic=t, pass_mark=80)
                    order += 1

        for email, role in ((opts.get("admin"), "admin"), (opts.get("content_manager"), "content_manager")):
            if email:
                u = User.objects.filter(email=email.lower()).first() or User.objects.create_user(email=email)
                u.role = role
                u.is_staff = role == "admin"
                u.save()
                StudentProfile.objects.get_or_create(user=u)
                Streak.objects.get_or_create(user=u)
                get_wallet(u)
        self.stdout.write(self.style.SUCCESS(f"Seed complete. {created} new sample questions."))
