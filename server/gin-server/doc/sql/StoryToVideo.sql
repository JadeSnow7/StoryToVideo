-- 项目表
CREATE TABLE IF NOT EXISTS project (
    id           VARCHAR(64) PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    story_text   TEXT NOT NULL,
    style        VARCHAR(64) NOT NULL,
    status       VARCHAR(32) NOT NULL,
    cover_image  VARCHAR(512),
    duration     INT DEFAULT 0,
    video_url    VARCHAR(512),
    description  TEXT,
    shot_count   INT DEFAULT 0,
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL
);

-- 分镜表
CREATE TABLE IF NOT EXISTS shot (
    id           VARCHAR(64) PRIMARY KEY,
    project_id   VARCHAR(64) NOT NULL,
    `order`      INT NOT NULL,
    title        VARCHAR(255) NOT NULL,
    description  TEXT,
    prompt       TEXT,
    status       VARCHAR(32) NOT NULL,
    image_path   VARCHAR(512),
    audio_path   VARCHAR(512),
    transition   VARCHAR(64),
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

-- 任务表
CREATE TABLE IF NOT EXISTS task (
    id                VARCHAR(64) PRIMARY KEY,
    project_id        VARCHAR(64) NOT NULL,
    shot_id           VARCHAR(64),
    type              VARCHAR(32) NOT NULL,
    status            VARCHAR(32) NOT NULL,
    progress          INT DEFAULT 0,
    message           TEXT,
    parameters        JSON,
    result            JSON,
    error             TEXT,
    estimated_duration INT DEFAULT 0,
    started_at        DATETIME,
    finished_at       DATETIME,
    created_at        DATETIME NOT NULL,
    updated_at        DATETIME NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
    FOREIGN KEY (shot_id) REFERENCES shot(id) ON DELETE SET NULL
);