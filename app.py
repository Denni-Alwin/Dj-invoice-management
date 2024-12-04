from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Function to connect to the SQLite database
def get_db_connection():
    connection = sqlite3.connect('local_database.db')
    connection.row_factory = sqlite3.Row  # Allows us to return rows as dictionaries
    return connection

# Function to create the table if it does not exist
def create_table():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoice_data (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        contact TEXT,
        product_type TEXT,
        product_description TEXT,
        damage_problem TEXT,
        address TEXT,
        job_status TEXT,
        payment_status TEXT,
        overall_status TEXT,
        given_amount REAL DEFAULT 0,
        amount REAL,
        added_date TEXT,
        completed_date TEXT
    )
    ''')
    connection.commit()
    connection.close()

# Call create_table when the app starts
create_table()

# Serve the HTML file
@app.route('/')
def serve_html():
    return send_from_directory('static', 'djbilling.html')

# API endpoint to add or update an invoice
@app.route('/add_invoice', methods=['POST'])
def add_invoice():
    data = request.json
    client_name = data.get('client_name')
    contact = data.get('contact')
    product_type = data.get('product_type')
    product_description = data.get('product_description')
    damage_problem = data.get('damage_problem')
    address = data.get('address')
    job_status = data.get('job_status')
    payment_status = data.get('payment_status')
    overall_status = data.get('overall_status')
    amount = data.get('amount')
    given_amount = data.get('given_amount', 0)  # Default to 0 if not provided
    added_date = datetime.now().strftime('%B %d, %Y, %I:%M %p') # Current date and time in ISO format
    completed_date = data.get('completed_date')

    # Check if all fields are provided
    if not client_name or not contact or not product_type or not product_description or not damage_problem or not address or not job_status or not payment_status or not overall_status or amount is None:
        return jsonify({'error': 'All fields (client_name, contact, product_type, product_description, damage_problem, address, job_status, payment_status, overall_status, amount) are required!'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
    INSERT INTO invoice_data (client_name, contact, product_type, product_description, damage_problem, address, job_status, payment_status, overall_status, amount, given_amount, added_date, completed_date) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    ''', (client_name, contact, product_type, product_description, damage_problem, address, job_status, payment_status, overall_status, amount, given_amount, added_date, completed_date))
    connection.commit()
    connection.close()

    return jsonify({'message': f'Invoice added for client: {client_name}'}), 200

# API endpoint to retrieve all details for an invoice by client name
@app.route('/get_invoice/<string:client_name>', methods=['GET'])
def get_invoice(client_name):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM invoice_data WHERE client_name=?', (client_name,))
    result = cursor.fetchone()
    connection.close()

    if result:
        return jsonify({
            'invoice_id': result['invoice_id'],
            'client_name': result['client_name'],
            'contact': result['contact'],
            'product_type': result['product_type'],
            'product_description': result['product_description'],
            'damage_problem': result['damage_problem'],
            'address': result['address'],
            'job_status': result['job_status'],
            'payment_status': result['payment_status'],
            'overall_status': result['overall_status'],
            'amount': result['amount'],
            'given_amount' : result['given_amount'],
            'added_date': result['added_date'],
            'completed_date': result['completed_date']
        }), 200
    else:
        return jsonify({'error': 'Invoice not found for the specified client'}), 404


@app.route('/get_total_amount', methods=['GET'])
def get_total_amount():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT SUM(amount) as total_amount FROM invoice_data')
    result = cursor.fetchone()
    connection.close()

    if result and result['total_amount'] is not None:
        return jsonify({'total_amount': result['total_amount']}), 200
    else:
        return jsonify({'total_amount': 0}), 200


# API endpoint to calculate amount_to_be_collected
@app.route('/get_amount_to_be_collected', methods=['GET'])
def get_amount_to_be_collected():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query to calculate the total amount and the sum of given_amount
    cursor.execute('SELECT SUM(amount) as total_amount, SUM(given_amount) as total_given FROM invoice_data')
    result = cursor.fetchone()
    connection.close()

    # Calculate the balance
    total_amount = result['total_amount'] if result['total_amount'] is not None else 0
    total_given = result['total_given'] if result['total_given'] is not None else 0
    balance_amount = total_amount - total_given

    return jsonify({
        'total_amount': total_amount,
        'total_given': total_given,
        'amount_to_be_collected': balance_amount
    }), 200


