-- ============================================================================
-- ICAP Business Case Analysis and Decision Engine — database schema
-- SQLite + FTS5. Schema version 1.
-- Conventions: stdlib JSON only (no YAML); Decimal-safe app layer; seed data is
-- upserted with INSERT OR REPLACE and MUST never touch student tables
-- (StudentAttempts, MistakeLog).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- Papers ---
CREATE TABLE IF NOT EXISTS Papers (
    paper_id            TEXT PRIMARY KEY,
    code                TEXT,
    title               TEXT,
    scheme              TEXT,
    competency          TEXT,
    teaching_hours      TEXT,
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT,
    notes               TEXT
);

-- ------------------------------------------------------- SyllabusVersions ---
CREATE TABLE IF NOT EXISTS SyllabusVersions (
    version_id          TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES Papers(paper_id),
    scheme              TEXT,
    version_label       TEXT,
    effective_date      TEXT,
    source_url          TEXT,
    verification_status TEXT,
    notes               TEXT
);

-- ------------------------------------------------------ LearningOutcomes ---
CREATE TABLE IF NOT EXISTS LearningOutcomes (
    lo_id               TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES Papers(paper_id),
    syllabus_ref        TEXT,
    description         TEXT,
    proficiency_level   TEXT,
    testing_level       TEXT,
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT,
    review_status       TEXT
);

-- --------------------------------------------------------------- Topics ---
CREATE TABLE IF NOT EXISTS Topics (
    topic_id            TEXT PRIMARY KEY,
    paper_id            TEXT REFERENCES Papers(paper_id),
    syllabus_ref        TEXT,
    title               TEXT,
    weightage           TEXT,
    parent_topic_id     TEXT REFERENCES Topics(topic_id),
    verification_status TEXT,
    official_source     TEXT,
    effective_date      TEXT
);

-- -------------------------------------------------------------- Concepts ---
CREATE TABLE IF NOT EXISTS Concepts (
    concept_id          TEXT PRIMARY KEY,
    name                TEXT,
    definition          TEXT,
    paper_id            TEXT REFERENCES Papers(paper_id),
    topic_ref           TEXT,
    verification_status TEXT,
    source_ref          TEXT,
    review_status       TEXT
);

-- ------------------------------------------------------------ Frameworks ---
CREATE TABLE IF NOT EXISTS Frameworks (
    framework_id          TEXT PRIMARY KEY,
    name                  TEXT,
    definition            TEXT,
    purpose               TEXT,
    appropriate_situations TEXT,
    required_inputs       TEXT,
    limitations           TEXT,
    common_mistakes       TEXT,
    example               TEXT,
    related_topics        TEXT,
    verification_status   TEXT,
    source_ref            TEXT,
    review_status         TEXT
);

CREATE TABLE IF NOT EXISTS FrameworkSteps (
    step_id      TEXT PRIMARY KEY,
    framework_id TEXT REFERENCES Frameworks(framework_id),
    step_no      INTEGER,
    title        TEXT,
    description  TEXT,
    formula      TEXT
);

-- ---------------------------------------------------------- CasePatterns ---
CREATE TABLE IF NOT EXISTS CasePatterns (
    case_id            TEXT PRIMARY KEY,
    title              TEXT,
    paper_code         TEXT,
    topic_ref          TEXT,
    business_context   TEXT,
    industry           TEXT,
    company_size       TEXT,
    case_facts         TEXT,
    main_issue         TEXT,
    secondary_issues   TEXT,
    decision_to_make   TEXT,
    relevant_concepts  TEXT,
    possible_frameworks TEXT,
    quantitative_info  TEXT,
    qualitative_info   TEXT,
    missing_info       TEXT,
    constraints        TEXT,
    stakeholders       TEXT,
    alternatives       TEXT,
    evaluation_criteria TEXT,
    source_basis       TEXT,
    review_status      TEXT,
    verification_status TEXT
);

