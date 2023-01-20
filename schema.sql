DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS surveys;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS answers;
DROP TABLE IF EXISTS choose_answers;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  firstname VARCHAR(32) NOT NULL,
  lastname VARCHAR(32) NOT NULL,
  username VARCHAR(32) NOT NULL UNIQUE,
  password VARCHAR(80) NOT NULaL
);

CREATE TABLE surveys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL UNIQUE,
  body TEXT NOT NULL,
  admin_id INTEGER NOT NULL,
  status BIT DEFAULT 0,
  start_time DATETIME,
  end_time DATETIME,
  FOREIGN KEY (admin_id) REFERENCES users(id)
);

CREATE TABLE questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  body TEXT NOT NULL,
  survey_id INTEGER NOT NULL,
  FOREIGN KEY (survey_id) REFERENCES surveys(id)
);

CREATE TABLE answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  body TEXT NOT NULL,
  question_id INTEGER NOT NULL,
  survey_id INTEGER NOT NULL,
  is_correct BIT DEFAULT 0,
  FOREIGN KEY (question_id) REFERENCES questions(id),
  FOREIGN KEY (survey_id) REFERENCES surveys(id)
);

CREATE TABLE user_answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  survey_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  answer_id INTEGER NOT NULL,
  is_correct BIT DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (survey_id) REFERENCES survey(id),
  FOREIGN KEY (question_id) REFERENCES questions(id),
  FOREIGN KEY (answer_id) REFERENCES answers(id)
);

CREATE TABLE invitations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INTEGER NOT NULL,
  admin_username VARCHAR(32) NOT NULL,
  participant_id INTEGER NOT NULL,
  survey_id INTEGER NOT NULL,
  FOREIGN KEY (admin_id) REFERENCES users(id),
  FOREIGN KEY (admin_username) REFERENCES users(username),
  FOREIGN KEY (participant_id) REFERENCES users(id),
  FOREIGN KEY (survey_id) REFERENCES surveys(id)
);

CREATE TABLE tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_key VARCHAR(80) NOT NULL,
  used INTEGER DEFAULT 0,
  available INTEGER DEFAULT 0,
  survey_id INTEGER NOT NULL,
  FOREIGN KEY (survey_id) REFERENCES surveys(id)
);