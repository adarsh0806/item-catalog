apt-get -qqy update
apt-get -qqy install python-pip
apt-get -qqy install python-flask python-sqlalchemy
pip install oauth2client
pip install requests
pip install httplib2
pip install flask-seasurf
pip install passlib

vagrantTip="[35m[1mThe shared directory is located at /vagrant\nTo access your shared files: cd /vagrant(B[m"
echo -e $vagrantTip > /etc/motd

