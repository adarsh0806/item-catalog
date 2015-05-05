# Used for lots of stuff.
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from datetime import datetime
from functools import wraps

# Used to create our XML feed.
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from flask import Response
from xml.dom import minidom

# Used to create our ATOM feed.
from urlparse import urljoin
from werkzeug.contrib.atom import AtomFeed

# Used for receiving image files.
import os
import os.path
import random
from werkzeug import secure_filename

# Libraries needed for OAuth authentication.
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from urllib import urlencode
import json
from flask import make_response
import requests
from base64 import b64encode

# Used to keep session information.
from flask import session as login_session

import random, string

# Used to prevent CSRF.
from flask.ext.seasurf import SeaSurf


app = Flask(__name__)
csrf = SeaSurf(app)


import dboperations as dbops


# Read Google client ID.
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Set GitHub variables used for OAuth authentication.
GH_CLIENT_ID = json.loads(open('gh_client_secrets.json', 'r').read())['web']['app_id']
GH_CLIENT_SECRET = json.loads(open('gh_client_secrets.json', 'r').read())['web']['app_secret']
GH_AUTHORIZATION_BASE_URL = 'https://github.com/login/oauth/authorize'
GH_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GH_USER_URL = 'https://api.github.com/user'
GH_SCOPE = 'user:email'


