"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

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

class MessageModelTestCase(TestCase):
    """ Test message models. """

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        self.uid = 94566
        u = User.signup("testing", "testing@test.com", "password", None)
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        """ Clear any foul transactions. """
        db.session.rollback()
        
    def test_message_model(self):
        """ Does basic message model work? """

        test_message = Message(text="my sample message", user_id=self.uid)
        db.session.add(test_message)
        db.session.commit()

        # User should only have one message. 
        self.assertEqual(len(self.u.messages), 1)   
        # In that one message, it should be "my sample message"
        self.assertEqual(self.u.messages[0].text, 'my sample message')

    def test_message_likes(self):
        """ Does liking another message work? """

        test_message = Message(text="my sample message", user_id=self.uid)
        self.u.likes.append(test_message)
        db.session.commit()

        myLikes = Likes.query.filter(Likes.user_id == self.u.id).all()
        
        self.assertEqual(len(myLikes), 1)
        self.assertEqual(myLikes[0].message_id, test_message.id)


    