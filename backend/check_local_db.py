import sqlite3

db = r"F:\muni48\backend\users.db"
con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
con.row_factory = sqlite3.Row

print("LOCAL NEWS PAYMENTS:")
for row in con.execute("""
    SELECT * FROM news_daily_payments
    ORDER BY id DESC
    LIMIT 20
"""):
    print(dict(row))

con.close()
