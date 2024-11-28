import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import mysql.connector
import generic_helper
import db_helper

app = FastAPI()

# Dictionary to track in-progress orders for sessions
inprogress_orders = {}

# Database connection using environment variables
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.post("/")
async def handle_request(request: Request):
    try:
        payload = await request.json()
        intent = payload['queryResult']['intent']['displayName']
        parameters = payload['queryResult']['parameters']
        output_context = payload['queryResult'].get('outputContexts', [])
        
        # Extract session ID safely
        session_id = ""
        if output_context:
            session_id = generic_helper.extract_session_id(output_context[0].get('name', ''))

        intent_handler_dict = {
            "order.add - context : ongoing-order": add_to_order,
            "track.order - context: ongoing-tracking": track_order,
            "order.complete- context: ongoing-order": complete_order,
            "order.remove - context: ongoing-order": remove_from_order,
        }

        handler = intent_handler_dict.get(intent)
        if handler:
            return handler(parameters, session_id)
        else:
            return JSONResponse(content={
                "fulfillmentText": f"Unsupported intent: {intent}"
            })

    except Exception as e:
        return JSONResponse(content={
            "fulfillmentText": f"An error occurred: {str(e)}"
        })

def add_to_order(parameters: dict, session_id: str):
    food_items = parameters.get('food-item', [])
    quantities = parameters.get('number', [])

    if len(food_items) != len(quantities):
        return JSONResponse(content={
            "fulfillmentText": "Sorry, I didn't understand. Can you specify food items and their quantities clearly?"
        })

    new_food_dict = dict(zip(food_items, quantities))

    if session_id in inprogress_orders:
        inprogress_orders[session_id].update(new_food_dict)
    else:
        inprogress_orders[session_id] = new_food_dict

    order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
    fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I am having trouble finding your order. Can you place a new order?"
        })

    current_order = inprogress_orders[session_id]
    food_items = parameters.get("food-item", [])

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item in current_order:
            removed_items.append(item)
            del current_order[item]
        else:
            no_such_items.append(item)

    messages = []
    if removed_items:
        messages.append(f"Removed {', '.join(removed_items)} from your order.")
    if no_such_items:
        messages.append(f"Your current order does not have {', '.join(no_such_items)}.")
    if not current_order:
        messages.append("Your order is now empty.")
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        messages.append(f"Here is what is left in your order: {order_str}")

    return JSONResponse(content={"fulfillmentText": " ".join(messages)})

def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I am having trouble finding your order. Can you place a new order?"
        })

    order = inprogress_orders[session_id]
    order_id = save_to_db(order)

    if order_id == -1:
        return JSONResponse(content={
            "fulfillmentText": "Sorry, I couldn't process your order due to a backend error."
        })

    order_total = db_helper.get_total_order_price(order_id)
    del inprogress_orders[session_id]

    fulfillment_text = (
        f"Awesome! We have placed your order. "
        f"Here is your order ID #{order_id}. "
        f"Your order total is {order_total}, payable at delivery."
    )
    return JSONResponse(content={"fulfillmentText": fulfillment_text})

def save_to_db(order: dict) -> int:
    next_order_id = db_helper.get_next_order_id()

    for food_item, quantity in order.items():
        result = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if result == -1:
            return -1

    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id

def track_order(parameters: dict, session_id: str):
    order_id = parameters.get('order_id') or parameters.get('number')
    if not order_id:
        return JSONResponse(content={
            "fulfillmentText": "Order ID is missing in the request."
        })

    try:
        order_id = int(order_id)
    except ValueError:
        return JSONResponse(content={
            "fulfillmentText": "Invalid Order ID format. Please provide a numeric value."
        })

    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order ID {order_id} is: {order_status}."
    else:
        fulfillment_text = f"No order found with order ID: {order_id}."

    return JSONResponse(content={"fulfillmentText": fulfillment_text})








