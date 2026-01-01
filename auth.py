USERS = {
    "TSD": {
        "password": "TSD@123",
        "role": "TSD"
    },
    "HOD": {
        "password": "HOD@123",
        "role": "HOD"
    }
}

def authenticate(username, password):
    if username in USERS and USERS[username]["password"] == password:
        return True, USERS[username]["role"]
    return False, None
