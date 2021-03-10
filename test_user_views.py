"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase
from bs4 import BeautifulSoup
from models import db, connect_db, Message, User, Likes, Follows

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


class UserViewTestCase(TestCase):
    """ Test user views. """

    def setUp(self):
        """ Add sample data with test client. """

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="test",
                                    email="test@test.com",
                                    password="test",
                                    image_url=None)
        self.testuser.id = 123

        self.u1 = User.signup("user1", "user1@gmail.com", "password", None)
        self.u1.id = 456
        self.u2 = User.signup("user2", "user2@gmail.com", "password", None)
        self.u2.id = 789
        self.u3 = User.signup("user3", "user3@gmail.com", "password", None)
        self.u4 = User.signup("user4", "user4@gmail.com", "password", None)

        db.session.commit()

        
    def tearDown(self):
        """ Clear any foul transactions. """
        db.session.rollback()

    def test_users_index(self):
        """ Does our list of users show? """
        with self.client as c:
            resp = c.get("/users")

        self.assertIn("@test", str(resp.data))
        self.assertIn("@user1", str(resp.data))
        self.assertIn("@user2", str(resp.data))
        self.assertIn("@user3", str(resp.data))
        self.assertIn("@user4", str(resp.data))

    def test_users_search(self):
        """ Is the user searchable? """

        with self.client as c:
            resp = c.get('/users?q=user')

        self.assertIn("@user1", str(resp.data))
        self.assertIn("@user2", str(resp.data))
        self.assertIn("@user3", str(resp.data))
        self.assertIn("@user4", str(resp.data))

        self.assertNotIn('@test', str(resp.data))

    
    def test_user_show(self):
        """ Does the user show? """

        with self.client as c:
            resp = c.get(f'/users/{self.testuser.id}')

        self.assertEqual(resp.status_code, 200)
        self.assertIn('@test', str(resp.data))

    def setup_likes(self):
        m1 = Message(text="msg1", user_id=self.testuser.id)
        m2 = Message(text="msg2", user_id=self.testuser.id)
        m3 = Message(id=9876, text="msg3", user_id=self.u1.id)
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        test_like = Likes(user_id=self.testuser.id, message_id=9876)

        db.session.add(test_like)
        db.session.commit()

    def test_user_show_with_likes(self):
        self.setup_likes()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@test", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        m = Message(id=333, text="bla bla bla", user_id=self.u1.id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/users/add_like/333", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==333).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser.id)

    def test_remove_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text=="msg3").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser.id)

    
        l = Likes.query.filter(
            Likes.user_id==self.testuser.id and Likes.message_id==m.id
        ).one()

        # confirm that the testuser likes the message "msg3"
        self.assertIsNotNone(l)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/users/add_like/{m.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==m.id).all()
            # the like has been deleted
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text=="msg2").one()
        self.assertIsNotNone(m)

        like_count = Likes.query.count()

        with self.client as c:
            resp = c.post(f"/users/add_like/{m.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # After the request, the number of requests have not changed.
            self.assertEqual(like_count, Likes.query.count())

    def setup_followers(self):
        f1 = Follows(user_being_followed_id=self.u1.id, user_following_id=self.testuser.id)
        f2 = Follows(user_being_followed_id=self.u2.id, user_following_id=self.testuser.id)
        f3 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.u1.id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_user_show_with_follows(self):

        self.setup_followers()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("test", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 0 messages
            self.assertIn("0", found[0].text)

            # Test for a count of 2 following
            self.assertIn("2", found[1].text)

            # Test for a count of 1 follower
            self.assertIn("1", found[2].text)

            # Test for a count of 0 likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(f"/users/{self.testuser.id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@user1", str(resp.data))
            self.assertIn("@user2", str(resp.data))
            self.assertNotIn("@user3", str(resp.data))
            self.assertNotIn("@user4", str(resp.data))

    def test_show_followers(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(f"/users/{self.testuser.id}/followers")

            self.assertIn("@user1", str(resp.data))
            self.assertNotIn("@user2", str(resp.data))
            self.assertNotIn("@user3", str(resp.data))
            self.assertNotIn("@user4", str(resp.data))

    
    def test_unauthorized_following_page_access(self):
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser.id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@user4", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser.id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@user4", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))
