import os
import mysql.connector

# Database connection setup
cnx = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 3306)),  # Default to 3306 if DB_PORT is not set
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

# Insert tracking info into the database
def insert_order_tracking(order_id, status):
    try:
        cursor = cnx.cursor()
        insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
        cursor.execute(insert_query, (order_id, status))
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error inserting order tracking: {err}")
        cnx.rollback()
    finally:
        cursor.close()

# Get total order price for a given order ID
def get_total_order_price(order_id):
    try:
        cursor = cnx.cursor()
        query = "SELECT get_total_order_price(%s)"
        cursor.execute(query, (order_id,))
        
        result = cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            print(f"No total price found for order ID {order_id}")
            return 0  # Return a default value if not found
    except mysql.connector.Error as err:
        print(f"Error fetching total order price: {err}")
        return 0
    finally:
        cursor.close()

# Insert a food item into an order
def insert_order_item(food_item, quantity, order_id):
    try:
        cursor = cnx.cursor()
        cursor.callproc('insert_order_item', (food_item, quantity, order_id))
        cnx.commit()
        print(f"Order item {food_item} inserted successfully!")
        return 1
    except mysql.connector.Error as err:
        print(f"Error inserting order item: {err}")
        cnx.rollback()
        return -1
    except Exception as e:
        print(f"An error occurred: {e}")
        cnx.rollback()
        return -1
    finally:
        cursor.close()

# Get the next available order ID
def get_next_order_id():
    try:
        cursor = cnx.cursor()
        query = "SELECT MAX(order_id) FROM orders"
        cursor.execute(query)
        
        result = cursor.fetchone()
        if result[0] is None:
            return 1  # Start from 1 if no orders are in the database
        return result[0] + 1
    except mysql.connector.Error as err:
        print(f"Error fetching next order ID: {err}")
        return -1
    finally:
        cursor.close()

# Get the status of an order
def get_order_status(order_id: int):
    try:
        cursor = cnx.cursor()
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        
        result = cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None
    except mysql.connector.Error as err:
        print(f"Error fetching order status: {err}")
        return None
    finally:
        cursor.close()




"""import os

import mysql.connector



cnx = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
)

def insert_order_tracking(order_id, status):
    cursor = cnx.cursor()

    insert_query = "insert into order_tracking (order_id,status) values (%s,%s)"
    cursor.execute(insert_query,(order_id,status))

    cnx.commit()


    cursor.close()
    

def get_total_order_price(order_id):
    cursor = cnx.cursor()

    query = f"select get_total_order_price({order_id})"
    cursor.execute(query)

    result = cursor.fetchone()[0]

    cursor.close()

    return result

def insert_order_item(food_item, quantity, order_id):
    try:

        cursor = cnx.cursor()

        cursor.callproc('insert_order_item', (food_item,quantity,order_id))

        cnx.commit()

        cursor.close()

        print("Order item inserted successfully!")

        return 1
    except mysql.connector.Error as err:
        print(f"Error inserting order item:{err}")
              
        cnx.rollback()

        return -1
    
    except Exception as e:
        print(f"An error occurred: {e}")

        cnx.rollback()

        return -1




def get_next_order_id():
    cursor = cnx.cursor()

    query = "select max(order_id) from orders"
    cursor.execute(query)

    result = cursor.fetchone()[0]

    cursor.close()

    if result is None:
        return 1
    else:
        return result + 1


def get_order_status(order_id: int):
    cursor = cnx.cursor()

    query = "SELECT status FROM order_tracking WHERE order_id = %s"
    cursor.execute(query, (order_id,))

    result = cursor.fetchone()

    cursor.close()
    

    if result is not None:
        return result[0]
    else:
        return None
"""