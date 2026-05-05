import unittest

def validate_password(password):
    return len(password) >= 8 and any(char.isupper() for char in password)

def validate_friendship(user_id, friend_id):
    # nu poti sa te adaugi singur ca prieten
    return user_id != friend_id

class TestConnectify(unittest.TestCase):

    # UNIT TEST: PAROLE
    def test_password_rules(self):
        self.assertTrue(validate_password("ParolaMea2026")) 
        self.assertFalse(validate_password("scurta"))      
        self.assertFalse(validate_password("faramajuscula1")) 

    # UNIT TEST: PRIETENII
    def test_friendship_rules(self):
        user_id = 1
        friend_id = 2
        self.assertTrue(validate_friendship(user_id, friend_id)) 
        self.assertFalse(validate_friendship(user_id, user_id))  
        
        # UNIT TEST: SINGLETON
    def test_singleton_connection(self):
 
        from app import DatabaseSingleton
        
        db1 = DatabaseSingleton()
        db2 = DatabaseSingleton()
        
        self.assertIs(db1, db2, "Singleton nu funcționează: Instanțele sunt diferite!")

if __name__ == '__main__':
    unittest.main()