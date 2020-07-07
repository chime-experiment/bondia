from chimedb.core import connect as connect_chimedb
from chimedb.core.mediawiki import MediaWikiUser

import panel as pn
import tornado


def get_user(request_handler):
    user = request_handler.get_secure_cookie("user")
    if user is not None and isinstance(user, (str, bytes, bytearray)):
        user = tornado.escape.json_decode(user)
    return user


next_url = "/"

login_url = "/login"


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        errormessage = self.get_argument("error", "")
        self.render("login.html", errormessage=errormessage)

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        if not username:
            error_msg = "?error=" + tornado.escape.url_escape("Invalid username.")
            self.redirect(login_url + error_msg)
            return

        connect_chimedb()
        try:
            MediaWikiUser.authenticate(username, password)
        except UserWarning as err:
            error_msg = "?error=" + tornado.escape.url_escape(str(err))
            self.redirect(login_url + error_msg)
        else:
            # make the username accessible to the panel application
            pn.state.cache["username"] = username
            self.set_current_user(username)
            self.redirect(next_url)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")

    def get_user(self):
        user = self.get_secure_cookie("user")
        if user is not None and isinstance(user, (str, bytes, bytearray)):
            user = tornado.escape.json_decode(user)
        return user


logout_url = "/logout"


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(next_url)
