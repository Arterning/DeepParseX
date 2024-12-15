from flask import Flask, request, jsonify

app = Flask(__name__)


# @app.route('/')
# def hello_world():  # put application's code here
#     return 'Hello World!'


# 模拟用户数据库
database = {
    "teachers": [
        {"username": "123456", "password": "Teacher@123"},
        {"username": "123457", "password": "Teacher@456"}
    ],
    "students": [
        {"username": "123458", "password": "Student@123"},
        {"username": "123459", "password": "Student@456"}
    ]
}

# 注册路由
@app.route("/register", methods=["POST"])
def register():
    # 解析请求数据
    data = request.json

    # 1. 验证输入字段是否完整
    if not validate_input(data):
        return jsonify({"success": False, "message": "缺少必要的字段"}), 400

    username = data["username"]
    password = data["password"]
    confirm_password = data["confirm_password"]
    role = data["role"].lower()

    # 2. 验证用户名格式
    if not validate_username_format(username):
        return jsonify({"success": False, "message": "用户名必须为4-9个数字"}), 400

    # 3. 验证用户名是否已存在
    if username_exists(username, role):
        return jsonify({"success": False, "message": "用户名已存在"}), 409

    # 4. 验证密码是否匹配
    if password != confirm_password:
        return jsonify({"success": False, "message": "密码与确认密码不匹配"}), 400

    # 5. 验证密码复杂度
    if not validate_password_complexity(password):
        return jsonify({"success": False, "message": "密码不符合复杂性要求"}), 400

    # 6. 添加用户到数据库
    add_user_to_database(username, password, role)

    # 7. 注册成功
    return jsonify({"success": True, "message": "注册成功！"})

# 验证输入字段是否完整
def validate_input(data):
    return data and all(key in data for key in ("username", "password", "confirm_password", "role"))

# 验证用户名格式
def validate_username_format(username):
    return username.isdigit() and 4 <= len(username) <= 9

# 验证用户名是否已存在
def username_exists(username, role):
    user_list = database["teachers"] if role == "teacher" else database["students"]
    return username in [user["username"] for user in user_list]

# 验证密码复杂性
def validate_password_complexity(password):
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char in "@#$%^&+=" for char in password):
        return False
    return True

# 添加用户到数据库
def add_user_to_database(username, password, role):
    user_data = {"username": username, "password": password}
    if role == "teacher":
        database["teachers"].append(user_data)
    else:
        database["students"].append(user_data)

if __name__ == "__main__":
    app.run(debug=True)