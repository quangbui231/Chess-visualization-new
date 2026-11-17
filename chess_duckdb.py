import duckdb

con = duckdb.connect("data/chess.duckdb", read_only=True)

# Xem cấu trúc bảng đã xử lý
print(con.sql("DESCRIBE staging.games").df())

# Xem 10 dòng dữ liệu đã xử lý
print(con.sql("SELECT * FROM staging.games LIMIT 10").df())

con.close()