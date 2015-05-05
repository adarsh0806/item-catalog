# Item Catalog Application

**_Note: These instructions assume you have Git, VirtualBox, and Vagrant installed. If you do not have these three applications installed, you can download them from the following links:_**

**Git** - http://git-scm.com/downloads

**VirtualBox** - https://www.virtualbox.org/wiki/Downloads

**Vagrant** - https://www.vagrantup.com/downloads


## Instructions

Unzip the zip file and copy the itemcatalog folder to an appropriate location on your host machine.

Run Git (Git Bash on Windows; regular terminal program on Mac or Linux systems) and navigate to the catalog folder, then type **vagrant up** to launch your virtual machine. This will load all the libraries needed to run the Catalog application. For reference, these are the libraries that are loaded:
```
    flask
    sqlalchemy
    oauth2client
    requests
    httplib2
    flask-seasurf
    passlib
```
Now that you have Vagrant up and running, type **vagrant ssh** to log into your VM. Change to the /vagrant directory by typing **cd /vagrant**, then change to the application folder by typing **cd application**. This will take you to the folder where the application files reside.


### Database Setup

Set up the database by typing **python database_setup.py**. The setup will create four tables:
```
    category
    item
    user
    admin
```
Populate the database by typing **python addstuff.py**. This will add categories and items to the database along with setting up an admin user.

Launch the Catalog application by typing **python catalog.py**.

Now open up a browser and access the catalog website by browsing to:
```
    http://localhost:8000
```
On the home page is a list of categories and a list of the most recent items added to the database.

A user that is not logged in can browse the categories, see all the items in a category, and view descriptions of each item.

From any page, you can get back to the home page by clicking on the **Sun Ra Sports** logo.


### OAuth Setup

This application makes use of three OAuth providers: Google, Facebook, and GitHub. Before you can log in, you will need to set up a connection to each of these providers. You'll need to register an app with the respective developer sites and obtain a client/app ID and client/app secret.

**Google Setup:**

 1. Login in at: https://console.developers.google.com
 2. Create a new project and give it a name such as Catalog app. Leave the Project ID as is.
 3. Once you've created the app, go to **APIs & auth -> Credentials** and click **Create new Client ID.**
 4. Select **Web application** for the Application type, then click **Configure consent screen.**
 5. Designate an email address, enter a Product name, and click **Save.**
 6. In the box that says **Authorized JavaScript origins,** add http://localhost:8000, then click **Create Client ID.**
 7. Click the **Download JSON** button and save the file to the same folder where this application resides.
 8. Rename the file to: client_secrets.json
 9. Open login.html located in the application/templates folder. Look for the following line:
```
    data-clientid="YOUR_GOOGLE_CLIENT_ID_GOES_HERE"
```
10. Replace YOUR_GOOGLE_CLIENT_ID_GOES_HERE with your Google client ID and save the file.

This completes the Google OAuth setup.

**Facebook Setup:**

 1. Login at: https://developers.facebook.com
 2. Go to MyApps -> Add a New App and select **Website.**
 3. Enter a name for the app, for example Catalog App, and click **Create New Facebook App ID.**
 4. Choose a Category and click **Create App ID.**
 5. For the Site URL, enter http://localhost:8000 and click **Next.**
 6. Under **Next Steps,** click **Skip to Developer Dashboard** and note your app ID and app secret.
 7. The next step is to add your Facebook app ID and secret to the fb_client_secrets.json file that is located in the folder this application resides.
 8. Open fb_client_secrets.json in a text editor.
 9. Replace YOUR_FACEBOOK_APP_ID with your Facebook app ID and replace YOUR_FACEBOOK_APP_SECRET with your Facebook app secret and save the file.
10. Open login.html located in the application/templates folder. Look for the following line:
```
    appId      : 'YOUR_FACEBOOK_APP_ID_GOES_HERE',
```
11. Replace YOUR_FACEBOOK_APP_ID_GOES_HERE with your Facebook app ID and save the file.

This completes the Facebook OAuth setup.

**GitHub Setup:**

1. Go to: https://github.com/settings/applications
2. Click on **Register new application.**
3. For the **Application name** give it a name such as Catalog App.
4. For the **Homepage URL** enter: http://localhost:8000
5. For the **Authorization callback URL** enter: http://localhost:8000/ghconnect
6. Click on **Register Application** then at the top right of the page, note your Client ID and Client Secret.
7. The next step is to add your GitHub app ID and secret to the gh_client_secrets.json file that is located in the folder this application resides.
8. Open gh_client_secrets.json in a text editor.
9. Replace YOUR_GITHUB_APP_ID with your GitHub app ID and replace YOUR_GITHUB_APP_SECRET with your GitHub app secret and save the file.
 
This completes the GitHub OAuth setup.


### Logging In

A **Login** button appears at the top right of every page. You can log in using a Google Plus, Facebook, or GitHub account, or you can use a local account. The login page provides a link that takes you to a simple registration page where you can register a local account. The login page also provides a way to reset your local account password. For purposes of this project, I simply display the reset password on the login page.


### After Logging In

Once you log in, you have the ability to create an item. To create an item, browse to a category, then click on the **Add item** button. You have the ability to include an image with the item.

You have the ability to edit and delete the items you created. To edit or delete an item, go to the description of the item and click on the **Edit** or **Delete** link.

You cannot edit or delete items created by other users.

To see a list of the items you created, click on the **My items** button.

After you log in, your name will appear under the **Logout** button and it will be linked to a basic user profile. If you logged in under a local account, you have the ability to update the name and password on your profile.


### Administrator

The application allows for an administrator who has the ability to create, edit, and delete categories, and to edit and delete any item. To log in as the administrator, go to:
```
http://localhost:8000/admin
```
Enter the following credentials:
```
    User: admin
    Password: mycatalog
```
Once you log in as the admin, you'll be directed to the home page. From the home page is where you can add, edit, and delete categories. You also have the ability to see a list of users that have logged into the site by accessing the **Registered users** link at the bottom of the category list. On the registered users page, are individual user links that take you to a page listing the items created by each user.


### API Endpoints

At the bottom right of each page are links to three different feeds: JSON, XML, ATOM. A number of feeds are available.

**Available JSON feeds:**
```
    JSON feed listing all categories and items
      http://localhost:8000/categories/JSON

    JSON feed listing all items in a specified category
      http://localhost:8000/category/<int:category_id>/JSON

    JSON feed listing a single item
      http://localhost:8000/category/<int:category_id>/item/<int:item_id>/JSON
```
**Available XML feeds:**
```
    XML feed listing all categories and items
      http://localhost:8000/categories/XML

    XML feed of items for a specific category
      http://localhost:8000/category/<int:category_id>/XML
```
**Available ATOM feed:**
```
    ATOM feed of the ten most recently updated items
      http://localhost:8000/recentitems/ATOM
```
### Addendum

Sun Ra Sports and Sun Ra Enterprises are fictitious names.

The website template graphics were freely obtained from http://freewebsitetemplates.com. The clip art was obtained from a free clip art site.

The GitHub login code was developed from going over GitHub's documentation and reviewing examples found through Google searches.

The custom dialogue box that appears on web pages was obtained from https://jqueryui.com/dialog/.
