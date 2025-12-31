USERS = {
    "TSD": {"password": "1234", "role": "READ"},
    "HOD": {"password": "admin", "role": "ADMIN"}
}

def authenticate(username, password):
    if username in USERS and USERS[username]["password"] == password:
        return True, USERS[username]["role"]
    return False, None
