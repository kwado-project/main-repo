"""Past-question research pipeline: discovery, provenance, staging and verification.

Design rules
  * Everything here is a STAGING area. Nothing reaches the live student question
    bank (apps.questions) except through `promote.py`, which requires human
    verification AND cleared rights, and lands as a draft for answer verification.
  * Question text is only ever stored for sources whose permission status allows
    it (see Source.may_extract). Discovery stores metadata only.
  * Extracted text is never edited in place. Checks, AI reviews and human
    decisions are recorded as VerificationRecord rows.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ExaminationYear(TimeStampedModel):
    """A sitting of an examination (e.g. JAMB UTME 2014)."""

    examination = models.ForeignKey("examinations.Examination", on_delete=models.CASCADE, related_name="years")
    year = models.PositiveSmallIntegerField()
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("examination", "year")]
        ordering = ["examination", "year"]

    def __str__(self):
        return f"{self.examination.name} {self.year}"


class ResearchTarget(TimeStampedModel):
    """One cell of the research matrix: examination × subject × year."""

    class Status(models.TextChoices):
        MISSING = "missing", "No source found yet"
        SEARCHING = "searching", "Searching"
        SOURCES_FOUND = "sources_found", "Sources found, awaiting permission or extraction"
        EXTRACTED = "extracted", "Questions extracted"
        VERIFIED = "verified", "Has verified questions"
        UNAVAILABLE = "unavailable", "Searched exhaustively, nothing found"

    exam_year = models.ForeignKey(ExaminationYear, on_delete=models.CASCADE, related_name="targets")
    subject = models.ForeignKey("examinations.Subject", on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.MISSING, db_index=True)
    search_attempts = models.PositiveSmallIntegerField(default=0)
    last_searched_at = models.DateTimeField(null=True, blank=True)
    documents_found = models.PositiveIntegerField(default=0)
    questions_extracted = models.PositiveIntegerField(default=0)
    questions_verified = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("exam_year", "subject")]
        ordering = ["exam_year__year", "subject__name"]

    def __str__(self):
        return f"{self.exam_year} · {self.subject.name}"


class Source(TimeStampedModel):
    """A website (domain) that may hold past questions, with its compliance state."""

    class Permission(models.TextChoices):
        UNKNOWN = "unknown", "Not reviewed"
        NEEDS_REVIEW = "needs_review", "Terms need human review"
        TERMS_PROHIBIT = "terms_prohibit", "Terms appear to prohibit copying"
        ROBOTS_DISALLOW = "robots_disallow", "robots.txt disallows crawling"
        PERMITTED = "permitted", "Written permission recorded"
        OPEN_LICENSE = "open_license", "Openly licensed (licence recorded)"
        DENIED = "denied", "Permission refused"

    domain = models.CharField(max_length=253, unique=True)
    name = models.CharField(max_length=200, blank=True)
    homepage = models.URLField(max_length=500, blank=True)
    discovered_via = models.CharField(max_length=60, blank=True, help_text="seed, brave, google_cse, serpapi, firecrawl, crawl")
    permission_status = models.CharField(max_length=16, choices=Permission.choices, default=Permission.UNKNOWN, db_index=True)
    robots_checked_at = models.DateTimeField(null=True, blank=True)
    robots_txt = models.TextField(blank=True)
    crawl_delay_seconds = models.FloatField(default=5.0)
    terms_url = models.URLField(max_length=500, blank=True)
    terms_checked_at = models.DateTimeField(null=True, blank=True)
    terms_flags = models.JSONField(default=list, blank=True, help_text="Phrases found in the site's terms")
    license_name = models.CharField(max_length=120, blank=True)
    subjects_seen = models.JSONField(default=list, blank=True)
    years_seen = models.JSONField(default=list, blank=True)
    is_seed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self):
        return self.domain

    @property
    def may_extract(self) -> bool:
        """Question text may be stored only with recorded permission or an open licence."""
        return self.is_active and self.permission_status in (self.Permission.PERMITTED, self.Permission.OPEN_LICENSE)


class CopyrightPermission(TimeStampedModel):
    """Evidence for (or against) the right to store and use a source's questions."""

    class Status(models.TextChoices):
        REQUESTED = "requested"
        GRANTED = "granted"
        DENIED = "denied"
        EXPIRED = "expired"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="permissions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)
    basis = models.CharField(max_length=40, blank=True, help_text="written_permission, licence, public_domain, own_content")
    scope = models.CharField(max_length=255, blank=True, help_text="What is permitted, e.g. 'store and display 2000-2015 Mathematics'")
    evidence = models.TextField(blank=True, help_text="Licence text, email excerpt or link to the agreement")
    contact = models.CharField(max_length=200, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class SourceDocument(TimeStampedModel):
    """A single page or PDF found during discovery."""

    class Kind(models.TextChoices):
        HTML = "html"
        PDF = "pdf"
        UNKNOWN = "unknown"

    class Status(models.TextChoices):
        DISCOVERED = "discovered"
        BLOCKED = "blocked", "Blocked by robots.txt or rights"
        FETCHED = "fetched"
        EXTRACTED = "extracted"
        NO_QUESTIONS = "no_questions"
        FAILED = "failed"
        SKIPPED = "skipped"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="documents")
    url = models.URLField(max_length=1000, unique=True)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.UNKNOWN)
    title = models.CharField(max_length=500, blank=True)
    snippet = models.TextField(blank=True)
    examination_guess = models.CharField(max_length=20, blank=True)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    classification_confidence = models.FloatField(default=0)
    discovered_via = models.CharField(max_length=60, blank=True)
    discovery_query = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DISCOVERED, db_index=True)
    status_reason = models.CharField(max_length=255, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    storage_key = models.CharField(max_length=300, blank=True, help_text="Raw copy (permitted sources only)")
    fetched_at = models.DateTimeField(null=True, blank=True)
    fetch_backend = models.CharField(max_length=20, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    depth = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["source", "status"]), models.Index(fields=["subject", "year"])]

    def __str__(self):
        return self.url


