USE acb;

-- Table with all the teams uniquely identified
CREATE TABLE team (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    team_acbid VARCHAR(3) UNIQUE NOT NULL,  -- Unique code from ACB.
    founded_year INTEGER DEFAULT null
);
CREATE INDEX team_acbid_idx ON team(team_acbid);

-- Table with the teams and associated names for each season
CREATE TABLE teamname (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    team_id INTEGER NOT NULL,  -- Reference to the team table autogenerated id
    name VARCHAR(255) NOT NULL,  -- Name taken for a single season (depends on the sponsors)
    season INTEGER NOT NULL,  -- Season year
    FOREIGN KEY (team_id) REFERENCES team(id)
);
CREATE INDEX teamName_team_id_idx ON teamname(team_id);

-- Table with all the games
CREATE TABLE game (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    game_acbid INTEGER UNIQUE NOT NULL,  -- ACB game ID.
    team_home_id INTEGER NOT NULL,  -- Reference to the home team id
    team_away_id INTEGER NOT NULL,  -- Reference to the away team id

    competition_phase VARCHAR(255) DEFAULT null,  -- Regular season or playoff
    round_phase VARCHAR(255) DEFAULT null,  -- If playoff, round of the game (quarter final, semifinal, final)
    journey INTEGER DEFAULT null,  -- Number of the journey. In regular season it is generally one journey per week. In playoff it is one journey per round match.
    venue VARCHAR(255) DEFAULT null,  -- Place of the game, stadium
    attendance INTEGER DEFAULT null,  -- Game attendance
    kickoff_time DATETIME DEFAULT null,  -- Kick-off time. In number of seconds since UNIX epoch, UTC timezone.

    -- Final score including extra time.
    score_home INTEGER,
    score_away INTEGER,
    -- Score in first quarter.
    score_home_first INTEGER,
    score_away_first INTEGER,
    -- Score in second quarter.
    score_home_second INTEGER,
    score_away_second INTEGER,
    -- Score in third quarter.
    score_home_third INTEGER,
    score_away_third INTEGER,
    -- Score in fourth quarter.
    score_home_fourth INTEGER,
    score_away_fourth INTEGER,
    -- Score in extra-time. Most likely NULL.
    score_home_extra INTEGER,
    score_away_extra INTEGER,

    FOREIGN KEY (team_home_id) REFERENCES team(id),
    FOREIGN KEY (team_away_id) REFERENCES team(id),

    -- True flag if all the information with respect to the game has been inserted correctly.
    db_flag BOOLEAN
);
CREATE INDEX game_game_id_idx ON game(game_acbid);
CREATE INDEX game_team_home_id_idx ON game(team_home_id);
CREATE INDEX game_team_away_id_idx ON game(team_away_id);

/* An actor is a player or a coach. In this table, many fields may be set to NULL. */
CREATE TABLE actor (
    id INTEGER  AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    actor_acbid VARCHAR(255) NOT NULL,  -- ACB player / coach ID.
    is_coach BOOLEAN DEFAULT null,
    display_name VARCHAR(255) DEFAULT null,
    full_name VARCHAR(255) DEFAULT null,
    nationality VARCHAR(255) DEFAULT null,
    birth_place VARCHAR(255) DEFAULT null,
    birth_date DATETIME DEFAULT null,  -- Date of birth. In number of seconds since UNIX epoch, UTC timezone.
    position VARCHAR(255) DEFAULT null,  -- simple string
    height REAL DEFAULT null,  -- In meters.
    weight REAL DEFAULT null,  -- In kilograms.
    license VARCHAR(255) DEFAULT null,
    debut_acb DATETIME DEFAULT null,
    twitter VARCHAR(255) DEFAULT null
);
CREATE INDEX actor_acbd_idx ON actor(actor_acbid);
CREATE INDEX actor_display_name_idx ON actor(display_name);


/* A participant is a player, a coach or a referee. In this table, many fields may be set to NULL. */
CREATE TABLE participant (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    game_id INTEGER NOT NULL,
    team_id INTEGER DEFAULT null,
    actor_id INTEGER DEFAULT null,

    display_name VARCHAR(255) DEFAULT null,  -- Display name of the actor
    first_name VARCHAR(255) DEFAULT null,  -- First name of the actor
    last_name VARCHAR(255) DEFAULT null,  -- Last name of the actor

    -- Squad number of the player
    number INTEGER DEFAULT null,
    -- True if the actor is the coach.
    is_coach BOOLEAN DEFAULT null,
    -- True if the actor is a referee.
    is_referee BOOLEAN DEFAULT null,
    -- True if the player starts the game.
    is_starter BOOLEAN DEFAULT null,

     -- Number of minutes played.
    minutes INTEGER DEFAULT null,
    point INTEGER DEFAULT null,

    -- Two points attempts and scored.
    t2_attempt INTEGER DEFAULT null,
    t2 INTEGER DEFAULT null,
    -- Three points attempts and scored.
    t3_attempt INTEGER DEFAULT null,
    t3 INTEGER DEFAULT null,
     -- Free shots attempts and scored.
    t1_attempt INTEGER DEFAULT null,
    t1 INTEGER DEFAULT null,

    -- Offensive and deffensive rebounds
    defensive_reb INTEGER DEFAULT null,
    offensive_reb INTEGER DEFAULT null,
    -- Assist
    assist INTEGER DEFAULT null,
    -- Steals and turnovers
    steal INTEGER DEFAULT null,
    turnover INTEGER DEFAULT null,
    -- Counterattacks
    counterattack INTEGER DEFAULT null,
    --  Blocks and received blocks
    block INTEGER DEFAULT null,
    received_block INTEGER DEFAULT null,
    -- Dunks
    dunk INTEGER DEFAULT null,
    -- Faults and received faults
    fault INTEGER DEFAULT null,
    received_fault INTEGER DEFAULT null,
    -- +/- ratio. NULL for old matches.
    plus_minus INTEGER DEFAULT null,
    -- Efficiency.
    efficiency INTEGER DEFAULT null,

    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (team_id) REFERENCES team(id),
    FOREIGN KEY (actor_id) REFERENCES actor(id)

);
CREATE INDEX participant_game_id_idx ON participant(game_id);
CREATE INDEX participant_team_id_idx ON participant(team_id);
CREATE INDEX participant_actor_id_idx ON participant(actor_id);

CREATE TABLE event (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,  -- Table autogenerated id
    event_acbid INTEGER NOT NULL,
    game_acbid INTEGER NOT NULL,
    team_acbid VARCHAR(255) DEFAULT null,
    legend VARCHAR(255) DEFAULT null,
    extra_info VARCHAR(255) DEFAULT null,
    elapsed_time INTEGER DEFAULT null,
    display_name VARCHAR(255) CHARACTER SET utf8mb4,
    jersey INTEGER DEFAULT null,
    home_score INTEGER DEFAULT null,
    away_score INTEGER DEFAULT null,
    FOREIGN KEY (game_acbid) REFERENCES game(game_acbid)
    );
CREATE INDEX event_game_id_idx ON event(game_acbid);
CREATE INDEX event_event_id_idx ON event(event_acbid);