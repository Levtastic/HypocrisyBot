CREATE TABLE
    user_guilds
(
    id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_did INTEGER NOT NULL,
    admin INTEGER NOT NULL,
    blacklisted INTEGER NOT NULL
);

CREATE INDEX
    user_guilds_user_id
ON
    user_guilds
    (
        user_id
    );