# Used to upload images.
UPLOAD_FOLDER = 'static/item_images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# For a given image file, return whether it's an allowed type or not.
def allowed_file(filename):
    """Checks if the filename extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# Decorator to check if the user is logged in.
def login_required(f):
    """Decorator that checks if a user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if login_session.get('username') is None:
            return redirect(url_for('show_login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if the user is an admin.
def admin_access_required(f):
    """Decorator that checks if the logged in user is an Admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if login_session.get('isadmin') is None or not login_session['isadmin']:
            return redirect(url_for('categories'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to verify the state.
def verify_state(f):
    """Decorator that verifies the session state.."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If our session state is not valid, abort.
        clientstate = request.args.get('state') or request.form.get('state')
        if clientstate != login_session['state']:
            response = make_response(json.dumps('Invalid state parameter.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        return f(*args, **kwargs)
    return decorated_function

# Function to return "Invalid category" message to user if an invalid ID was specified.
def invalid_category():
    """Function that returns an 'Invalid category' message if an invalid category ID was specified.."""
    response = make_response(json.dumps('Invalid category ID.'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response

# Function to return "Invalid item" message to user if an invalid ID was specified.
def invalid_item():
    """Function that returns an 'Invalid item' message if an invalid item ID was specified."""
    response = make_response(json.dumps('Invalid item ID.'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response

# Function to return "Invalid user" message to user if an invalid ID was specified.
def invalid_user():
    """Function that returns an 'Invalid user' message if an invalid user ID was specified."""
    response = make_response(json.dumps('Invalid user ID.'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response



# Route for login page.
@app.route('/login')
def show_login():
    """Route that shows the user login page and creates an anti-forgery session state and token."""
    # Check if the user is already logged in, and if they are, redirect to the home page.
    if 'username' in login_session:
        flash("You are already logged in. No need to log in again.")
        return redirect(url_for('categories'))

    # Create anti-forgery state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE = state, gh_auth_link=('%s?scope=%s&client_id=%s&state=%s' % (GH_AUTHORIZATION_BASE_URL, GH_SCOPE, GH_CLIENT_ID, state)))


# Route for admin login page.
@app.route('/admin')
def admin_login():
    """Route that shows the Admin login page and creates an anti-forgery session state and token."""
    # Check if admin is already logged in, and if they are, redirect to the home page.
    if 'username' in login_session and login_session['isadmin']:
        flash("You are already logged in. No need to log in again.")
        return redirect(url_for('categories'))

    # Create anti-forgery state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state

    return render_template('admin.html', STATE=state)


# Route to see user profile.
@app.route("/userprofile", methods = ['GET', 'POST'])
@login_required
def user_profile():
    """Route that shows the user profile page."""
    # Get the user info from the database
    user = dbops.get_user_info(login_session['user_id'])

    return render_template('userprofile.html', user=user)


# Route to see list of registered users (Admin access only).
@app.route("/users")
@admin_access_required
def users():
    """Route that shows a list of registered users (Admin access only)."""
    # Get a list of registered users from the database
    users = dbops.get_users()

    return render_template('users.html', users=users)


# Route to see items created by a given user (Admin access only).
@app.route("/useritems/<int:user_id>")
@admin_access_required
def user_items(user_id):
    """Route that shows the items created by a given user (Admin access only)."""
    # Get a list of registered users from the database
    user = dbops.get_user_info(user_id)
    if user is None:
        return invalid_user()
    useritems = dbops.get_user_items(user_id)

    return render_template('useritems.html', user=user, useritems=useritems)


# Route for local authentication.
@app.route('/lconnect', methods=['POST'])
@verify_state
def lconnect():
    """Route used to authenticate the Admin login."""
    # Gather our form values; remove leading and trailing whitespace.
    user = request.form['user'].strip()
    password = request.form['password'].strip()

    # If nothing was entered, redirect to login page with message.
    if user == '' or password == '':
        flash("Please enter a username and password.")
        return redirect(url_for('admin_login'))

    # Check if the user exists.
    user = dbops.does_user_exist(user, password)
    if not user:
        flash("Incorrect username and/or password.")
        return redirect(url_for('admin_login'))

    # Let's see if the user is an admin.
    if dbops.is_user_admin(user.id):
        login_session['isadmin'] = True
    else:
        login_session['isadmin'] = False

    # Set the rest of the session.
    login_session['provider'] = 'local'
    login_session['user_id'] = user.id
    login_session['username'] = user.name
    if login_session['username'] == '':
        login_session['username'] = 'Anonymous'
    login_session['email'] = user.email
    login_session['picture'] = user.picture

    flash("Welcome %s..." % user.name)

    return redirect(url_for('categories'))


# Route for Facebook authentication.
@csrf.exempt        # We won't worry about CSRF here.
@app.route('/fbconnect', methods=['POST'])
@verify_state
def fbconnect():
    """Route used for Facebook OAuth authentication.

    1. To set up a connection to Facebook, login at: https://developers.facebook.com
    2. Go to MyApps -> Add a New App and select **Website.**
    3. Enter a name for the app, for example Catalog App, and click **Create New Facebook App ID.**
    4. Choose a Category and click **Create App ID.**
    5. For the Site URL, enter http://localhost:8000 and click **Next.**
    6. Under **Next Steps,** click **Skip to Developer Dashboard** and note your app ID and app secret.
    7. The next step is to add your Facebook app ID and secret to the fb_client_secrets.json file that is located in the folder this application resides.
    8. Open fb_client_secrets.json in a text editor.
    9. Replace YOUR_FACEBOOK_APP_ID with your Facebook app ID and replace YOUR_FACEBOOK_APP_SECRET with your Facebook app secret and save the file.
    10. Open login.html located in the application/templates folder. Look for the following line:

    appId      : 'YOUR_FACEBOOK_APP_ID_GOES_HERE',

    11. Replace YOUR_FACEBOOK_APP_ID_GOES_HERE with your Facebook app ID and save the file.
    """
    access_token = request.data
    print "access token received %s" % access_token

    # Exchange client token for long-lived server-side token.
    # GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token} 
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id,app_secret,access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.2/me"

    # Strip expire tag from access token.
    token = result.split("&")[0]

    # Let's go grab the user data from Facebook.
    url = 'https://graph.facebook.com/v2.2/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    # Set the session info
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    if login_session['username'] == '':
        login_session['username'] = 'Anonymous'
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    login_session['isadmin'] = False

    # Get user picture
    url = 'https://graph.facebook.com/v2.2/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]
  
    # See if user exists in the database, and if not, create the user.
    user_id = dbops.get_user_id(login_session['email'])
    if user_id is None:
        user_id = dbops.create_user(login_session)
    login_session['user_id'] = user_id

    # Create HTML message to welcome the user.
    output = ''
    output +='<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    return output


# Route for Facebook logout.
@app.route('/fbdisconnect')
def fbdisconnect():
    """Route to disconnect the Facebook OAuth authentication."""
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1] 
    return


# Route for Google authentication.
@csrf.exempt        # We won't worry about CSRF here.
@app.route('/gconnect', methods=['POST'])
@verify_state
def gconnect():
    """Route used for Google OAuth authentication.

    1. To set up a connection with Google, login in at: https://console.developers.google.com
    2. Create a new project and give it a name such as Catalog app. Leave the Project ID as is.
    3. Once you've created the app, go to **APIs & auth -> Credentials** and click **Create new Client ID.**
    4. Select **Web application** for the Application type, then click **Configure consent screen.**
    5. Designate an email address, enter a Product name, and click **Save.**
    6. In the box that says **Authorized JavaScript origins,** add http://localhost:8000, then click **Create Client ID.**
    7. Click the **Download JSON** button and save the file to the same folder where this application resides.
    8. Rename the file to: client_secrets.json
    9. Open login.html located in the application/templates folder. Look for the following line:

    data-clientid="YOUR_GOOGLE_CLIENT_ID_GOES_HERE"

    10. Replace YOUR_GOOGLE_CLIENT_ID_GOES_HERE with your Google client ID and save the file.
    """
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object.
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check to see if user is already logged in.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps("Current user is already connected."), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url =  "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    #print(answer.text)

    # Set our session information
    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    if login_session['username'] == '':
        login_session['username'] = 'Anonymous'
    login_session['email'] = data['email'] # to get the email from google, make sure login page has data-scope="openid email"
    login_session['picture'] = data['picture']
    # see if the user exists in the database; if not create a new user
    user_id = dbops.get_user_id(login_session['email'])
    if user_id is None:
        user_id = dbops.create_user(login_session)
    login_session['user_id'] = user_id
    login_session['isadmin'] = False

    # Create HTML message to welcome the user.
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'

    return output


# Function to log out a Google user.
def gdisconnect():
    """Route to disconnect the Google OAuth authentication."""
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'),401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    # For whatever reason, the given token was invalid.
    if result['status'] != '200':
        response = make_response(
        json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response
    return


# Route for GitHub authentication.
@csrf.exempt        # We won't worry about CSRF here.
@app.route('/ghconnect', methods=['GET'])
@verify_state
def ghconnect():
    """Route used for GitHub OAuth authentication.

    1. To set up a connection with GitHub, go to: https://github.com/settings/applications
    2. Click on **Register new application.**
    3. For the **Application name** give it a name such as Catalog App.
    4. For the **Homepage URL** enter: http://localhost:8000
    5. For the **Authorization callback URL** enter: http://localhost:8000/ghconnect
    6. Click on **Register Application** then at the top right of the page, note your Client ID and Client Secret.
    7. The next step is to add your GitHub app ID and secret to the gh_client_secrets.json file that is located in the folder this application resides.
    8. Open gh_client_secrets.json in a text editor.
    9. Replace YOUR_GITHUB_APP_ID with your GitHub app ID and replace YOUR_GITHUB_APP_SECRET with your GitHub app secret and save the file.
    """
    # Let's take the code we received from GitHub and get an access token.
    code = request.args.get('code')
    h = httplib2.Http()
    postdata = dict(client_id=GH_CLIENT_ID, client_secret=GH_CLIENT_SECRET, code=code)
    response, content = h.request(GH_TOKEN_URL, "POST", urlencode(postdata), headers={'Accept':'application/json'} )
    data = json.loads(content)

    try:
        access_token = data['access_token']
    except KeyError:
        access_tokan = False

    # If we didn't get an access token, abort.
    if not access_token:
        response = make_response(json.dumps('Failed to obtain access token.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Let's take the access token and grab GitHub's profile on the user.
    url = GH_USER_URL
    headers = {'Authorization': 'token %s' % access_token}
    h = httplib2.Http()
    result = h.request(url, 'GET', headers=headers)[1]
    profile = json.loads(result)

    # We have the user data; let's set the session.
    login_session['provider'] = 'github'
    login_session['username'] = profile['name']
    if login_session['username'] == '':
        login_session['username'] = 'Anonymous'
    login_session['email'] = profile['email']
    login_session['picture'] = profile['avatar_url']
    login_session['github_id'] = profile['id']
    login_session['isadmin'] = False

    # See if the user exists in the database; if not create a new user.
    user_id = dbops.get_user_id(login_session['email'])
    if user_id is None:
        user_id = dbops.create_user(login_session)
    login_session['user_id'] = user_id

    flash("Welcome %s. You are logged in." % login_session['username'])

    return redirect(url_for('categories'))


# Route for GitHub logout.
@app.route('/ghdisconnect')
def ghdisconnect():
    """Route to disconnect GitHub OAuth authentication."""

    return

    # tried to use the code below to disconnect from GitHub, but it doesn't work
    # no matter what username/password is used, the response is "Bad credentials"
    # not sure what GitHub is looking for
    github_id = login_session['github_id']
    url = 'https://api.github.com/authorizations/:%s' % github_id
    h = httplib2.Http()
    # h.add_credentials(GH_CLIENT_ID, GH_CLIENT_SECRET)
    auth = b64encode('%s : %s' % (GH_CLIENT_ID, GH_CLIENT_SECRET))
    headers = { 'Authorization' : 'Basic %s' % auth }
    result = h.request(url, 'DELETE', headers=headers)[1]
    print result
    return


# LOGOUT - Revoke a current user's token and reset their login_session.
@app.route('/disconnect')
def disconnect():
    """Route used to logout a user by revoking the authentication token and resetting the login session."""
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            # Reset Google specific session vars
            del login_session['credentials']
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            # Reset Facebook specific session vars
            del login_session['facebook_id']
        if login_session['provider'] == 'github':
            ghdisconnect()
            # Reset GitHub specific session vars
            del login_session['github_id']
        # if login_session['provider'] == 'local':        There is nothing to do for the local provider other than what we do below.

        # Reset the user's session.
        del login_session['provider']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['isadmin']
        del login_session['user_id']

        # Redirect user to home page and give message they have been logged out.
        flash("You have been successfully logged out. Happy trails...")
        return redirect(url_for('categories'))
    else:
        return redirect(url_for('categories'))


# Route for the homepage which will show the list of categories and a list of the nine most recent items added.
@app.route("/")
def categories():
    """Route to display the homepage showing all the categories and the most recent items."""
    # Grab all the categories and 9 most recent items
    categories  = dbops.get_categories()
    recentItems = dbops.get_recent_items()

    return render_template('home.html', categories=categories, recentItems=recentItems)

# Route that will list the items in a single category.
@app.route('/category/<int:category_id>/')
def category_items(category_id):
    """Route to display the items for a given category."""
    # Grab all the categories, the current category, and the current category items and item count.
    categories = dbops.get_categories()
    category   = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    items      = dbops.get_category_items(category_id)
    count      = len(items)

    return render_template('categoryitems.html', categories=categories, category=category, items=items, count=count)

# Route to show the item information.
@app.route('/category/<int:category_id>/item/<int:item_id>/')
def item_info(category_id, item_id):
    """Route to display item information for a given item."""
    # Grab the current category and item info
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    item = dbops.get_item_info(item_id)
    if item is None:
        return invalid_item()

    # If the user is logged in, pass user id to page; otherwise, pass a bogus value for the user id.
    # This will let us determine whether to show the Edit/Delete links to the user.
    if 'username' in login_session:
        return render_template('iteminfo.html', category=category, item=item, user_id=login_session['user_id'], owner=item.user_id)
    else:
        return render_template('iteminfo.html', category=category, item=item, user_id='-------', owner=item.user_id)


# Route to add a category.
@app.route('/category/add/', methods = ['GET', 'POST'])
@admin_access_required
def new_category():
    """Route to create a new category."""
    print login_session.get('isadmin')

    if request.method == 'POST':
        newcategoryname = request.form['name'].strip()

        if newcategoryname == '':
            flash("Please enter a category name.")
            return render_template('addcategory.html')

        # Let's make sure the category does not already exist, and if it doesn't create the new one.
        categoryexists = dbops.does_category_exist(newcategoryname)

        if categoryexists:
            flash("Sorry, the '%s' category already exists." % categoryexists.name)
            return render_template('addcategory.html')

        dbops.create_new_category(newcategoryname)

        flash("The '%s' category has been created. Congratulations!" % newcategoryname)

        return redirect(url_for('categories'))
    else:
        return render_template('addcategory.html')


# Route to edit a category; this allows the category name to be changed.
@app.route('/category/<int:category_id>/edit/', methods = ['GET', 'POST'])
@admin_access_required
def edit_category(category_id):
    """Route to edit an existing category. This allows the category name to be changed."""
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()

    if request.method == 'POST':
        oldcategory = category.name
        newcategoryname = request.form['name'].strip()

        if newcategoryname == '':
            flash("Please enter a category name.")
            return render_template('editcategory.html', category=category)

        # Let's make sure the category does not already exist, and if it doesn't update the category.
        categoryexists = dbops.does_category_exist(newcategoryname)

        if categoryexists:
            flash("Sorry, you cannot change '%s' to '%s'. The '%s' category already exists." % (category.name, newcategoryname, categoryexists.name))
            return render_template('editcategory.html', category=category)

        dbops.update_category(category, newcategoryname)

        flash("'%s' has been updated to '%s'. That looks much better!" % (oldcategory, category.name))

        return redirect(url_for('categories'))
    else:
        return render_template('editcategory.html', category=category)


# Route to delete a category.
@app.route('/category/<int:category_id>/delete/', methods = ['GET', 'POST'])
@admin_access_required
def delete_category(category_id):
    """Route to delete a new category."""
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    items = dbops.get_category_items(category_id)

    if request.method == 'POST':

        # Remove any item image files that may exist.
        if items:
            for item in items:
                if item.image:
                    if os.path.isfile(UPLOAD_FOLDER + "/" + item.image):
                        os.remove(os.path.join(UPLOAD_FOLDER, item.image))

        dbops.delete_category_items(category_id)
        dbops.delete_category(category)

        flash("The '%s' category has been deleted, trashed, removed, outta here!" % category.name)

        return redirect(url_for('categories'))
    else:
        return render_template('deletecategory.html', category_id=category_id, category=category)


# Route to add an item to a category.
@app.route('/category/<int:category_id>/add/', methods = ['GET', 'POST'])
@login_required
def new_item(category_id):
    """Route to create a new item."""
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()

    if request.method == 'POST':

        # If the user did not supply all information, redirect back to page.
        if request.form['name'].strip() == '' or request.form['price'].strip() == '' or request.form['description'] == '':
            flash("You are missing the name, price, and/or description. Please try again!")
            return render_template('additem.html', category_id=category_id, category=category)

        # If an image file was uploaded, process it accordingly.
        if request.files['image']:
            file = request.files['image']

            # Check if the file is one of the allowed types/extensions.
            if file and allowed_file(file.filename):

                imagefile = secure_filename(file.filename)

                # Move the file form the temporal folder to the upload folder we setup.
                # First make sure a file with the same name does not already exist and if it does, change the name of the uploaded file.
                if os.path.isfile(UPLOAD_FOLDER + "/" + imagefile):
                    imagefile = "%s-%s%s" % (os.path.splitext(imagefile)[0], str(random.randrange(999)), os.path.splitext(imagefile)[1])

                file.save(os.path.join(UPLOAD_FOLDER, imagefile))

                # Set the parameters for our new item which will include the image file.
                dbops.create_new_item(request.form['name'], request.form['description'], request.form['price'], imagefile, category_id, login_session['user_id'])
            else:
                # Set the parameters for our new item which excludes the image file since it failed the allowed file test.
                imagefile = None
                dbops.create_new_item(request.form['name'], request.form['description'], request.form['price'], imagefile, category_id, login_session['user_id'])
        else:
            # Set the parameters for our new item which excludes an image file since one was not uploaded.
            imagefile = None
            dbops.create_new_item(request.form['name'], request.form['description'], request.form['price'], imagefile, category_id, login_session['user_id'])

        flash("'%s' has been created. Congratulations!" % request.form['name'])

        return redirect(url_for('category_items', category_id=category_id))
    else:
        return render_template('additem.html', category_id=category_id, category=category)


# Route to edit an item in a category; this allows the item name, description, and category to be changed.
@app.route('/category/<int:category_id>/item/<int:item_id>/edit/', methods = ['GET', 'POST'])
@login_required
def edit_item(category_id, item_id):
    """Route to edit an item in a category. This allows the item name, description, and category to be changed."""
    # Grab all the categories, the current category, and the current item
    categories = dbops.get_categories()
    category   = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    item       = dbops.get_item_info(item_id)
    if item is None:
        return invalid_item()

    # If the user is not the owner of the item and not an admin, disallow access.
    if login_session['user_id'] != item.user_id and not login_session['isadmin']:
        flash("What do you think you are trying to do!? You may only edit items you created. Bad dog!!")
        return redirect('/category/%s/item/%s/' % (item.category_id, item.id))

    if request.method == 'POST':

        # If the user did not supply all information, redirect back to page
        if request.form['name'].strip() == '' or request.form['price'].strip() == '' or request.form['description'] == '':
            flash("You missed something. You must include the name, a price, and a description.")
            return render_template('edititem.html', category_id=category_id, category=category, categories=categories, item_id=item_id, item=item)

        imagefile = item.image

        # If an image file was uploaded, process it accordingly.
        if request.files['image']:
            file = request.files['image']

            # Check if the file is one of the allowed types/extensions.
            if file and allowed_file(file.filename):

                # Before we save the new image, we need to delete the old file if there is one.
                if item.image:

                    if os.path.isfile(UPLOAD_FOLDER + "/" + item.image):
                        os.remove(os.path.join(UPLOAD_FOLDER, item.image))

                # Make the filename safe, remove unsupported chars.
                imagefile = secure_filename(file.filename)

                # Move the file form the temporal folder to the upload folder we setup.
                # First make sure a file with the same name does not already exist and if it does, change the name of the uploaded file.
                if os.path.isfile(UPLOAD_FOLDER + "/" + imagefile):

                    # Append a random number to the imagefile.
                    imagefile = "%s-%s%s" % (os.path.splitext(imagefile)[0], str(random.randrange(999)), os.path.splitext(imagefile)[1])

                file.save(os.path.join(UPLOAD_FOLDER, imagefile))

        # Remove the image if the user checked the remove image box.
        if request.form.get('deleteimage') == 'on':

            if item.image:

                if os.path.isfile(UPLOAD_FOLDER + "/" + item.image):
                    os.remove(os.path.join(UPLOAD_FOLDER, item.image))

            imagefile = None

        dbops.update_item(item, request.form['name'], request.form['description'], request.form['price'], imagefile, request.form['category'])

        flash("'%s' has been updated. That looks much better!" % item.name)

        return redirect(url_for('item_info', category_id=category_id, item_id=item.id))
    else:
        return render_template('edititem.html', category_id=category_id, category=category, categories=categories, item_id=item_id, item=item)


# Route to delete an item from a category.
@app.route('/category/<int:category_id>/item/<int:item_id>/delete/', methods = ['GET', 'POST'])
@login_required
def delete_item(category_id, item_id):
    """Route to delete an item from a category."""
    # Grab the current category and item
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    item = dbops.get_item_info(item_id)
    if item is None:
        return invalid_item()

    # If the user is not the owner of the item, disallow access.
    if login_session['user_id'] != item.user_id and not login_session['isadmin']:
        flash("What do you think you are trying to do!? You may only delete items you created. Bad dog!!")
        return redirect('/category/%s/item/%s/' % (item.category_id, item.id))

    if request.method == 'POST':

        # If the item has an image, we need to delete the file.
        if item.image:

            if os.path.isfile(UPLOAD_FOLDER + "/" + item.image):
                os.remove(os.path.join(UPLOAD_FOLDER, item.image))

        dbops.delete_item(item)

        flash("'%s' has been deleted, trashed, removed, outta here!" % item.name)

        return redirect(url_for('category_items', category_id=category_id))
    else:
        return render_template('deleteitem.html', category_id=category_id, category=category, item_id=item_id, item=item)

# Route to show the user what items they control.
@app.route("/myitems")
@login_required
def my_items():
    """Route that displays a list of items created by the logged in user."""
    # Grab all the categories and items that were created by the user.
    categories = dbops.get_categories()
    myItems = dbops.get_user_items(login_session['user_id'])

    return render_template('myitems.html', categories=categories, myItems=myItems)


# Route to return a JSON list of all categories and items.
@app.route('/categories/JSON')
def categories_json():
    """Route that returns a JSON list of all categories and items.
    The data is read into a nested dictionary which is then jasonified."""
    # We are going to read the database entries into a nested dictionary, then return a jasonified dictionary.

    cDict = { "Categories":[] }
    categories = dbops.get_categories()
    # Iterate through the categories; with each iteration, we place the category info in a dictionary, then append it to our cDict dictionary
    for c in categories:
        cdata = {}
        cdata["id"] = c.id
        cdata["name"] = c.name
        cDict["Categories"].append(cdata)

        # Create a dictionary object that will hold the items in a category.
        iDict = { "Categories":[] }
        items = dbops.get_category_items(c.id)
        # Iterate through the items; with each iteration, we place the item info in a dictionary, then append it to our iDict dictionary.
        for i in items:
            idata = {}
            idata["id"] = i.id
            idata["name"] = i.name
            idata["description"] = i.description
            idata["price"] = i.price
            idata["category_id"] = i.category_id
            if i.image:
                # Create a fully qualified URL for the item image.
                idata["picture"] = url_for('static', filename='item_images/' + i.image, _external=True)
            else:
                idata["picture"] = 'No image available.'
            iDict["Categories"].append(idata)

        cDict["Categories"].append(iDict["Categories"])

    return jsonify(cDict)


# Route to return a JSON list of all items in a given category.
@app.route('/category/<int:category_id>/JSON')
def category_items_json(category_id):
    """Route that returns a JSON list of all items in a given category."""
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    items = dbops.get_category_items(category_id)
    return jsonify(CategoryItems=[i.serialize for i in items])


# Route to return a JSON list for a single item.
@app.route('/category/<int:category_id>/item/<int:item_id>/JSON')
def item_json(category_id, item_id):
    """Route that returns a JSON list for a single item."""
    item = dbops.get_item_info(item_id)
    if item is None:
        return invalid_item()
    return jsonify(CategoryItem=[item.serialize])


# Route to return an XML feed listing all categories and items.
@app.route('/categories/XML')
def categories_xml_feed():
    """Route that returns an XML feed of all categories and items."""
    categories = dbops.get_categories()

    # Create our XML
    Categories = Element('Categories')
    comment = Comment('Sun Ra Sports')
    Categories.append(comment)

    # Let's iterate through the categories.
    for c in categories:

        category = SubElement(Categories, 'Category')

        # Designate the categories
        Name = SubElement(category, 'Name')
        ID   = SubElement(category, 'ID')

        Name.text        = c.name
        ID.text          = str(c.id)

        items = dbops.get_category_items(c.id)

        # Let's iterate through the items in the category.
        for i in items:

            item = SubElement(category, 'Item')

            Name         = SubElement(item, 'Name')
            ID           = SubElement(item, 'ID')
            Description  = SubElement(item, 'Description')
            Price        = SubElement(item, 'Price')
            Image        = SubElement(item, 'Image')

            Name.text        = i.name
            ID.text          = str(i.id)
            Description.text = i.description
            Price.text       = i.price
            if i.image:
                # create a fully qualified URL for the item image
                Image.text   = url_for('static', filename='item_images/' + i.image, _external=True)
            else:
                Image.text   = ''

    # Format the XML to look nice.
    rough_string = tostring(Categories)
    reparsed = minidom.parseString(rough_string)

    return Response(reparsed.toprettyxml(indent="  "), content_type='text/xml; charset=utf-8')


# Route to return an XML feed of items for a specific category.
@app.route('/category/<int:category_id>/XML')
def category_items_xml_feed(category_id):
    """Route that returns an XML feed of items for a given category."""
    category = dbops.get_category(category_id)
    if category is None:
        return invalid_category()
    items = dbops.get_category_items(category.id)

    # Create our XML
    Items = Element('Items')
    comment = Comment('Sun Ra Sports')
    Items.append(comment)

    # Designate the category the items belong to
    CategoryName = SubElement(Items, 'CategoryName')
    CategoryID   = SubElement(Items, 'CategoryID')

    CategoryName.text        = category.name
    CategoryID.text          = str(category.id)

    # Create the items group
    CategoryItems = SubElement(Items, 'CategoryItems')

    # Let's iterate through the items and XMLify them.
    for i in items:
        item = SubElement(CategoryItems, 'item')

        name        = SubElement(item, 'name')
        id          = SubElement(item, 'id')
        description = SubElement(item, 'description')
        price       = SubElement(item, 'price')
        image       = SubElement(item, 'image')

        name.text        = i.name
        id.text          = str(i.id)
        description.text = i.description
        price.text       = i.price
        if i.image:
            # Create a fully qualified URL for the item image.
            image.text   = url_for('static', filename='item_images/' + i.image, _external=True)
        else:
            image.text   = ''

    # Format the XML to look nice.
    rough_string = tostring(Items)
    reparsed = minidom.parseString(rough_string)

    return Response(reparsed.toprettyxml(indent="  "), content_type='text/xml; charset=utf-8')


# Route to return an ATOM feed of the ten most recently added items.
@app.route('/recentitems/ATOM')
def atom_feed():
    """Route that returns an ATOM feed of the ten most recently added items."""
    # Grab the 10 most recently updated items.
    recentItems = dbops.get_recent_items()
    feed = AtomFeed("Sun Ra Sporting Goods", feed_url=request.url,
                    url=request.host_url,
                    subtitle="Recent Item Listings")

    # Create a datetime object required by the feed
    cDate=datetime.today()

    # Add the items to the feed.
    for i in recentItems:
        feed.add(i.name, i.description, content_type='text', author="Sun Ra Sports", url="%scategory/%s/item/%s/" % (request.host_url, i.category_id, i.id), id=i.id, updated=i.last_updated, published=i.date_created)

    return feed.get_response()



if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
