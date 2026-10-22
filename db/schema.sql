-- Sistema de votaciones - esquema para PostgreSQL 16

-- ------------------------------------------------------------
-- persons: datos comunes de votantes y candidatos.
-- El UNIQUE sobre email garantiza que una misma persona no se
-- registre dos veces, ni siquiera con roles distintos.
-- ------------------------------------------------------------
CREATE TABLE persons (
    id     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name   VARCHAR(100) NOT NULL,
    email  VARCHAR(255) NOT NULL,
    role   VARCHAR(10)  NOT NULL,

    CONSTRAINT uq_persons_email UNIQUE (email),
    CONSTRAINT ck_persons_email_lowercase CHECK (email = lower(email)),
    CONSTRAINT ck_persons_role CHECK (role IN ('VOTER', 'CANDIDATE')),
    -- Redundante con la PK a propósito: crea el "destino" que
    -- necesitan las FK compuestas (id, role) de voters y candidates.
    CONSTRAINT uq_persons_id_role UNIQUE (id, role)
);

-- ------------------------------------------------------------
-- voters: solo puede apuntar a personas con role = 'VOTER'
-- ------------------------------------------------------------
CREATE TABLE voters (
    person_id  INT PRIMARY KEY,
    role       VARCHAR(10) NOT NULL DEFAULT 'VOTER',
    has_voted  BOOLEAN     NOT NULL DEFAULT FALSE,

    CONSTRAINT ck_voters_role CHECK (role = 'VOTER'),
    CONSTRAINT fk_voters_person
        FOREIGN KEY (person_id, role)
        REFERENCES persons (id, role)
        ON DELETE RESTRICT
);

-- ------------------------------------------------------------
-- candidates: solo puede apuntar a personas con role = 'CANDIDATE'
-- ------------------------------------------------------------
CREATE TABLE candidates (
    person_id  INT PRIMARY KEY,
    role       VARCHAR(10)  NOT NULL DEFAULT 'CANDIDATE',
    party      VARCHAR(100),
    votes      INT          NOT NULL DEFAULT 0,

    CONSTRAINT ck_candidates_role CHECK (role = 'CANDIDATE'),
    CONSTRAINT ck_candidates_votes CHECK (votes >= 0),
    CONSTRAINT fk_candidates_person
        FOREIGN KEY (person_id, role)
        REFERENCES persons (id, role)
        ON DELETE RESTRICT
);

-- ------------------------------------------------------------
-- votes: un voto por votante (UNIQUE) y borrado protegido (RESTRICT)
-- ------------------------------------------------------------
CREATE TABLE votes (
    id            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voter_id      INT         NOT NULL,
    candidate_id  INT         NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_votes_voter UNIQUE (voter_id),
    CONSTRAINT fk_votes_voter
        FOREIGN KEY (voter_id)
        REFERENCES voters (person_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_votes_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES candidates (person_id)
        ON DELETE RESTRICT
);

-- voter_id ya tiene índice por el UNIQUE; candidate_id no (las FK no lo crean solas)
CREATE INDEX ix_votes_candidate_id ON votes (candidate_id);