class ExtractionJob(TimeStampedModel):
    """Durable record of every unit of pipeline work, for resume and de-duplication."""

    class Kind(models.TextChoices):
        DISCOVER = "discover"
        COMPLIANCE = "compliance"
        CRAWL = "crawl"
        EXTRACT = "extract"
        VERIFY = "verify"
        CYCLE = "cycle"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        SKIPPED = "skipped"

    kind = models.CharField(max_length=12, choices=Kind.choices, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    idempotency_key = models.CharField(max_length=200, unique=True)
    target = models.ForeignKey(ResearchTarget, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    document = models.ForeignKey(SourceDocument, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    attempts = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class PastQuestion(TimeStampedModel):
    """A question as extracted from one source document. Original text is immutable."""

    class Verification(models.TextChoices):
        UNVERIFIED = "unverified"
        AUTO_CHECKED = "auto_checked", "Passed automatic checks"
        NEEDS_REVIEW = "needs_review", "Needs human review"
        VERIFIED = "verified", "Verified by a person"
        REJECTED = "rejected"

    class Rights(models.TextChoices):
        PERMISSION_PENDING = "permission_pending"
        CLEARED = "cleared"
        DENIED = "denied"

    class Method(models.TextChoices):
        HTML = "html"
        PDF_TEXT = "pdf_text"
        OCR = "ocr"
        MANUAL = "manual"

    examination = models.ForeignKey("examinations.Examination", on_delete=models.PROTECT, related_name="+")
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    question_number = models.PositiveSmallIntegerField(null=True, blank=True)
    text = models.TextField(help_text="Exactly as extracted — never edited")
    passage = models.TextField(blank=True)
    normalized_hash = models.CharField(max_length=64, db_index=True)
    topic = models.ForeignKey("examinations.Topic", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    difficulty = models.PositiveSmallIntegerField(null=True, blank=True)
    has_math = models.BooleanField(default=False)
    has_diagram = models.BooleanField(default=False)
    image_refs = models.JSONField(default=list, blank=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="questions")
    document = models.ForeignKey(SourceDocument, on_delete=models.PROTECT, related_name="questions")
    source_url = models.URLField(max_length=1000)
    page_number = models.PositiveSmallIntegerField(null=True, blank=True)
    extraction_method = models.CharField(max_length=10, choices=Method.choices)
    extraction_confidence = models.FloatField(default=0)
    verification_status = models.CharField(max_length=14, choices=Verification.choices, default=Verification.UNVERIFIED, db_index=True)
    rights_status = models.CharField(max_length=20, choices=Rights.choices, default=Rights.PERMISSION_PENDING, db_index=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates")
    flags = models.JSONField(default=list, blank=True)
    promoted_question = models.ForeignKey("questions.Question", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["year", "subject", "question_number"]
        indexes = [models.Index(fields=["subject", "year"]), models.Index(fields=["verification_status", "rights_status"])]
        constraints = [models.UniqueConstraint(fields=["document", "question_number", "normalized_hash"], name="uniq_question_in_document")]

    def __str__(self):
        return f"{self.year} {self.subject} Q{self.question_number}"


class PastQuestionOption(models.Model):
    question = models.ForeignKey(PastQuestion, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=2)
    text = models.TextField()

    class Meta:
        ordering = ["label"]
        unique_together = [("question", "label")]


class PastAnswer(TimeStampedModel):
    """An answer claim. A source's key, a human decision, or an AI opinion — never merged."""

    class Origin(models.TextChoices):
        SOURCE = "source", "Answer key in the source"
        HUMAN = "human", "Human reviewer"
        AI = "ai", "AI review (advisory only)"

    question = models.ForeignKey(PastQuestion, on_delete=models.CASCADE, related_name="answers")
    label = models.CharField(max_length=2)
    origin = models.CharField(max_length=8, choices=Origin.choices)
    confidence = models.FloatField(default=1.0)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=255, blank=True)


class PastExplanation(TimeStampedModel):
    question = models.ForeignKey(PastQuestion, on_delete=models.CASCADE, related_name="explanations")
    text = models.TextField()
    origin = models.CharField(max_length=8, choices=PastAnswer.Origin.choices, default=PastAnswer.Origin.SOURCE)


class VerificationRecord(TimeStampedModel):
    """Append-only audit trail of every check and decision about a question."""

    class Result(models.TextChoices):
        PASS = "pass"
        WARN = "warn"
        FAIL = "fail"
        INFO = "info"

    class Actor(models.TextChoices):
        SYSTEM = "system"
        AI = "ai"
        HUMAN = "human"

    question = models.ForeignKey(PastQuestion, on_delete=models.CASCADE, related_name="verifications")
    check_name = models.CharField(max_length=40, db_index=True)
    result = models.CharField(max_length=4, choices=Result.choices)
    actor = models.CharField(max_length=6, choices=Actor.choices, default=Actor.SYSTEM)
    details = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
