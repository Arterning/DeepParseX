import pytest
from flask import Flask
from flask.testing import FlaskClient
from app import app, database

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.mark.parametrize("test_input, expected_status, expected_message", [
    # 测试用例序号 1-11 对应输入和期望的返回值
    ({"username": "12345", "password": "111",  "role": "Student"}, 400, "缺少必要的字段"),
    ({"username": "123", "password": "111", "confirm_password": "111", "role": "Student"}, 400, "用户名必须为4-9个数字"),
    ({"username": "123456", "password": "111", "confirm_password": "111", "role": "Teacher"}, 409, "用户名已存在"),
    ({"username": "12345", "password": "111", "confirm_password": "123", "role": "Student"}, 400, "密码与确认密码不匹配"),
    ({"username": "12345", "password": "111", "confirm_password": "111", "role": "Student"}, 400, "密码不符合复杂性要求"),
    ({"username": "12345", "password": "khyyyyyy", "confirm_password": "khyyyyyy", "role": "Student"}, 400, "密码不符合复杂性要求"),
    ({"username": "12345", "password": "khy12345", "confirm_password": "khy12345", "role": "Student"}, 400, "密码不符合复杂性要求"),
    ({"username": "12345", "password": "KHY12345", "confirm_password": "KHY12345", "role": "Student"}, 400, "密码不符合复杂性要求"),
    ({"username": "12345", "password": "Khy12345", "confirm_password": "Khy12345", "role": "Student"}, 400, "密码不符合复杂性要求"),
    ({"username": "12345", "password": "Khy12345@", "confirm_password": "Khy12345@", "role": "Student"}, 200, "注册成功！"),
    ({"username": "1234567", "password": "Khy12345@", "confirm_password": "Khy12345@", "role": "Teacher"}, 200, "注册成功！"),
])
def test_register(client: FlaskClient, test_input, expected_status, expected_message):
    response = client.post("/register", json=test_input)
    assert response.status_code == expected_status
    assert response.json["message"] == expected_message

