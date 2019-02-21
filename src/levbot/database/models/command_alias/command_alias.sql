CREATE TABLE
    command_aliases
(
    id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    command TEXT NOT NULL,
    alias TEXT NOT NULL
);

CREATE INDEX
    command_aliases_alias
ON
    command_aliases
    (
        alias
    );
