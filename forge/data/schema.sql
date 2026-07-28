-- FORGE component and material catalog.
--
-- Every row carries the evidence-register source key it came from and a
-- provenance class, so a downstream design decision can always be traced to
-- the document that justified it. Rows with provenance 'assumed' are project
-- decisions and must be visible as such in the report.

CREATE TABLE IF NOT EXISTS cores (
    part            TEXT PRIMARY KEY,
    family          TEXT NOT NULL,        -- ELP, ER, E/PLT
    manufacturer    TEXT NOT NULL,
    combination     TEXT NOT NULL,        -- E+E or E+I, as named by the vendor
    ae_mm2          REAL NOT NULL,        -- effective cross-section
    amin_mm2        REAL,                 -- minimum cross-section
    le_mm           REAL NOT NULL,        -- effective path length
    ve_mm3          REAL NOT NULL,        -- effective volume
    sigma_l_a_inv_mm REAL,                -- core factor
    height_mm       REAL NOT NULL,        -- assembled set height
    width_mm        REAL,
    length_mm       REAL,
    window_h_mm     REAL,                 -- winding window height per half
    window_w_mm     REAL,
    mass_g          REAL,
    source_key      TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS materials (
    name            TEXT PRIMARY KEY,
    manufacturer    TEXT NOT NULL,
    mu_i            REAL,
    b_sat_25c_mt    REAL,
    b_sat_100c_mt   REAL,
    curie_c         REAL,
    resistivity_ohm_m REAL,
    density_kg_m3   REAL,
    band_lo_hz      REAL,
    band_hi_hz      REAL,
    source_key      TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    status          TEXT NOT NULL,        -- characterised | unavailable
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS loss_points (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    material        TEXT NOT NULL,
    frequency_hz    REAL NOT NULL,
    b_peak_t        REAL NOT NULL,
    temperature_c   REAL NOT NULL,
    pv_w_m3         REAL NOT NULL,
    typical         INTEGER NOT NULL,     -- 1 typical, 0 guaranteed limit
    source_key      TEXT NOT NULL,
    locator         TEXT,
    FOREIGN KEY (material) REFERENCES materials(name)
);

CREATE TABLE IF NOT EXISTS loss_fits (
    material        TEXT NOT NULL,
    temperature_c   REAL NOT NULL,
    k               REAL NOT NULL,
    alpha           REAL NOT NULL,
    beta            REAL NOT NULL,
    f_lo_hz         REAL NOT NULL,
    f_hi_hz         REAL NOT NULL,
    b_lo_t          REAL NOT NULL,
    b_hi_t          REAL NOT NULL,
    n_points        INTEGER NOT NULL,
    max_residual    REAL NOT NULL,
    alpha_assumed   INTEGER NOT NULL,
    rel_uncertainty REAL NOT NULL,
    notes           TEXT,
    PRIMARY KEY (material, temperature_c)
);

CREATE TABLE IF NOT EXISTS devices (
    part            TEXT PRIMARY KEY,
    manufacturer    TEXT NOT NULL,
    role            TEXT NOT NULL,        -- primary_switch | synchronous_rectifier
    v_ds_max_v      REAL NOT NULL,
    r_ds_on_mohm    REAL NOT NULL,
    q_g_nc          REAL,
    q_oss_nc        REAL,
    q_oss_at_v      REAL,
    q_rr_nc         REAL,
    package         TEXT,
    source_key      TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS laminates (
    name            TEXT PRIMARY KEY,
    dk              REAL NOT NULL,        -- relative permittivity
    df              REAL NOT NULL,        -- loss tangent
    dk_freq_hz      REAL,
    tg_c            REAL,
    cti_group       TEXT,
    breakdown_kv_mm REAL,
    thermal_cond_w_mk REAL,
    source_key      TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS copper_weights (
    ounces          REAL PRIMARY KEY,
    thickness_um    REAL NOT NULL,
    provenance      TEXT NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS loss_points_by_material ON loss_points(material);
CREATE INDEX IF NOT EXISTS cores_by_family ON cores(family);
