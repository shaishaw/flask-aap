import os
import re
import subprocess
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, flash, make_response

app = Flask(__name__)

appName = 'User Management App'


def login_required(f):
    '''
    Login required decorator.
    '''

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not 'username' in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Validate login credential and start the session.
    '''

    # The redirecting url for routes which requires login_required decorator
    next = request.args.get('next')

    # If request is POST than validate the form inputs
    if request.method == 'POST':
        next = request.form['next']
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['username'] = request.form['username']
            if not next:
                next = url_for('index')
            flash('Log in successful...', 'success')
            return redirect(next)
        else:
            flash('Invalid username or password...', 'error')

    # Redirect to index if session is already started and user hit the login url
    if 'username' in session:
        return redirect(url_for('index'))

    data = {
        'appName': appName,
        'pageTitle': 'Login',
        'next': next,
    }
    return render_template('login.html', data = data)

@app.route('/logout')
def logout():
    '''
    Logout the user and destroy the session.
    '''

    data = {
        'appName': appName,
        'pageTitle': 'Logout',
    }
    session.clear()
    flash('Log out successful...', 'success')
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    '''
    Display the user list if user is logged in.
    '''
    data={
        'appName': appName,
        'pageTitle': 'Index Page',
        'users': getUsers(),
    }
    return render_template('index.html', data = data)

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    '''
    Add a new user.
    '''

    data = {
        'appName': appName,
        'pageTitle': 'Add User',
    }

    # If request is POST than validate and form inputs and add the user
    if request.method == 'POST':
        data['username'] = request.form['username'].strip()
        data['shellpath'] = request.form['shellpath'].strip()
        data['homedir'] = request.form['homedir'].strip()
        data['password'] = request.form['password'].strip()
        data['password1'] = request.form['password1'].strip()
        data['sudo'] = 'sudo' in request.form

        # Validate form inputs
        valid = True
        if not data['username'] or not data['shellpath'] or not data['homedir'] or not data['password'] or not data['password1']:
            flash('Required fields are not entered...', 'error')
            valid = False
        else:
            if not re.match('^[a-zA-Z_][a-zA-Z0-9._]{1,31}$', data['username']):
                valid = False
                flash('Invalid username...', 'error')
            if data['username'] in getUsers():
                valid = False
                flash('Duplicate user, the username exists...', 'error')
            if data['shellpath'].startswith('/'):
                if not os.path.isfile(data['shellpath']):
                    valid = False
                    flash('Shell path doesnot exist...', 'error')
            else:
                valid = False
                flash('Shell path must be an absolute path...', 'error')
            if not data['homedir'].startswith('/'):
                valid = False
                flash('Home directory must be an absolute path...', 'error')
            if data['password'] != data['password1']:
                valid = False
                flash('Passwords didnot match...', 'error')

        # Run system commands if inputs are valid
        if valid:
            # Add user: run useradd command
            exitcode = subprocess.call(['sudo', 'useradd', '--create-home', '--home-dir=' + data['homedir'], '--shell=' + data['shellpath'], data['username']])
            if exitcode == 0:
                # Set password: run passwd command
                p = subprocess.Popen(['sudo', 'passwd', '--stdin', data['username']], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
                p.communicate(data['password'])
                exitcode = p.returncode
                waitcounter = 0
                while exitcode == None:
                    waitcounter += 1
                    # Give some timeout before marking it failed
                    if waitcounter > 10:
                        break
                    sleep(0.05)
                    exitcode = p.returncode
                if exitcode == 0:
                    if data['sudo']:
                        # Add user to sudoer
                        exitcode = subprocess.call(['sudo', 'grep', '-q', '^' + data['username'] + '\s', '/etc/sudoers'])
                        if exitcode == 0:
                            # User exist is sudoers, edit it
                            exitcode = subprocess.call(['sudo', 'sed', '-i', '/^' + data['username'] + '\s/c' + data['username'] + '\tALL=(ALL)\tNOPASSWD: ALL', '/etc/sudoers'])
                        else:
                            # User doesnot exist is sudoers, add it
                            exitcode = subprocess.call(['sudo', 'sed', '-i', '$a' + data['username'] + '\tALL=(ALL)\tNOPASSWD: ALL', '/etc/sudoers'])
                        if exitcode != 0:
                            flash('Failed to add user to sudoers...', 'error')
                    flash('User added successfully...', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Failed to set user password...', 'error')
            else:
                flash('Error adding user, useradd command returned non zero exit code...', 'error')

    return render_template('new.html', data = data)

@app.route('/edit/<username>', methods=['GET', 'POST'])
def edit(username):
    '''
    Edit existing user.
    '''

    data = {
        'appName': appName,
        'pageTitle': 'Edit User (%s)' % username,
        'user': username,
    }

    # If request is POST than validate and form inputs and add the user
    if request.method == 'POST':
        data['username'] = request.form['username'].strip()
        data['shell'] = request.form['shell'].strip()
        data['homedir'] = request.form['homedir'].strip()
        data['password'] = request.form['password'].strip()
        data['password1'] = request.form['password1'].strip()
        data['sudo'] = 'sudo' in request.form

        # Validate form inputs
        valid = True
        if not data['username'] or not data['shell'] or not data['homedir']:
            flash('Required fields are not entered...', 'error')
            valid = False
        else:
            if not re.match('^[a-zA-Z_][a-zA-Z0-9._]{1,31}$', data['username']):
                valid = False
                flash('Invalid username...', 'error')
            if data['username'] != username and data['username'] in getUsers():
                valid = False
                flash('Duplicate user, the username exists...', 'error')
            if data['shell'].startswith('/'):
                if not os.path.isfile(data['shell']):
                    valid = False
                    flash('Shell path doesnot exist...', 'error')
            else:
                valid = False
                flash('Shell path must be an absolute path...', 'error')
            if not data['homedir'].startswith('/'):
                valid = False
                flash('Home directory must be an absolute path...', 'error')

        # Run system commands if inputs are valid
        if valid:
            # Modify user: run usermod command
            exitcode = subprocess.call(['sudo', 'usermod', '--login', data['username'],'--move-home', '--home=' + data['homedir'], '--shell=' + data['shell'], username])
            if exitcode == 0:
                # Set password: run passwd command
                if data['password'] !="":
                    p = subprocess.Popen(['sudo', 'passwd', '--stdin', data['username']], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
                    p.communicate(data['password'])
                    exitcode = p.returncode
                    waitcounter = 0
                    while exitcode == None:
                        waitcounter += 1
                        # Give some timeout before marking it failed
                        if waitcounter > 10:
                            break
                        sleep(0.05)
                        exitcode = p.returncode
                if exitcode == 0:
                    if data['sudo']:
                        # Add user to sudoer
                        exitcode = subprocess.call(['sudo', 'grep', '-q', '^' + data['username'] + '\s', '/etc/sudoers'])
                        if exitcode == 0:
                            # User exist is sudoers, edit it
                            exitcode = subprocess.call(['sudo', 'sed', '-i', '/^' + data['username'] + '\s/c' + data['username'] + '\tALL=(ALL)\tNOPASSWD: ALL', '/etc/sudoers'])
                        else:
                            # User doesnot exist is sudoers, add it
                            exitcode = subprocess.call(['sudo', 'sed', '-i', '$a' + data['username'] + '\tALL=(ALL)\tNOPASSWD: ALL', '/etc/sudoers'])
                            if exitcode != 0:
                                flash('Failed to add user to sudoers...', 'error')
                            else:
                                flash('Sudoers file has been updated for user...', 'success')
                    else:
                        exitcode = subprocess.call(['sudo', 'sed', '-i', '/^' + username + '\s/d', '/etc/sudoers'])
                        if exitcode != 0:
                            flash('Failed to add user to sudoers...', 'error')
                        else:
                            flash('Sudoers file has been updated for user...', 'success')
                        
                    flash('User paramaters updated successfully...', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Failed to set user password...', 'error')
            else:
                flash('Error updating user, usermod command returned non zero exit code...', 'error')
    userslist = getUsers()
    if username in userslist:
            data['username']  = userslist[username]['username']
            data['shell']     = userslist[username]['shell']
            data['homedir']   = userslist[username]['homedir']  
            exitcode = subprocess.call(['sudo', 'grep', '-q', '^' + username + '\s', '/etc/sudoers'])
            if exitcode == 0:
                data['sudo'] = 1                
            else:
                data['sudo'] = 0
            
    return render_template('update.html', data = data)

@app.route('/remove/<username>', methods=['POST'])
def remove(username):
    '''
    Delete user.
    '''

    exitcode = subprocess.call(['sudo', 'grep', '-q', '^' + username + '\s', '/etc/sudoers'])
    if exitcode == 0:
        # User exist in sudoer, delete it
        exitcode = subprocess.call(['sudo', 'sed', '-i', '/^' + username + '\s/d', '/etc/sudoers'])
        if exitcode == 0:
            flash('Successfully deleted user from sudoers...', 'success')
        else:
            flash('Failed to delete user from sudoers...', 'error')

    # Delete user
    exitcode = subprocess.call(['sudo', 'userdel', username])
    if exitcode == 0:
        flash('User deleted successfully...', 'success')
    else:
        flash('Failed to delete user, userdel returned non zero exit code...', 'error')

    return redirect(url_for('index'))

def getUsers():
    '''
    Read uses from /etc/passwd and return the list of non system users.
    '''

    users = {}

    # Default UID_MIN and UID_MAX
    uid_min = 500
    uid_max = 60000

    # Read UID_MIN and UID_MAX if it is defined
    if os.path.isfile('/etc/login.defs'):
        with open('/etc/login.defs') as fh:
            login_data = fh.readlines()
        for line in login_data:
            if line.startswith('UID_MIN'):
                uid_min = int(line.split()[1].strip())
            if line.startswith('UID_MAX'):
                uid_max = int(line.split()[1].strip())

    with open('/etc/passwd', 'r') as fh:
        lines = fh.readlines()
        for line in lines:
            (username, encrypwd, uid, gid, gecos, homedir, shell) = line.split(':')
            iUid = int(uid)
            if iUid >= uid_min and iUid <=uid_max:
                users[username] = { 'username': username, 'homedir': homedir, 'shell': shell }

    return users


if __name__ == '__main__':
    # Read the secret key from file is it exist or generate a secret random key for the session and write in the file
    if os.path.isfile('secret.key'):
        with open('secret.key', 'r') as fh:
            app.secret_key = fh.read()
    else:
        app.secret_key = os.urandom(128)
        with open('secret.key', 'w') as fh:
            fh.write(app.secret_key)
    app.debug = False        
    app.run(host='0.0.0.0')
