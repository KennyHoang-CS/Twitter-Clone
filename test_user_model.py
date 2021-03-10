"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test user models."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        u1 = User.signup("test1", "email1@email.com", "password", None)
        uid1 = 1111
        u1.id = uid1

        u2 = User.signup("test2", "email2@email.com", "password", None)
        uid2 = 2222
        u2.id = uid2

        db.session.commit()

        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    def tearDown(self):
        """ Clear any foul transactions. """
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    # Users following / followed tests. 
    def test_users_follows(self):
        """ Does user following / followed work? """
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u2.followers), 1)
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u1.following), 1)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    # User class methods test. 
    def test_users_repr(self):
        """ Does the User __repr__ work? """
        self.assertEqual(User.__repr__(self.u1), f"<User #{self.u1.id}: {self.u1.username}, {self.u1.email}>")

    def test_user_create(self):
        """ Does User.create successfully create a new user given valid credentials? """

        self.assertIsInstance(User.signup('NewName', 'NewEmail', 'NewPassWord', None), User)
        self.assertIsNot(User.signup('', 'NewEmail', 'N', None), User)

    # User authenticate tests. 
    def test_user_authenticate(self):
        """ Does user authenticate work? """

        # Test valid username and valid password. 
        self.assertTrue(User.authenticate("test1", "password"))
        # Test valid username with bad password.
        self.assertFalse(User.authenticate('test1', 'badPassword'))
        # Test bad username with valid password. 
        self.assertFalse(User.authenticate('badUsername', 'password'))

    def test_user_invalid_email(self):
        """ Does it fail for an user's invalid email? """
        
        bad_user = User.signup('bad', None, 'password', None)
        bad_user.id = 123
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_user_invalid_username(self):
        """ Does it fail for an user's invalid username? """

        bad_user = User.signup(None, 'lol@gmail.com', 'password', None)
        bad_user.id = 123
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
    
    def test_user_invalid_password(self):
        """ Does it fail for an user's invalid password? """

        with self.assertRaises(ValueError):
            User.signup('bad', 'bad@gmail.com', "", None)