"""from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper

app = FastAPI()

# Dictionary to track in-progress orders for sessions
inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    try:
        # Parse the Dialogflow payload
        payload = await request.json()
        intent = payload['queryResult']['intent']['displayName']
        parameters = payload['queryResult']['parameters']
        output_context = payload['queryResult'].get('outputContexts', [])
        
        # Extract session ID safely
        session_id = ""
        if output_context:
            session_id = generic_helper.extract_session_id(output_context[0].get('name', ''))

        # Intent handler mapping
        intent_handler_dict = {
            "order.add - context : ongoing-order": add_to_order,
            "track.order - context: ongoing-tracking": track_order,
            "order.complete- context: ongoing-order": complete_order,
            "order.remove - context: ongoing-order": remove_from_order,
        }

        # Call the appropriate handler
        handler = intent_handler_dict.get(intent)
        if handler:
            return handler(parameters, session_id)
        else:
            return JSONResponse(content={
                "fulfillmentText": f"Unsupported intent: {intent}"
            })

    except Exception as e:
        return JSONResponse(content={
            "fulfillmentText": f"An error occurred: {str(e)}"
        })


def add_to_order(parameters: dict, session_id: str):
    food_items = parameters.get('food-item', [])
    quantities = parameters.get('number', [])

    if len(food_items) != len(quantities):
        return JSONResponse(content={
            "fulfillmentText": "Sorry, I didn't understand. Can you specify food items and their quantities clearly?"
        })

    new_food_dict = dict(zip(food_items, quantities))

    # Update the session's in-progress order
    if session_id in inprogress_orders:
        inprogress_orders[session_id].update(new_food_dict)
    else:
        inprogress_orders[session_id] = new_food_dict

    order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
    fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I am having trouble finding your order. Can you place a new order?"
        })

    current_order = inprogress_orders[session_id]
    food_items = parameters.get("food-item", [])

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item in current_order:
            removed_items.append(item)
            del current_order[item]
        else:
            no_such_items.append(item)

    # Build response text
    messages = []
    if removed_items:
        messages.append(f"Removed {', '.join(removed_items)} from your order.")
    if no_such_items:
        messages.append(f"Your current order does not have {', '.join(no_such_items)}.")
    if not current_order:
        messages.append("Your order is now empty.")
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        messages.append(f"Here is what is left in your order: {order_str}")

    return JSONResponse(content={"fulfillmentText": " ".join(messages)})


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I am having trouble finding your order. Can you place a new order?"
        })

    order = inprogress_orders[session_id]
    order_id = save_to_db(order)

    if order_id == -1:
        return JSONResponse(content={
            "fulfillmentText": "Sorry, I couldn't process your order due to a backend error."
        })

    # Fetch order total and delete the session order
    order_total = db_helper.get_total_order_price(order_id)
    del inprogress_orders[session_id]

    fulfillment_text = (
        f"Awesome! We have placed your order. "
        f"Here is your order ID #{order_id}. "
        f"Your order total is {order_total}, payable at delivery."
    )
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def save_to_db(order: dict) -> int:
    next_order_id = db_helper.get_next_order_id()

    for food_item, quantity in order.items():
        result = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if result == -1:
            return -1

    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id


def track_order(parameters: dict, session_id: str):
    order_id = parameters.get('order_id') or parameters.get('number')
    if not order_id:
        return JSONResponse(content={
            "fulfillmentText": "Order ID is missing in the request."
        })

    try:
        order_id = int(order_id)
    except ValueError:
        return JSONResponse(content={
            "fulfillmentText": "Invalid Order ID format. Please provide a numeric value."
        })

    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fulfillment_text = f"The order status for order ID {order_id} is: {order_status}."
    else:
        fulfillment_text = f"No order found with order ID: {order_id}."

    return JSONResponse(content={"fulfillmentText": fulfillment_text})
"""






























# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse
# import db_helper
# import generic_helper

# app = FastAPI()

# inprogress_orders = {}

