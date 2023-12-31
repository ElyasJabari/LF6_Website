from flask import Flask, request, jsonify, render_template, redirect, url_for
import psycopg2
from datetime import datetime, timedelta

app = Flask(__name__)


class Connection:
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'database': 'dev',
        'user': 'postgres',
        'password': 'postgres',
        'port': '5432',
    }

    def __init__(self, host, database, user, password):
        try:
            # Establish a connection to the PostgreSQL database
            self.connection = psycopg2.connect(**Connection.db_params)
        except psycopg2.Error as e:
            raise ConnectionError(f'Error connecting to {database}\n\n{str(e)}')

    @staticmethod
    def get():
        # Static method to get a Connection instance
        return Connection('localhost', 'dev', 'postgres', 'postgres')

    @staticmethod
    def query_data(select_query):
        # Query data from the table using a provided SELECT query
        connection = Connection.get()
        with connection.connection.cursor() as cursor:
            cursor.execute(select_query)
            rows = cursor.fetchall()
            return rows

    @staticmethod
    def execute_query(query, values=None):
        # Execute INSERT or UPDATE queries on the table
        connection = Connection.get()
        with connection.connection.cursor() as cursor:
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
        connection.connection.commit()

    @staticmethod
    def get_ref_by_id(table, column, id__):
        # Get reference values by ID from a specified table and column
        select_query = f'SELECT {column} FROM {table} WHERE id = {id__};'
        result = Connection.query_data(select_query)
        if result:
            name = result[0][0]
            return name
        else:
            raise ValueError(f'Could not find {table}.{column} for id {id__}')

    @staticmethod
    def get_id(table, column, value):
        # Get the ID by matching a value in a specified table and column
        select_query = f'SELECT id FROM {table} WHERE {column} = {value};'
        result = Connection.query_data(select_query)
        if result:
            id__ = result[0][0]
            return id__
        else:
            raise ValueError(f'Could not find {table}.{column} for value {value}')


class User:
    class Password:
        @staticmethod
        def hash(password):
            # Simple password hashing method (replace with a secure hashing algorithm)
            # TODO: https://stackoverflow.com/questions/9594125/salt-and-hash-a-password-in-python
            return password[::-1]

    class Role:
        @staticmethod
        def get_role_name(role_id):
            # Get the role name by ID
            return Connection.get_ref_by_id('ref_role', 'name', role_id)

    def __init__(self, id__, username, password, role_id):
        self.id = id__
        self.username = username
        self.password = password
        self.role_id = role_id

    def serialize(self):
        # Serialize user information
        return {
            'username': self.username,
            'id': self.id,
            'password': self.password,
            'role_id': self.role_id
        }

    def __eq__(self, other):
        # Check if two User objects are equal
        return self.username == other.username and self.password == other.password

    @staticmethod
    def checkLogin(username, password):
        connection = Connection.get()
        gehashtes_passwort = User.Password.hash(password)
        with connection.connection.cursor() as cursor:
            cursor.execute("select role_id from tbl_user where username = %s and password = %s", (username, gehashtes_passwort))
            user_data = cursor.fetchone()
            return {'loginOk': cursor.rowcount == 1, 'role_id': user_data[0] if user_data else None}

    @staticmethod
    def user_exists(username):
        connection = Connection.get()
        with connection.connection.cursor() as cursor:
            cursor.execute("select * from tbl_user where username = %s", (username,))
            return cursor.rowcount == 1

    @staticmethod
    def create_user(benutzername, passwort, role_id):
        gehashtes_passwort = User.Password.hash(passwort)
        insert_user_query = 'INSERT INTO tbl_user (username, password, role_id) VALUES (%s, %s, %s);'
        values = (benutzername, gehashtes_passwort, role_id)
        Connection.execute_query(insert_user_query, values)
        return {'status': 200, 'message': 'Benutzer erfolgreich erstellt', 'account_url': 'URL_ZUR_WEITERLEITUNG'}


