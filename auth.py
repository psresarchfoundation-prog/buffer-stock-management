# auth.py

USERS = {
    "TSD": {
        "password": "TSDwh@2026",
        "role": "TSD"
    },
    "HOD": {
        "password": "HODwh@2026",
        "role": "HOD"
    }
}

def authenticate(username, password):
    if username in USERS and USERS[username]["password"] == password:
        return True, USERS[username]["role"]
    return False, None
