from chimedb.core.mediawiki import MediaWikiUser

import os
import tornado


def get_user(request_handler):
    return request_handler.get_secure_cookie("user")


root_url = os.getenv("BONDIA_ROOT_URL", "")
next_url = os.getenv("BONDIA_NEXT_URL", "/")


# If this is done by defining login_url directly, tornado is inconsistent with the root url.
def get_login_url(request):
    return root_url + "/login"


class CustomLoginHandler(tornado.web.RequestHandler):
    def get(self):
        errormessage = self.get_argument("error", "")
        self.render(
            "login.html",
            root_url=os.getenv("BONDIA_ROOT_URL", "/"),
            errormessage=errormessage,
        )

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        if not username:
            error_msg = "?error=" + tornado.escape.url_escape("Invalid username.")
            self.redirect(os.getenv("BONDIA_ROOT_URL", "") + "/login" + error_msg)
            return

        try:
            MediaWikiUser.authenticate(username, password)
        except UserWarning as err:
            error_msg = "?error=" + tornado.escape.url_escape(str(err))
            self.redirect(os.getenv("BONDIA_ROOT_URL", "") + "/login" + error_msg)
        else:
            self.set_current_user(username)
            self.redirect(os.getenv("BONDIA_NEXT_URL", "/"))

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", user)
        else:
            self.clear_cookie("user")

    def get_user(self):
        user = self.get_secure_cookie("user")
        return user


def get_logout_url(request):
    return root_url + "/logout"


class CustomLogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(os.getenv("BONDIA_NEXT_URL", "/"))


def set_root_url(new_root_url: str):
    os.environ["BONDIA_ROOT_URL"] = new_root_url
    os.environ["BONDIA_LOGOUT_URL"] = new_root_url + "/logout"
    os.environ["BONDIA_NEXT_URL"] = new_root_url + "/"