class Ticket:
    class Device:
        @staticmethod
        def get_device_name(device_id):
            # Get the device name by ID
            return Connection.get_ref_by_id('ref_device', 'name', device_id)

        @staticmethod
        def get_all_devices():
            # Get a list of all devices with their IDs and names
            select_all_query = "SELECT id, name FROM ref_device;"
            result = Connection.query_data(select_all_query)
            devices = [{'id': row[0], 'name': row[1]} for row in result]
            return devices

    class Status:
        @staticmethod
        def get_status_name(status_id):
            # Get the status name by ID
            return Connection.get_ref_by_id('ref_status', 'name', status_id)

        @staticmethod
        def get_all_statuses():
            # Get a list of all statuses with their IDs and names
            select_all_query = "SELECT id, name FROM ref_status;"
            result = Connection.query_data(select_all_query)
            statuses = [{'id': row[0], 'name': row[1]} for row in result]
            return statuses

    class Category:
        @staticmethod
        def get_category_name(category_id):
            # Get the category name by ID
            return Connection.get_ref_by_id('ref_category', 'name', category_id)

        @staticmethod
        def get_all_categories():
            # Get a list of all categories with their IDs and names
            select_all_query = "SELECT id, name FROM ref_category;"
            result = Connection.query_data(select_all_query)
            categories = [{'id': row[0], 'name': row[1]} for row in result]
            return categories

    def __init__(self, title, description, ticket_id, creation_date, due_date, device_id, category_id, status_id):
        self.title = title
        self.description = description
        self.id = ticket_id
        self.creation_date = creation_date
        self.due_date = due_date
        self.device_id = device_id
        self.category_id = category_id
        self.status_id = status_id

    def serialize(self):
        # Serialize ticket information
        return {
            'title': self.title,
            'id': self.id,
            'description': self.description,
            'status': self.status_id,
            'category': self.category_id,
            'device': self.device_id,
            'creation_date': self.creation_date,
            'due_date': self.due_date
        }

    @staticmethod
    def create(title, description, device, category, status):
        # Create a new ticket with default dates
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        due_date = (datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d %H:%M:%S')
        insert_query = "INSERT INTO tbl_ticket (title, description, creation_date, due_date, device_id, category_id, status_id) VALUES (%s, %s, %s, %s, %s, %s, %s);"
        values = (title, description, current_date, due_date, device, category, status)
        Connection.execute_query(insert_query, values)

    @staticmethod
    def get_ticket_by_id(ticket_id):
        # Get a ticket by ID
        select_query = f'SELECT * FROM tbl_ticket WHERE id = {ticket_id};'
        values = (ticket_id,)
        result = Connection.query_data(select_query)
        if result:
            row = result[0]
            ticket = Ticket(
                ticket_id=row[0],
                title=row[1],
                description=row[2],
                creation_date=row[3],
                due_date=row[4],
                device_id=row[5],
                category_id=row[6],
                status_id=row[7]
            )
            return ticket
        else:
            raise ValueError(f'Could not find ticket with id {ticket_id}')

    def save_ticket_to_db(self):
        # Update a ticket by ID
        update_query = "UPDATE tbl_ticket SET title = %s, description = %s, device_id = %s, category_id = %s, status_id = %s WHERE id = %s;"
        values = (self.title, self.description, self.device_id, self.category_id, self.status_id, self.id)
        Connection.execute_query(update_query, values)

    @staticmethod
    def get_all_tickets_serialized():
        # Get all tickets and serialize them
        select_all_query = "SELECT * FROM tbl_ticket;"
        result = Connection.query_data(select_all_query)
        tickets = []
        for row in result:
            ticket = Ticket(
                ticket_id=row[0],
                title=row[1],
                description=row[2],
                creation_date=row[3],
                due_date=row[4],
                device_id=row[5],
                category_id=row[6],
                status_id=row[7]
            )
            tickets.append(ticket.serialize())
        return tickets


# Endpoint for posting Ticket objects
@app.route('/ticket', methods=['POST'])
def post_ticket():
    try:
        data = request.get_json()
        # Deserialize the JSON payload into a Ticket object
        Ticket.create(data['title'], data['description'], data['device'], data['category'], data['status'])
        return jsonify({'message': 'Ticket created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Endpoint for getting all tickets as JSON
@app.route('/tickets', methods=['GET'])
def get_all_tickets():
    # Serialize all tickets to JSON
    serialized_tickets = Ticket.get_all_tickets_serialized()
    return jsonify(serialized_tickets)


# Endpoint for getting a single ticket by ID
@app.route('/ticket/<int:ticket_id>', methods=['GET'])
def get_ticket_by_id(ticket_id):
    # Find the ticket with the specified ID
    ticket = Ticket.get_ticket_by_id(ticket_id)
    if ticket:
        # Serialize the ticket to JSON
        serialized_ticket = ticket.serialize()
        return jsonify(serialized_ticket)
    else:
        return jsonify({'error': 'Ticket not found'}), 404


# Endpoint for getting the status name
@app.route('/ticket/status/<int:status_id>', methods=['GET'])
def get_status_name(status_id):
    status_name = Ticket.Status.get_status_name(status_id)
    if status_name is not None:
        return jsonify({'status_name': status_name})
    else:
        return jsonify({'error': 'Status not found'}), 404


# Endpoint for getting the category name
@app.route('/ticket/category/<int:category_id>', methods=['GET'])
def get_category_name(category_id):
    category_name = Ticket.Category.get_category_name(category_id)
    if category_name is not None:
        return jsonify({'category_name': category_name})
    else:
        return jsonify({'error': 'Category not found'}), 404


# Endpoint for getting the device name
@app.route('/ticket/device/<int:device_id>', methods=['GET'])
def get_device_name(device_id):
    device_name = Ticket.Device.get_device_name(device_id)
    if device_name is not None:
        return jsonify({'device_name': device_name})
    else:
        return jsonify({'error': 'Device not found'}), 404


# Endpoint for getting the role name
@app.route('/user/role/<int:role_id>', methods=['GET'])
def get_role_name(role_id):
    role_name = User.Role.get_role_name(role_id)
    if role_name is not None:
        return jsonify({'role_name': role_name})
    else:
        return jsonify({'error': 'Role not found'}), 404


@app.route('/status/list', methods=['GET'])
def get_all_statuses():
    # Get all statuses and return them as JSON
    all_statuses = Ticket.Status.get_all_statuses()
    return jsonify(all_statuses)


@app.route('/category/list', methods=['GET'])
def get_all_categories():
    # Get all categories and return them as JSON
    all_categories = Ticket.Category.get_all_categories()
    return jsonify(all_categories)


# Endpoint for verifying the login credentials
@app.route('/user/verify', methods=['POST'])
def login():
    data = request.get_json()
    print("Received data:", data)
    if 'username' not in data or 'password' not in data:
        print("not OK")
        return jsonify({'error': 'Username and password are required'}), 400
    else:
        print("OK")
    username = data['username']
    password = data['password']
    try:
        user_login_ok = User.checkLogin(username, password)
        print("OK")
    except Exception as e:
        print(e)
        return jsonify({'error': f'No user could be found.\n\n{str(e)}'}), 400
    # Check if the provided credentials are valid
    if user_login_ok['loginOk']:
        if user_login_ok['role_id'] == 1:
            return jsonify({'status': 200, 'account_url': f'/ticketlist'})
        else:
            return jsonify({'status': 200, 'account_url': f'/support'})

    else:
        print("no johooo " + username)
        return jsonify({'status': 403, 'error': 'Invalid credentials'}), 400


# In your Flask application, add the following route
@app.route('/device/list', methods=['GET'])
def get_all_devices():
    # Get all devices and return them as JSON
    all_devices = Ticket.Device.get_all_devices()
    return jsonify(all_devices)


# Endpoint for creating a new account
@app.route('/user/create', methods=['POST'])
def create():
    data = request.get_json()
    print("Received data create User:", data)
    if 'username' not in data or 'password' not in data or 'role_id' not in data:
        print("not OK CU")
        return jsonify({'error': 'Username, password and role_id are required'}), 400
    username = data['username']
    password = data['password']
    role_id = data['role_id']
    try:
        if not User.user_exists(username):
            print("hohoho CU")
            user = User.create_user(username, password, role_id)
            return jsonify({'status': 200, 'account_url': f'/createUserSuccessfully'})
        else:
            print("no hohoho CU")
            return jsonify({'error': 'Username was already taken'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/createUserSuccessfully')
def render_createUserSuccessfully():
    return render_template('createUserSuccessfully.html')


@app.route('/logout')
def logout():
    return redirect(url_for('render_login'))


# Endpoint to render login.html
@app.route('/login')
def render_login():
    return render_template('login.html')


@app.route('/success')
def render_success():
    return render_template('success.html')


# Endpoint to render ticket.html
@app.route('/ticket')
def render_ticket():
    return render_template('ticket.html')


# Endpoint to render ticketlist.html
@app.route('/ticketlist')
def render_ticketlist():
    # check cookie sessionId in user table - if ok show ticketlist else show login  --> Zukunft Elyas
    return render_template('ticketlist.html')


@app.route('/support')
def render_support():
    # check cookie sessionId in user table - if ok show support else show login  --> Zukunft Elyas
    return render_template('support.html')


# Endpoint to render technician.html
@app.route('/technician')
def render_technician():
    return render_template('technician.html')


if __name__ == '__main__':
    app.run(debug=True)
