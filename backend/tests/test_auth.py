from tests.helpers import auth_headers, login_user, register_user


def test_register_user(client, email_task_delay):
    response = client.post(
        "/auth/register",
        json={"username": "sam", "email": "sam@example.com", "password": "secret123"},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["username"] == "sam"
    assert data["email"] == "sam@example.com"
    assert "hashed_password" not in data
    email_task_delay.assert_called_once_with(
        "sam@example.com", "Welcome!", "welcome.html", {"username": "sam"}
    )


def test_login_user(client):
    register_user(client, username="sam", email="sam@example.com")

    response = client.post(
        "/auth/login", data={"username": "sam", "password": "secret123"}
    )

    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


def test_login_user_invalid_credentials(client):
    register_user(client, username="sam", email="sam@example.com")

    response = client.post(
        "/auth/login", data={"username": "jack", "password": "qwerty456"}
    )

    assert response.status_code == 401


def test_get_me_with_token(client):
    register_user(client, username="sam", email="sam@example.com")
    tokens = login_user(client, username="sam")

    response = client.get(
        "/auth/users/me", headers=auth_headers(tokens["access_token"])
    )

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "sam"
    assert "hashed_password" not in data


def test_get_me_without_token(client):
    response = client.get("/auth/users/me")

    assert response.status_code == 401


def test_refresh_rotates_refresh_token_and_revokes_old_one(client):
    register_user(client, username="sam", email="sam@example.com")
    tokens = login_user(client, username="sam")

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    old_refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["refresh_token"] != tokens["refresh_token"]
    assert old_refresh_response.status_code == 401


def test_logout_revokes_refresh_token(client):
    register_user(client, username="sam", email="sam@example.com")
    tokens = login_user(client, username="sam")

    logout_response = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out"}
    assert refresh_response.status_code == 401


def test_login_rate_limit_uses_test_redis_without_external_service(client):
    register_user(client, username="sam", email="sam@example.com")

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "sam", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        data={"username": "sam", "password": "wrong-password"},
    )

    assert response.status_code == 429
