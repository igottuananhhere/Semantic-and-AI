import jwt

# Phải khớp đúng CUBEJS_API_SECRET trong docker-compose.yml
token = jwt.encode({}, "demo_secret_change_me", algorithm="HS256")
print(token)