CREATE TABLE IF NOT EXISTS CaseFacts (
    fact_id           TEXT PRIMARY KEY,
    case_id           TEXT REFERENCES CasePatterns(case_id),
    wording           TEXT,
    normalised        TEXT,
    source_location   TEXT,
    classification    TEXT,
    related_issue     TEXT,
    related_framework TEXT,
    verified_or_assumed TEXT
);

-- ------------------------------------------------------- ProblemPatterns ---
CREATE TABLE IF NOT EXISTS ProblemPatterns (
    pattern_id  TEXT PRIMARY KEY,
    name        TEXT,
    description TEXT,
    indicators  TEXT
);

CREATE TABLE IF NOT EXISTS TriggerRules (
    rule_id                TEXT PRIMARY KEY,
    pattern_id             TEXT REFERENCES ProblemPatterns(pattern_id),
    title                  TEXT,
    triggers_json          TEXT,
    required_conditions    TEXT,
    interpretation         TEXT,
    alternative_explanations TEXT,
    info_needed            TEXT,
    relevant_concepts      TEXT,
    recommended_analysis   TEXT,
    rule_source            TEXT,
    review_status          TEXT
);

CREATE TABLE IF NOT EXISTS RuleFrameworkMappings (
    map_id       TEXT PRIMARY KEY,
    rule_id      TEXT REFERENCES TriggerRules(rule_id),
    framework_id TEXT REFERENCES Frameworks(framework_id),
    rationale    TEXT
);

-- --------------------------------------------------------------- Formulas ---
CREATE TABLE IF NOT EXISTS Formulas (
    formula_id          TEXT PRIMARY KEY,
    calc_id             TEXT,
    name                TEXT,
    formula_text        TEXT,
    inputs_json         TEXT,
    units_json          TEXT,
    assumptions         TEXT,
    limitations         TEXT,
    verification_status TEXT,
    validation_status   TEXT,
    review_status       TEXT
);

CREATE TABLE IF NOT EXISTS CalculationExamples (
    example_id   TEXT PRIMARY KEY,
    formula_id   TEXT REFERENCES Formulas(formula_id),
    inputs_json  TEXT,
    steps_json   TEXT,
    result_text  TEXT,
    interpretation TEXT
);

-- -------------------------------------------------------- DecisionOptions ---
CREATE TABLE IF NOT EXISTS DecisionOptions (
    option_id             TEXT PRIMARY KEY,
    case_id               TEXT REFERENCES CasePatterns(case_id),
    description           TEXT,
    financial_impact      TEXT,
    nonfinancial_benefits TEXT,
    costs                 TEXT,
    risks                 TEXT,
    time_requirements     TEXT,
    resource_requirements TEXT,
    stakeholder_effects   TEXT,
    strategic_alignment   TEXT,
    legal_constraints     TEXT,
    assumptions           TEXT,
    evidence              TEXT
);

CREATE TABLE IF NOT EXISTS EvaluationCriteria (
    criterion_id   TEXT PRIMARY KEY,
    case_id        TEXT REFERENCES CasePatterns(case_id),
    name           TEXT,
    description    TEXT,
    weight         REAL,
    criterion_type TEXT
);

-- ------------------------------------------------------ PracticeQuestions ---
CREATE TABLE IF NOT EXISTS PracticeQuestions (
    question_id            TEXT PRIMARY KEY,
    paper_code             TEXT,
    topic_ref              TEXT,
    syllabus_ref           TEXT,
    question_text          TEXT,
    difficulty             TEXT,
    marks                  INTEGER,
    suggested_minutes      INTEGER,
    required_skills        TEXT,
    expected_answer_elements TEXT,
    calculation_requirements TEXT,
    common_mistakes        TEXT,
    source_verified        INTEGER,
    source_note            TEXT,
    verification_status    TEXT
);