# API endpoint to update an invoice using client_name or invoice_id
@app.route('/update_invoice', methods=['PUT'])
def update_invoice():
    data = request.json
    identifier = data.get('identifier')  # This can be either client_name or invoice_id
    update_fields = data.get('update_fields')

    # Check if identifier and fields to update are provided
    if not identifier or not update_fields:
        return jsonify({'error': 'Identifier (client_name or invoice_id) and fields to update are required!'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    # Determine if the identifier is a number (assuming invoice_id is an integer)
    if identifier.isdigit():
        # Update based on invoice_id
        cursor.execute('SELECT * FROM invoice_data WHERE invoice_id=?', (int(identifier),))
    else:
        # Update based on client_name
        cursor.execute('SELECT * FROM invoice_data WHERE client_name=?', (identifier,))

    result = cursor.fetchone()

    if not result:
        connection.close()
        return jsonify({'error': 'Invoice not found for the specified identifier'}), 404

    # Build the update query dynamically based on the fields provided in update_fields
    fields_to_update = ', '.join(f"{key}=?" for key in update_fields.keys())
    values = list(update_fields.values())

    # Append the identifier value at the end of the list for the WHERE clause
    if identifier.isdigit():
        values.append(int(identifier))
        query = f'UPDATE invoice_data SET {fields_to_update} WHERE invoice_id=?'
    else:
        values.append(identifier)
        query = f'UPDATE invoice_data SET {fields_to_update} WHERE client_name=?'

    cursor.execute(query, values)
    connection.commit()
    connection.close()

    return jsonify({'message': 'Invoice updated successfully'}), 200


@app.route('/get_pending_status', methods=['GET'])
def get_pending_status():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT * FROM invoice_data 
        WHERE job_status = 'YET-TO' 
        OR payment_status = 'UNPAID' 
        OR overall_status = 'PENDING'
    ''')
    results = cursor.fetchall()
    connection.close()

    pending_entries = [
        {
            'invoice_id': row['invoice_id'],
            'client_name': row['client_name'],
            'contact': row['contact'],
            'product_type': row['product_type'],
            'product_description': row['product_description'],
            'damage_problem': row['damage_problem'],
            'address': row['address'],
            'job_status': row['job_status'],
            'payment_status': row['payment_status'],
            'overall_status': row['overall_status'],
            'amount': row['amount'],
            'given_amount' : row['given_amount'],
            'added_date': row['added_date'],
            'completed_date': row['completed_date']
        } for row in results
    ]

    return jsonify(pending_entries), 200

@app.route('/get_pending_invoice_count', methods=['GET'])
def get_pending_invoice_count():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS pending_count 
        FROM invoice_data 
        WHERE job_status = 'YET-TO' 
        AND payment_status = 'UNPAID' 
        AND overall_status = 'PENDING'
    ''')
    result = cursor.fetchone()
    connection.close()

    return jsonify({'pending_invoice_count': result['pending_count']}), 200

# API endpoint to get the count of paid invoices
@app.route('/get_paid_invoice_count', methods=['GET'])
def get_paid_invoice_count():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS paid_count 
        FROM invoice_data 
        WHERE payment_status = 'PAID'
    ''')
    result = cursor.fetchone()
    connection.close()

    return jsonify({'paid_invoice_count': result['paid_count']}), 200



@app.route('/get_invoice_by_id/<int:invoice_id>', methods=['GET'])
def get_invoice_by_id(invoice_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM invoice_data WHERE invoice_id=?', (invoice_id,))
    result = cursor.fetchone()
    connection.close()

    if result:
        return jsonify({
            'invoice_id': result['invoice_id'],
            'client_name': result['client_name'],
            'contact': result['contact'],
            'product_type': result['product_type'],
            'product_description': result['product_description'],
            'damage_problem': result['damage_problem'],
            'address': result['address'],
            'job_status': result['job_status'],
            'payment_status': result['payment_status'],
            'overall_status': result['overall_status'],
            'amount': result['amount'],
            'given_amount' : result['given_amount'],
            'added_date': result['added_date'],
            'completed_date': result['completed_date']
        }), 200
    else:
        return jsonify({'error': 'Invoice not found for the specified ID'}), 404


@app.route('/get_invoice_details', methods=['GET'])
def get_invoice_details():
    identifier = request.args.get('identifier')

    if not identifier:
        return jsonify({'error': 'Identifier (client_name or invoice_id) is required!'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if the identifier is a number (assuming invoice_id is an integer)
    if identifier.isdigit():
        cursor.execute('SELECT * FROM invoice_data WHERE invoice_id=?', (int(identifier),))
    else:
        cursor.execute('SELECT * FROM invoice_data WHERE client_name=?', (identifier,))

    result = cursor.fetchone()
    connection.close()

    if result:
        return jsonify({
            'invoice_id': result['invoice_id'],
            'client_name': result['client_name'],
            'contact': result['contact'],
            'product_type': result['product_type'],
            'product_description': result['product_description'],
            'damage_problem': result['damage_problem'],
            'address': result['address'],
            'job_status': result['job_status'],
            'payment_status': result['payment_status'],
            'overall_status': result['overall_status'],
            'amount': result['amount'],
            'given_amount' : result['given_amount'],
            'added_date': result['added_date'],
            'completed_date': result['completed_date']
        }), 200
    else:
        return jsonify({'error': 'Invoice not found for the specified identifier'}), 404



# API endpoint to retrieve all entries from the database
@app.route('/get_all_invoices', methods=['GET'])
def get_all_invoices():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM invoice_data')
    results = cursor.fetchall()
    connection.close()

    entries = [
        {
            'invoice_id': row['invoice_id'],
            'client_name': row['client_name'],
            'contact': row['contact'],
            'product_type': row['product_type'],
            'product_description': row['product_description'],
            'damage_problem': row['damage_problem'],
            'address': row['address'],
            'job_status': row['job_status'],
            'payment_status': row['payment_status'],
            'overall_status': row['overall_status'],
            'amount': row['amount'],
            'given_amount' : row['given_amount'],
            'added_date': row['added_date'],
            'completed_date': row['completed_date']
        } for row in results
    ]

    return jsonify(entries), 200

# API endpoint to delete an invoice by client name
@app.route('/delete_invoice/<string:identifier>', methods=['DELETE'])
def delete_invoice(identifier):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Check if identifier is a digit (indicating invoice_id)
    if identifier.isdigit():
        cursor.execute('DELETE FROM invoice_data WHERE invoice_id=?', (int(identifier),))
    else:
        cursor.execute('DELETE FROM invoice_data WHERE client_name=?', (identifier,))

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        return jsonify({'error': 'Invoice not found for the specified identifier'}), 404
    else:
        return jsonify({'message': f'Invoice deleted for identifier: {identifier}'}), 200

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6334, debug=True)