# @app.post("/")
# async def handle_request(request: Request):
    
#         # Parse the Dialogflow payload
#         payload = await request.json()
#         intent = payload['queryResult']['intent']['displayName']
#         parameters = payload['queryResult']['parameters']
#         output_context = payload['queryResult'].get('outputContexts', [])
        
#         # Extract session ID (handle missing context gracefully)
#         session_id = ""
#         if output_context:
#             session_id = generic_helper.extract_session_id(output_context[0].get('name', ''))

#         # Intent handler dictionary
#         intent_handler_dict = {
#             "order.add - context : ongoing-order": add_to_order,
#             "track.order - context: ongoing-tracking": track_order,
#             'order.complete- context: ongoing-order': complete_order,
#         }

#         # Handle the intent dynamically
#         handler = intent_handler_dict.get(intent)
#         if handler:
#             return handler(parameters, session_id)
#         # else:
#         #     return JSONResponse(content={
#         #         "fulfillmentText": f"Unsupported intent: {intent}"
#         #     })

#         # return JSONResponse(content={
#         #     "fulfillmentText": f"Error processing request: {str(e)}"
#         # })

# def remove_from_order(parameters: dict, session_id: str):
#      if session_id not in inprogress_orders:
#           return JSONResponse(content={
#               "fulfillmentText": "I am having a trouble finding your order.Sorry! Can you place a new order?" 
#           })
#      current_order = inprogress_orders[session_id]
#      food_items = parameters["food-item"]

#      removed_items = []
#      no_such_items = []



#      for item in food_items:
          
#           if item not in current_order:
#                no_such_items.append(item)
#           else:
#                removed_items.append(item)
#                del current_order[item]

#      if len(removed_items) > 0:
#           fulfillment_text =  f'Removed {",".join(removed_items)} from your order'         
#      if len(no_such_items)> 0:
#           fulfillment_text = f'Your current order does not have {",".join(no_such_items)}'
#      if len(current_order.keys() == 0):
#           fulfillment_text += "Your order is empty!"
#      else:
#           order_str = generic_helper.get_str_from_food_dict(current_order)
#           fulfillment_text += f"Here is what is left in your order: {order_str}"
#      return JSONResponse(content={
#           "fulfillmentText": fulfillment_text
#      })     
               
          
          
     
     


# def add_to_order(parameters: dict, session_id: str):
    
#         # Extract food items and quantities
#         food_items = parameters.get('food-item', [])
#         quantities = parameters.get('number', [])

        

#         if len(food_items) != len(quantities):
#             fulfillment_text = "Sorry, I didn't understand. Can you specify food items and their quantities clearly?"
#         else:
#             new_food_dict = dict(zip(food_items,quantities))
#             if session_id in inprogress_orders:
#                  current_food_dict = inprogress_orders[session_id]
#                  current_food_dict.update(new_food_dict)
#                  inprogress_orders[session_id] = current_food_dict
#             else:
#                  inprogress_orders[session_id] = new_food_dict
            
            
#             order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])

#             fulfillment_text = f"so far you have: {order_str}. Do you need anything else? ."



#         return JSONResponse(content={"fulfillmentText": fulfillment_text})

# def complete_order(parameters: dict,session_id:str):
#      if session_id not in inprogress_orders:
#           fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
#      else:
#           order = inprogress_orders[session_id]
#           order_id = save_to_db(order)

#           if order_id == -1:
#                fulfillment_text = "sorry, I couldn't process your order due to a backend error."
#           else:
#                order_total = db_helper.get_total_order_price(order_id)
#                fulfillment_text = f"Awesome . We have placed your order."\
#                                   f"Here is your order id #{order_id}."\
#                                   f"Your order total is {order_total} which you can pay at time of delivery!"
#           del inprogress_orders[session_id]           
#      return JSONResponse(content={
#          "fulfillmentText": fulfillment_text
#      })

