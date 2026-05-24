from pymongo import MongoClient
import bcrypt

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["petmart"]   # change to your database name
users = db["users"]       # collection name

# Admin details
admin_email = "admin@gmail.com"
admin_password = "admin123"

# Check if admin exists
if users.find_one({"email": admin_email}):
    print("❌ Admin already exists")
else:
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())

    admin_user = {
        "name": "Admin",
        "email": admin_email,
        "password": hashed_password.decode('utf-8'),
        "role": "admin"
    }

    users.insert_one(admin_user)
    print("✅ Admin user created successfully")