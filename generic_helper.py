import re

def extract_session_id(session_str:str):


    match = re.search(r"/sessions/(.*?)/contexts/",session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string
    
    return ""

def get_str_from_food_dict(food_dict: dict):
    return ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])


if __name__ == "__main__":

    print(get_str_from_food_dict({"samosa": 2, "chhole":5}))



    #print(extract_session_id("projects/chatbot-deew/agent/sessions/a871bc7d-43fa-78b8-6ef5-0f5a0c15645c/contexts/__system_counters__"))