# def save_to_db(order : dict):
#      next_order_id = db_helper.get_next_order_id()
     

#      for food_item, quantity in order.items():
#           rcode = db_helper.insert_order_item(
#                food_item,
#                quantity,
#                next_order_id
#           )

#           if rcode == -1:
#                return -1
          
#      db_helper.insert_order_tracking (next_order_id, "in progress")    
#      return   next_order_id  
               
                  


# def track_order(parameters: dict, session_id: str):
    
#         # Extract and validate order_id
#         order_id = parameters.get('order_id') or parameters.get('number')
#         if not order_id:
#             return JSONResponse(content={
#                 "fulfillmentText": "Order ID is missing in the request."
#             })

#         try:
#             order_id = int(order_id)
#         except ValueError:
#             return JSONResponse(content={
#                 "fulfillmentText": "Invalid Order ID format. Please provide a numeric value."
#             })

#         # Fetch order status from the database
#         order_status = db_helper.get_order_status(order_id)
#         if order_status:
#             fulfillment_text = f"The order status for order ID {order_id} is: {order_status}."
#         else:
#             fulfillment_text = f"No order found with order ID: {order_id}."

#         return JSONResponse(content={"fulfillmentText": fulfillment_text})
   
        


































# # from fastapi import FastAPI, Request
# # from fastapi.responses import JSONResponse
# # import db_helper
# # import generic_helper

# # app = FastAPI()

# # @app.post("/")
# # async def handle_request(request: Request):
    
# #         # Parse the Dialogflow payload
# #         payload = await request.json()
# #         intent = payload['queryResult']['intent']['displayName']
# #         parameters = payload['queryResult']['parameters']
# #         output_context = payload['queryResult']['outputContexts']
# #         session_id = generic_helper.extract_session_id(output_context[0]['name'])


# #         intent_handler_dict = {
# #             "order.add - context : ongoing-order": add_to_order,
# #             #'order.remove - context: ongoing-order': remove_from_order,
# #             #'order.complete - context: ongoing-order': complete_order,
# #             "track.order - context: ongoing-tracking": track_order
# #         }

# #         return intent_handler_dict[intent](parameters, session_id)

# #         # Route to the appropriate intent handler
# #         # if intent == "track.order - context: ongoing-tracking":
# #         #     return track_order(parameters)
# #         # elif intent == "order.add - context : ongoing-order":
# #         #     return add_to_order(parameters)

# #         # # Default response for unsupported intents
# #         # return JSONResponse(content={
# #         #     "fulfillmentText": f"Unsupported intent: {intent}"
# #         # })

    

# # def add_to_order(parameters: dict):
    
# #         # Extract food items and quantities
# #         food_items = parameters.get('food-item')
# #         quantities = parameters.get('number')

# #         if not food_items or not quantities:
# #             return JSONResponse(content={
# #                 "fulfillmentText": "Please specify both food items and quantities."
# #             })

# #         if len(food_items) != len(quantities):
# #             fulfillment_text = "Sorry, I didn't understand. Can you specify food items and their quantities clearly?"
# #         else:
# #             fulfillment_text = f"Received {food_items} and {quantities} in the backend."

# #         return JSONResponse(content={"fulfillmentText": fulfillment_text})


# # def track_order(parameters: dict):
    
# #         # Extract and validate order_id
# #         order_id = parameters.get('order_id') or parameters.get('number')
# #         if not order_id:
# #             return JSONResponse(content={
# #                 "fulfillmentText": "Order ID is missing in the request."
# #             })
        
# #             order_id = int(order_id)
       

# #         # Fetch order status from the database
# #         order_status = db_helper.get_order_status(order_id)
# #         if order_status:
# #             fulfillment_text = f"The order status for order ID {order_id} is: {order_status}."
# #         else:
# #             fulfillment_text = f"No order found with order ID: {order_id}."

# #         return JSONResponse(content={"fulfillmentText": fulfillment_text})

    