CREATE TABLE IF NOT EXISTS AnswerOutlines (
    outline_id   TEXT PRIMARY KEY,
    question_id  TEXT REFERENCES PracticeQuestions(question_id),
    outline_text TEXT,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS MarkingRubrics (
    rubric_id   TEXT PRIMARY KEY,
    question_id TEXT REFERENCES PracticeQuestions(question_id),
    rubric_json TEXT,
    note        TEXT
);

-- ---------------------------------------------------------------- Sources ---
CREATE TABLE IF NOT EXISTS Sources (
    source_id     TEXT PRIMARY KEY,
    citation      TEXT,
    url           TEXT,
    accessed_date TEXT,
    kind          TEXT
);

-- ---------------------------------------------------------- ReviewRecords ---
CREATE TABLE IF NOT EXISTS ReviewRecords (
    review_id   TEXT PRIMARY KEY,
    entity_type TEXT,
    entity_id   TEXT,
    reviewer    TEXT,
    review_date TEXT,
    status      TEXT,
    notes       TEXT
);

-- ============================================================ STUDENT TABLES
-- Seed code MUST NEVER insert into, update, or delete from these tables.
-- ============================================================
CREATE TABLE IF NOT EXISTS StudentAttempts (
    attempt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id    TEXT,
    attempted_at   TEXT,
    time_taken_min REAL,
    marks_self     REAL,
    checklist_json TEXT,
    answer_text    TEXT,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS MistakeLog (
    mistake_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER REFERENCES StudentAttempts(attempt_id),
    topic      TEXT,
    description TEXT,
    created_at TEXT,
    resolved   INTEGER DEFAULT 0
);

-- ---------------------------------------------------------- SchemaVersion ---
CREATE TABLE IF NOT EXISTS SchemaVersion (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT
);

-- ================================================================== INDEXES
CREATE INDEX IF NOT EXISTS idx_lo_paper      ON LearningOutcomes(paper_id);
CREATE INDEX IF NOT EXISTS idx_topics_paper  ON Topics(paper_id);
CREATE INDEX IF NOT EXISTS idx_concepts_paper ON Concepts(paper_id);
CREATE INDEX IF NOT EXISTS idx_steps_fw      ON FrameworkSteps(framework_id);
CREATE INDEX IF NOT EXISTS idx_facts_case     ON CaseFacts(case_id);
CREATE INDEX IF NOT EXISTS idx_rules_pattern  ON TriggerRules(pattern_id);
CREATE INDEX IF NOT EXISTS idx_map_rule       ON RuleFrameworkMappings(rule_id);
CREATE INDEX IF NOT EXISTS idx_map_fw         ON RuleFrameworkMappings(framework_id);
CREATE INDEX IF NOT EXISTS idx_examples_formula ON CalculationExamples(formula_id);
CREATE INDEX IF NOT EXISTS idx_options_case   ON DecisionOptions(case_id);
CREATE INDEX IF NOT EXISTS idx_criteria_case  ON EvaluationCriteria(case_id);
CREATE INDEX IF NOT EXISTS idx_q_paper        ON PracticeQuestions(paper_code);

-- ============================================================ FTS5 TABLES
-- Kept in sync by triggers below; seed.py also performs a full rebuild.
CREATE VIRTUAL TABLE IF NOT EXISTS case_fts USING fts5(
    case_id, title, business_context, industry, main_issue
);

CREATE VIRTUAL TABLE IF NOT EXISTS framework_fts USING fts5(
    framework_id, name, definition, purpose
);

CREATE VIRTUAL TABLE IF NOT EXISTS question_fts USING fts5(
    question_id, question_text, topic_ref
);

-- ------------------------------------------------- FTS sync triggers ---
CREATE TRIGGER IF NOT EXISTS case_fts_ai AFTER INSERT ON CasePatterns BEGIN
    INSERT INTO case_fts(case_id, title, business_context, industry, main_issue)
    VALUES (new.case_id, new.title, new.business_context, new.industry, new.main_issue);
END;

CREATE TRIGGER IF NOT EXISTS case_fts_ad AFTER DELETE ON CasePatterns BEGIN
    DELETE FROM case_fts WHERE case_id = old.case_id;
END;

CREATE TRIGGER IF NOT EXISTS case_fts_au AFTER UPDATE ON CasePatterns BEGIN
    DELETE FROM case_fts WHERE case_id = old.case_id;
    INSERT INTO case_fts(case_id, title, business_context, industry, main_issue)
    VALUES (new.case_id, new.title, new.business_context, new.industry, new.main_issue);
END;

CREATE TRIGGER IF NOT EXISTS framework_fts_ai AFTER INSERT ON Frameworks BEGIN
    INSERT INTO framework_fts(framework_id, name, definition, purpose)
    VALUES (new.framework_id, new.name, new.definition, new.purpose);
END;

CREATE TRIGGER IF NOT EXISTS framework_fts_ad AFTER DELETE ON Frameworks BEGIN
    DELETE FROM framework_fts WHERE framework_id = old.framework_id;
END;

CREATE TRIGGER IF NOT EXISTS framework_fts_au AFTER UPDATE ON Frameworks BEGIN
    DELETE FROM framework_fts WHERE framework_id = old.framework_id;
    INSERT INTO framework_fts(framework_id, name, definition, purpose)
    VALUES (new.framework_id, new.name, new.definition, new.purpose);
END;

CREATE TRIGGER IF NOT EXISTS question_fts_ai AFTER INSERT ON PracticeQuestions BEGIN
    INSERT INTO question_fts(question_id, question_text, topic_ref)
    VALUES (new.question_id, new.question_text, new.topic_ref);
END;

CREATE TRIGGER IF NOT EXISTS question_fts_ad AFTER DELETE ON PracticeQuestions BEGIN
    DELETE FROM question_fts WHERE question_id = old.question_id;
END;

CREATE TRIGGER IF NOT EXISTS question_fts_au AFTER UPDATE ON PracticeQuestions BEGIN
    DELETE FROM question_fts WHERE question_id = old.question_id;
    INSERT INTO question_fts(question_id, question_text, topic_ref)
    VALUES (new.question_id, new.question_text, new.topic_ref);
END;

-- ------------------------------------------------------------- Study aids --
-- Flashcards are generated deterministically from Frameworks, Formulas and
-- TriggerRules (tools/gen_study_aids.py); each card inherits its source
-- row's verification_status. FlashcardProgress is a STUDENT table: seed.py
-- and init_db() must never write to it.
CREATE TABLE IF NOT EXISTS Flashcards (
    card_id            TEXT PRIMARY KEY,
    deck               TEXT,
    front              TEXT NOT NULL,
    back               TEXT NOT NULL,
    framework_id       TEXT REFERENCES Frameworks(framework_id),
    formula_id         TEXT REFERENCES Formulas(formula_id),
    rule_id            TEXT REFERENCES TriggerRules(rule_id),
    topic              TEXT,
    paper_code         TEXT,
    card_type          TEXT,
    verification_status TEXT,
    official_source    TEXT
);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON Flashcards(deck);
CREATE INDEX IF NOT EXISTS idx_cards_fw   ON Flashcards(framework_id);

CREATE TABLE IF NOT EXISTS FlashcardProgress (
    card_id    TEXT PRIMARY KEY REFERENCES Flashcards(card_id),
    status     TEXT,   -- 'known' | 'unsure'
    reps       INTEGER NOT NULL DEFAULT 0,
    last_seen  TEXT
);

-- Mind-map catalogue: one row per map; leaf text is resolved from the
-- Frameworks/FrameworkSteps rows at render time (single source of truth).
CREATE TABLE IF NOT EXISTS MindMaps (
    map_id              TEXT PRIMARY KEY,
    framework_id        TEXT REFERENCES Frameworks(framework_id),
    title               TEXT,
    branch_order_json   TEXT,
    verification_status TEXT,
    source_ref          TEXT
);
