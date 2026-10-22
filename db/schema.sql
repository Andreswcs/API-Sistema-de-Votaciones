-- ============================================================
-- Sistema de votaciones - esquema para PostgreSQL 16
-- Ejecutar como SCRIPT completo en DBeaver (Alt + X), no con Ctrl + Enter
-- ============================================================

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


-- ============================================================
-- PRUEBAS MANUALES
-- Ejecuta cada sentencia por separado (Ctrl + Enter) y compara
-- con el resultado esperado. Los comentarios con "DEBE FALLAR"
-- indican qué restricción debería saltar.
-- ============================================================

-- 1) Votante válido
-- INSERT INTO persons (name, email, role) VALUES ('Ana', 'ana@mail.com', 'VOTER');
-- INSERT INTO voters (person_id) SELECT id FROM persons WHERE email = 'ana@mail.com';

-- 2) La misma persona como candidata. DEBE FALLAR (FK compuesta)
-- INSERT INTO candidates (person_id) SELECT id FROM persons WHERE email = 'ana@mail.com';

-- 3) Email duplicado con otro rol. DEBE FALLAR (uq_persons_email)
-- INSERT INTO persons (name, email, role) VALUES ('Otra Ana', 'ana@mail.com', 'CANDIDATE');

-- 4) Email con mayúsculas. DEBE FALLAR (ck_persons_email_lowercase)
-- INSERT INTO persons (name, email, role) VALUES ('Beto', 'Beto@Mail.com', 'VOTER');

-- 5) Candidato válido
-- INSERT INTO persons (name, email, role) VALUES ('Luis', 'luis@mail.com', 'CANDIDATE');
-- INSERT INTO candidates (person_id, party) SELECT id, 'Partido Azul' FROM persons WHERE email = 'luis@mail.com';

-- 6) Un voto válido
-- INSERT INTO votes (voter_id, candidate_id)
-- SELECT v.person_id, c.person_id
-- FROM persons pv, persons pc, voters v, candidates c
-- WHERE pv.email = 'ana@mail.com'  AND v.person_id = pv.id
--   AND pc.email = 'luis@mail.com' AND c.person_id = pc.id;

-- 7) El mismo votante vota otra vez. DEBE FALLAR (uq_votes_voter)
--    (repite la sentencia del punto 6)

-- 8) Borrar un votante que ya votó. DEBE FALLAR (fk_votes_voter, RESTRICT)
-- DELETE FROM voters WHERE person_id = (SELECT id FROM persons WHERE email = 'ana@mail.com');

-- 9) Borrar un candidato con votos. DEBE FALLAR (fk_votes_candidate, RESTRICT)
-- DELETE FROM candidates WHERE person_id = (SELECT id FROM persons WHERE email = 'luis@mail.com');

-- 10) Votos negativos. DEBE FALLAR (ck_candidates_votes)
-- UPDATE candidates SET votes = -1;

-- Limpieza total para repetir las pruebas (el orden importa):
-- DROP TABLE votes, voters, candidates, persons;
