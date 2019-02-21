CREATE TABLE
    vreddit_message
(
    id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    src_url TEXT NOT NULL,
    channel_did TEXT NOT NULL,
    src_message_did TEXT NOT NULL,
    dest_message_did TEXT NOT NULL
);

CREATE INDEX
    vreddit_message_src_message
ON
    vreddit_message
    (
        channel_did,
        src_message_did
    );

CREATE INDEX
    vreddit_message_dest_message
ON
    vreddit_message
    (
        channel_did,
        dest_message_did
    );
