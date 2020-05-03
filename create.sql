  CREATE TABLE users (
      id SERIAL PRIMARY KEY,
      username  VARCHAR(15) NOT NULL UNIQUE,
      email VARCHAR(50) NOT NULL UNIQUE,
      password VARCHAR(80) NOT NULL
  );


    CREATE TABLE books (
      id SERIAL PRIMARY KEY,
      isbn VARCHAR NOT NULL,
      title VARCHAR NOT NULL,
      author VARCHAR NOT NULL,
      year VARCHAR NOT NULL
  );

  
    CREATE TABLE reviews (
      id SERIAL PRIMARY KEY,
      score INTEGER,
      opinion VARCHAR,
      user_id INTEGER REFERENCES users,
      book_id INTEGER REFERENCES books
    );