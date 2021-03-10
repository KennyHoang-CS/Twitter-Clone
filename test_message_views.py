"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")


    def test_add_no_session(self):
        """ Should not allow users to send messages if not logged in. """
        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello World!"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_add_invalid_user(self):
        """ Invalid users should not be able to send messages. """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 999999999999 

            resp = c.post("/messages/new", data={"text": "Hello World!"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_message_show(self):

        # Create a message and add it to our test database. 
        m = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        
        db.session.add(m)
        db.session.commit()

        # Check if our message shows. 
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            m = Message.query.get(1234)

            resp = c.get(f'/messages/{m.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(m.text, str(resp.data))
    
    def test_invalid_message_show(self):
        """ Does our invalid message display an error if accessed? """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get('/messages/99999999')

            self.assertEqual(resp.status_code, 500)

    def test_message_delete(self):
        """  Are we able to delte a message? """
        
        # Create a message and add it to our test database. 
        m = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        db.session.add(m)
        db.session.commit()

        # Does our delete page respond with a status code 202?
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/1234/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            m = Message.query.get(1234)     # Our message should be deleted now. 
            self.assertIsNone(m)


    def test_message_delete_no_authentication(self):
        """ Message should not be deleted if user has no authentication. """
        
        # Create our sample message and add it to our test db. 
        m = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            resp = c.post("/messages/1234/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            m = Message.query.get(1234)
            self.assertIsNotNone(m)