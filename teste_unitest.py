import unittest

def validate_password(password):
    return len(password) >= 8 and any(char.isupper() for char in password)

def validate_friendship(user_id, friend_id):
    # nu poti sa te adaugi singur ca prieten
    return user_id != friend_id

def is_admin_email(email):
    
    return email == "sabinabrinzei277@gmail.com"

class TestConnectify(unittest.TestCase):

    # UNIT TEST: PAROLE
    def test_password_rules(self):
        self.assertTrue(validate_password("ParolaMea2026")) # Corect
        self.assertFalse(validate_password("scurta"))       # Prea scurtă
        self.assertFalse(validate_password("faramajuscula1")) # Nu are litere mari

    # UNIT TEST: PRIETENII
    def test_friendship_rules(self):
        user_id = 1
        friend_id = 2
        self.assertTrue(validate_friendship(user_id, friend_id)) # Prieteni diferiți
        self.assertFalse(validate_friendship(user_id, user_id))  # Același ID (Self-friend)

    # UNIT TEST: ADMIN
    def test_admin_assignment(self):
        self.assertTrue(is_admin_email("sabinabrinzei277@gmail.com"))
        self.assertFalse(is_admin_email("altcineva@gmail.com"))

if __name__ == '__main__':
    unittest.main()