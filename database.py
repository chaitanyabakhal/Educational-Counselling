import sqlite3

conn = sqlite3.connect('database.db')
print("Opened database successfully")

conn.execute('CREATE TABLE users (name TEXT, email TEXT, message TEXT)')
print("Table created successfully")

conn.close()