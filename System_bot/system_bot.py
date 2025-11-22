import telebot
from telebot import types
from datetime import datetime
import sqlite3
import json
import atexit
import csv
from dotenv import load_dotenv 
import os

from google import genai

load_dotenv("tokens.env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")


client = genai.Client(api_key=GOOGLE_API_KEY)

bot = telebot.TeleBot(BOT_TOKEN)

user_data ={}

user_data_cache = {}


def init_database():
  conn = sqlite3.connect('computers.db',check_same_thread = False)
  cursor = conn.cursor() 

  cursor.execute('''                        
    CREATE TABLE IF NOT EXISTS users (
      user_id INTEGER PRIMARY KEY,
      current_computer INTEGER,
      computers_data TEXT,
      last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
  ''')

  cursor.execute('''
    CREATE TABLE IF NOT EXISTS components_price (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      component_type TEXT,
      component_name TEXT,
      average_price_dollar INTEGER,
      category TEXT         
      )
  ''')

  conn.commit()
  conn.close()
  print("✅ Databases initialized successfully")

def import_prices_from_csv(csv_file_path = 'components.csv'):
    try:
      conn = sqlite3.connect('computers.db',check_same_thread=False)
      cursor = conn.cursor()

      with open(csv_file_path,'r',encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile,delimiter=';')
        next(csv_reader,None)

        imported_count = 0
        error_count = 0

        for row in csv_reader:
          try:
            if len(row) >= 4:
              component_type = row[0].strip()
              component_name = row[1].strip()
              average_price_dollar = int(row[2].strip())
              category = row[3].strip()

              cursor.execute('''
                INSERT OR REPLACE INTO components_price 
                (component_type, component_name, average_price_dollar, category)
                VALUES (?, ?, ?, ?)
              ''', (component_type, component_name, average_price_dollar, category))

              imported_count += 1
              print(f"✅ Added: {component_name} - ${average_price_dollar}")
            else:
              print(f"❌ Skipped row: not enough data - {row}")
              error_count += 1
          except ValueError as e:
            print(f"❌ Data error: {row} - {e}")
            error_count += 1
          except Exception as e:
            print(f"❌ Insert error: {row} - {e}")
            error_count += 1

        conn.commit()

        print(f"\n📊 Import completed!")
        print(f"✅ Successful: {imported_count}")
        print(f"❌ Errors: {error_count}")
    except FileNotFoundError:
      print(f"❌ File {csv_file_path} not found!")
    except Exception as e:
      print(f"❌ Import error: {e}")
    finally:
      if 'conn' in locals():
        conn.close() 


init_database()
#import_prices_from_csv()
#===================== Function for retrieving user data =====================
def get_user_data(user_id):
  if user_id not in user_data_cache:
    db_data = load_user_from_db(user_id)
    if db_data:
      user_data_cache[user_id] = db_data
      print(f"✅ Loaded user {user_id} from database")
    else:
      user_data_cache[user_id]={
        'current_computer' : None,
        'computers' : [],
        'awaiting_input' : None
      }

      save_user_to_db(user_id,user_data_cache[user_id])
      print(f"✅ Created new user {user_id}")

  return user_data_cache[user_id]

def auto_save(user_id):
  if user_id in user_data_cache:
    success = save_user_to_db(user_id,user_data_cache[user_id])
    computer = get_current_computer(user_id)

    if computer:
      count_total_price(computer)
    else:
      print("❌ No computer found")
    if success:
      print(f"💾 Auto-saved user {user_id}") 
    else:
      print(f"❌ Failed to auto-save user {user_id}") 

def save_all_data_on_exit():
  print("💾 Saving all data before exit...")
  for user_id in user_data_cache:
    save_user_to_db(user_id,user_data_cache[user_id])
  print("✅ All data saved successfully")

atexit.register(save_all_data_on_exit)

#===================== Function for creating a computer and assigning/adding it to user_data['computers'] =====================
def create_new_computer(user_id,computer_name = None):
  user_data = get_user_data(user_id)
  created_at = datetime.now()

  computer_id = len(user_data['computers']) + 1

  if not computer_name:
    computer_name = f"My computer #{computer_id}"

  new_computer = {
    'id' : computer_id,
    'name' : computer_name,
    'cpu' : None,
    'cpu_price' : None,
    'ram' : None,
    'ram_price' : None,
    'gpu' : None,
    'gpu_price' : None,
    'storage' : None,
    'storage_price' : None,
    'motherboard' : None,
    'motherboard_price' : None,
    'total_price' : None,
    'created_at' : created_at
  }

  user_data['computers'].append(new_computer)
  user_data['current_computer'] = computer_id

  auto_save(user_id)

#===================== Function for retrieving the user's current computer =====================
def get_current_computer(user_id):
  user_data = get_user_data(user_id)
  current_id = user_data['current_computer']

  if current_id is None and user_data['computers']:
    user_data['current_computer'] = user_data['computers'][0]['id']
    return user_data['computers'][0]
  
  for computer in user_data['computers']:
    if computer['id'] == current_id:
      return computer
    
  return None

def is_build_complete(computer):
  components = ['cpu', 'ram', 'gpu', 'storage', 'motherboard']
  return all(computer[comp] for comp in components)

def get_build_progress(computer):
  components = ['cpu', 'ram', 'gpu', 'storage', 'motherboard']
  filled = sum(1 for comp in components if computer[comp])
  return f"🚧 Build progress: {filled}/5 components"

def save_user_to_db(user_id,user_data):   
  try:
    conn = sqlite3.connect('computers.db', check_same_thread=False)
    cursor = conn.cursor()

    computers_json = json.dumps(user_data['computers'],default=str)

    cursor.execute(''' 
        INSERT OR REPLACE INTO users
        (user_id, current_computer,computers_data)
        VALUES (?, ?, ?)
    ''',(user_id, user_data['current_computer'],computers_json))

    conn.commit()
    conn.close()
    return True
  except Exception as e:
    print(f"❌ Error saving user {user_id} to database: {e}")
    return False

def load_user_from_db(user_id):
  try:
    conn = sqlite3.connect('computers.db',check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('SELECT current_computer,computers_data FROM users WHERE user_id = ?',(user_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
      current_computer = result[0]
      computers_data = result[1]

      if computers_data:
        computers = json.loads(computers_data)
        for computer in computers:
          if computer.get('created_at') and isinstance(computer['created_at'],str):
            computer['created_at'] = datetime.fromisoformat(computer['created_at'])
      else:
        computers = []

      return {
        'current_computer' : current_computer,
        'computers' : computers,
        'awaiting_input' : None
      }
    return None
  except Exception as e:
    print(f"❌ Error loading user {user_id} from database: {e}")
    return None

#===================== Method for searching in a database based on a user request ======================
def search_component_price(search_query, component_type = None):
  conn = sqlite3.connect('computers.db', check_same_thread=False)
  cursor = conn.cursor()

  search_query = search_query.lower()
  new_search_query = search_query.split()

  new_search_list = []

  for value in new_search_query:
    if len(value) > 2:
      new_search_list.append(value)
    else:
      pass
  
  condition_and = "AND component_name LIKE ?"
  params = []

  for param in new_search_list:
    params.append(f"%{param}%")

  conditions_list = []
  count = 0

  while count != len(params):
    conditions_list.append(condition_and)
    count += 1

  conditions_and = " ".join(conditions_list)

  sql = f"SELECT * FROM components_price WHERE 1=1 {conditions_and}"
  cursor.execute(sql,params)

  result = cursor.fetchall()

  if len(result) == 0:
    condition_or = "OR component_name LIKE ?"

    conditions_list = []
    count = 0

    while count != len(params):
      conditions_list.append(condition_or)
      count += 1

    conditions_or = " ".join(conditions_list)

    sql = f"SELECT * FROM components_price WHERE 1=1 {conditions_or}"

    cursor.execute(sql,params)

    result = cursor.fetchall()

  components_with_score = []

  for item in result:
    component_name = item[2]
    score = score_relevance(new_search_list,component_name)

    component_dict = {
      'id' : item[0],
      'type' : item[1],
      'name' : item[2],
      'price' : item[3],
      'category' : item[4],
      'score' : score
    }

    components_with_score.append(component_dict)

  sorted_components = sorted(components_with_score,key=lambda x: x['score'],reverse=True)

  return sorted_components

#===================== Method used to search for how much the data in the database matches the user's input ====================
def score_relevance(search_words, component_name):
  component_name = component_name.lower()
  list_component_name = component_name.split()
  score = 0

  count_same_words = 0
  positions_found = []

  for word_search in search_words:
    for index_component,word_component_name in enumerate(list_component_name):
      if word_search == word_component_name:
        positions_found.append(index_component)
        count_same_words += 1
  
  bonus = 100
  for position in positions_found:
    if position == 0:
      score += bonus
    for bonus_minus in range(1,10):
      if bonus_minus == position:
        score += bonus - (bonus_minus * 10)
  return score

def analyze_build_with_ai(computer):
  prompt = (
    f"You are an expert in assembling computers, evaluate the assembly that I will send you now, tell me how compatible all the components are, and give 5 tips for improvement, and rate my assembly from 1 to 10\n"
    f"CPU: {computer['cpu']}\n"
    f"RAM: {computer['ram']}\n"
    f"GPU: {computer['gpu']}\n"
    f"Storage: {computer['storage']}\n"
    f"Motherboard: {computer['motherboard']}\n"
    f"Total price: {computer['total_price']}\n\n"
    f"Write the text without any markup, that is, without * and _ so that Telegram can read your message.\n\n"
  )

  try:
    response = client.models.generate_content(
      model="gemini-2.5-pro",
      contents=prompt
    )
    return response.text
  except Exception as e:
    print(f"Error AI: {e}")
    return "Failed to analyze the assembly. Please try again later." 

def count_total_price(computer):
  total = 0

  keys = ['cpu_price','ram_price','gpu_price','storage_price','motherboard_price']

  for key in keys:
    price = computer.get(key)
    if price:
      total += int(price)

  computer['total_price'] = total


@bot.message_handler(commands=["start"])
def start(message):
  user_id = message.from_user.id

  if user_id not in user_data:
    user_data[user_id] = {
      'current_computer' : None,
      'computers' : [],
      'awaiting_input' : None
    }

  show_main_menu(message.chat.id,user_id) 


def show_main_menu(chat_id,user_id):
  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("🖥️ Create new system",callback_data="tab1")
  btn2 = types.InlineKeyboardButton("👾 View all systems",callback_data="tab2")
  btn3 = types.InlineKeyboardButton("🔄 Upgrade system",callback_data="tab3")
  btn4 = types.InlineKeyboardButton("📚 View tutorials",callback_data="tab4")

  markup.row(btn1)
  markup.row(btn2,btn3)
  markup.row(btn4)

  bot.send_message(
    chat_id,
    "✨ Welcome to the Telegram bot where you can create and test your system ✨",
    reply_markup=markup
  )

@bot.callback_query_handler(func=lambda call: call.data.startswith("tab"))
def handle_tabs(call):
  tab_number = call.data.replace("tab","")

  markup = types.InlineKeyboardMarkup()

  tabs_content = {
    "1": "🖥️ Create new system\n\nWhat you wanna do first:",
    "2": "👾 View all systems\n\nChoose the system:",
    "3": "🔄 Upgrade system\n\nChoose the system:",
    "4": "📚 View tutorials\n\nChoose the tutorial:"
  }


  if tab_number == "1":
    btn1 = types.InlineKeyboardButton("💻 Create new computer",callback_data="new_comp")
    btn2 = types.InlineKeyboardButton("🔧 Add components to ur computer",callback_data="new_components")
    btn3 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    markup.row(btn1,btn2)
    markup.row(btn3)

  elif tab_number == "2":
    btn1 = types.InlineKeyboardButton("💻 Check all computers",callback_data="choose_comp")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    markup.row(btn1)
    markup.row(btn2)

  elif tab_number == "3":
    btn1 = types.InlineKeyboardButton("💻 Choose the computer", callback_data="choose_comp")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    markup.row(btn1)
    markup.row(btn2)
  
  elif tab_number == "4":
    tabs_buttons =[
      [" What is CPU","https://www.arm.com/glossary/cpu"],
      [" What is RAM","https://www.intel.com/content/www/us/en/tech-tips-and-tricks/computer-ram.html"],
      [" What is GPU","https://www.intel.com/content/www/us/en/products/docs/processors/what-is-a-gpu.html?wapkw=What%20is%20GPU"],
      [" What is Storage","https://www.intel.com/content/www/us/en/search.html?ws=typeahead#q=storage&sort=relevancy"],
      [" What is Motherboard","https://www.intel.com/content/www/us/en/gaming/resources/how-to-choose-a-motherboard.html?wapkw=motherboard"],
      ["⬅️ Back to menu","back_menu"]
      ]
    for text, data in tabs_buttons:
      if data.startswith("http"):
        markup.add(types.InlineKeyboardButton(text, url=data))
      else:
        markup.add(types.InlineKeyboardButton(text, callback_data=data))
    
  else:
    markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu"))  
    

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id = call.message.message_id,
    text = tabs_content[tab_number],
    reply_markup= markup,
  )

  bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call:call.data == "new_comp")
def create_new_comp(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)
  
  user_data['awaiting_input'] = 'computer_name'

  bot.send_message(call.message.chat.id, "💻 Enter name of your computer:")


@bot.callback_query_handler(func=lambda call: call.data == "new_components")
def show_components_menu(call):
  markup = types.InlineKeyboardMarkup()


  btn1 = types.InlineKeyboardButton("🔧 Add CPU",callback_data="add_cpu")
  btn2 = types.InlineKeyboardButton("💾 Add RAM",callback_data="add_ram")
  btn3 = types.InlineKeyboardButton("🖳 Add GPU",callback_data="add_gpu")
  btn4 = types.InlineKeyboardButton("📦 Add Storage",callback_data="add_stor")
  btn5 = types.InlineKeyboardButton("📁 Add Motherboard",callback_data="add_mb")
  btn6 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

  markup.row(btn1)
  markup.row(btn2,btn3)
  markup.row(btn4,btn5)
  markup.row(btn6)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id = call.message.message_id,
    text = "👽 Choose what you wanna do:",
    reply_markup= markup,
  )

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_") or call.data == "add_next_component")
def choose_option_to_add(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)

  if not get_current_computer(user_id):
    bot.send_message(call.message.chat.id, "❌ You dont have any computers!")
    return
  
  bot.delete_message(call.message.chat.id, call.message.message_id)

  if call.data == "add_cpu":
    user_data['awaiting_input'] = 'cpu'
    bot.send_message(call.message.chat.id, "🔧 Enter CPU model:")

  elif call.data == "add_ram":
    user_data['awaiting_input'] = 'ram'
    bot.send_message(call.message.chat.id, "💾 Enter RAM model:")

  elif call.data == "add_gpu":
    user_data['awaiting_input'] = 'gpu'
    bot.send_message(call.message.chat.id, "🖳 Enter GPU model:")
  
  elif call.data == "add_stor":
    user_data['awaiting_input'] = 'storage'
    bot.send_message(call.message.chat.id, "📦 Enter Storage model:")

  elif call.data == "add_mb":
    user_data['awaiting_input'] = 'motherboard'
    bot.send_message(call.message.chat.id, "📁 Enter Motherboard model:")

  elif call.data == "add_next_component":
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔧 Add CPU", callback_data="add_cpu")
    btn2 = types.InlineKeyboardButton("💾 Add RAM", callback_data="add_ram")
    btn3 = types.InlineKeyboardButton("🖳 Add GPU", callback_data="add_gpu")
    btn4 = types.InlineKeyboardButton("📦 Add Storage", callback_data="add_stor")
    btn5 = types.InlineKeyboardButton("📁 Add Motherboard", callback_data="add_mb")
    btn6 = types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")

    markup.row(btn1)
    markup.row(btn2, btn3)
    markup.row(btn4, btn5)
    markup.row(btn6)

    bot.send_message(
      call.message.chat.id,
      "Choose what you wanna add:",
      reply_markup=markup
    )

@bot.message_handler(func=lambda message:True)  
def handle_text_input(message):
  user_id = message.from_user.id
  user_data = get_user_data(user_id)
  state = user_data.get('awaiting_input')

  if user_data.get('awaiting_input') == 'computer_name':
    computer_name = message.text
    create_new_computer(user_id, computer_name)
    user_data['awaiting_input'] = None

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔧 Add components", callback_data="new_components"))
    markup.row(types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu"))

    bot.send_message(
      message.chat.id,
      f"✅ Computer '{computer_name}' created! Now you can add components.",
      reply_markup=markup
    )
  
  elif user_data.get('awaiting_input').startswith("manual_name_"):
    component_type = state.split("_")[-1]
    component_name = message.text 

    user_data['temp_manual_name'] = component_name

    user_data['awaiting_input'] = f"manual_price_{component_type}"
        
    bot.send_message(message.chat.id, f"💰 Now enter price for: '{component_name}' (but in $):")
    return

  elif state and state.startswith("manual_price_"):
    component_type = state.split("_")[-1]
    try:
      price = int(message.text.strip())
    except ValueError:
      bot.send_message(message.chat.id, "❌ Please enter a valid number (e.g., 250).")
      return

    component_name = user_data.get('temp_manual_name', 'Unknown Component')
    computer = get_current_computer(user_id)

    price_keys = {
      'cpu': 'cpu_price',
      'ram': 'ram_price', 
      'gpu': 'gpu_price',
      'storage': 'storage_price',
      'motherboard': 'motherboard_price'
    }

        
    computer[component_type] = component_name
    price_key = price_keys.get(component_type, f'{component_type}_price')
    computer[price_key] = price

    user_data['awaiting_input'] = None
    if 'temp_manual_name' in user_data:
        del user_data['temp_manual_name']
        
    auto_save(user_id)


    markup = types.InlineKeyboardMarkup()
    markup.row(
      types.InlineKeyboardButton("🔧 Add next component", callback_data="add_next_component"),
      types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")
      )
        
    if is_build_complete(computer):
      markup.row(types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete"))

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ Manual entry: '{component_name}' - ${price} saved!\n{progress}", 
      reply_markup=markup
      )
    return

  elif user_data.get('awaiting_input') == 'cpu':
    cpu_name = message.text
    type = 'cpu'

    price = 0

    similar_components = search_component_price(cpu_name,type)
    if len(similar_components) == 0:

      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    elif len(similar_components) == 1:
      cpu_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_cpu:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

      
    computer = get_current_computer(user_id)
    computer['cpu'] = cpu_name
    computer['cpu_price'] = price

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ New CPU: '{cpu_name}' - ${price}  was added!\n{progress}",
      reply_markup=markup
    )
        

  elif user_data.get('awaiting_input') == 'ram':
    ram_name = message.text
    type = 'ram'

    price = 0

    similar_components = search_component_price(ram_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return

    elif len(similar_components) == 1:
       ram_name = similar_components[0]['name']
       price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_ram:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['ram'] = ram_name
    computer['ram_price'] = price

    user_data['awaiting_input'] = None
    
    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ New RAM: '{ram_name}' - ${price}  was added!\n{progress}",
      reply_markup=markup
    )

  elif user_data.get('awaiting_input') == 'gpu':
    gpu_name = message.text
    type = 'gpu'

    price = 0

    similar_components = search_component_price(gpu_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_gpu")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return

    elif len(similar_components) == 1:
       gpu_name = similar_components[0]['name']
       price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_gpu:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_gpu")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['gpu'] = gpu_name
    computer['gpu_price'] = price

    user_data['awaiting_input'] = None
    
    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ New GPU: '{gpu_name}' - ${price}  was added!\n{progress}",
      reply_markup=markup
    )

  elif user_data.get('awaiting_input') == 'storage':
    stor_name = message.text
    type = 'storage'

    price = 0

    similar_components = search_component_price(stor_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_stor")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return

    elif len(similar_components) == 1:
       stor_name = similar_components[0]['name']
       price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_stor:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_stor")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['storage'] = stor_name
    computer['storage_price'] = price

    user_data['awaiting_input'] = None
    
    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ New Storage: '{stor_name}' - ${price}  was added!\n{progress}",
      reply_markup=markup
    )

  elif user_data.get('awaiting_input') == 'motherboard':
    mam_name = message.text
    type = 'motherboard'

    price = 0

    similar_components = search_component_price(mam_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_mam")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return

    elif len(similar_components) == 1:
       mam_name = similar_components[0]['name']
       price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_mam:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_mam")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['motherboard'] = mam_name
    computer['motherboard_price'] = price

    user_data['awaiting_input'] = None
    
    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    progress = get_build_progress(computer)
    bot.send_message(
      message.chat.id, 
      f"✅ New Motherboard: '{mam_name}' - ${price}  was added!\n{progress}",
      reply_markup=markup
    )



  elif user_data.get('awaiting_input') == "change_cpu":
    cpu_name = message.text
    type = 'cpu'

    price = 0

    similar_components = search_component_price(cpu_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    
    elif len(similar_components) == 1:
      cpu_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_cpu:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_cpu")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['cpu'] = cpu_name

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Change next component",callback_data="ch_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    
    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
      message.chat.id, 
      f"✅ New CPU: '{cpu_name}' was added! Now you can change next component.",reply_markup=markup
    )

  elif user_data.get('awaiting_input') == "change_ram":
    ram_name = message.text
    type = 'ram'

    price = 0

    similar_components = search_component_price(ram_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_ram")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    
    elif len(similar_components) == 1:
      ram_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_ram:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_ram")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['ram'] = ram_name

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Change next component",callback_data="ch_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    
    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
      message.chat.id, 
      f"✅ New RAM: '{ram_name}' was added! Now you can change next component.",reply_markup=markup
    )

  elif user_data.get('awaiting_input') == "change_gpu":
    gpu_name = message.text
    type = 'gpu'

    price = 0

    similar_components = search_component_price(gpu_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_gpu")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    
    elif len(similar_components) == 1:
      gpu_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_gpu:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_gpu")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['gpu'] = gpu_name

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Change next component",callback_data="ch_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    
    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
      message.chat.id, 
      f"✅ New GPU: '{gpu_name}' was added! Now you can change next component.",reply_markup=markup
    )

  elif user_data.get('awaiting_input') == "change_stor":
    stor_name = message.text
    type = 'storage'

    price = 0

    similar_components = search_component_price(stor_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_stor")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    
    elif len(similar_components) == 1:
      stor_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_stor:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_stor")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['storage'] = stor_name

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Change next component",callback_data="ch_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    
    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
      message.chat.id, 
      f"✅ New Storage: '{stor_name}' was added! Now you can change next component.",reply_markup=markup
    )

  elif user_data.get('awaiting_input') == "change_mam":
    mam_name = message.text
    type = 'motherboard'

    price = 0

    similar_components = search_component_price(mam_name,type)

    if len(similar_components) == 0:
      markup = types.InlineKeyboardMarkup()

      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
      btn3 = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_mam")

      markup.row(btn1,btn3)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,"❌ No price found for this component, you need to enter the price by ur self",reply_markup=markup
      )
      return
    
    elif len(similar_components) == 1:
      mam_name = similar_components[0]['name']
      price = similar_components[0]['price']

    elif len(similar_components) > 1:
      markup = types.InlineKeyboardMarkup()

      top_components = similar_components[:4]

      for component in top_components:
        btn_component = types.InlineKeyboardButton(f"🖥️ {component['name']} - ${component['price']}",callback_data=f"select_mam:{component['id']}:{component['name']}:{component['price']}")
        markup.add(btn_component)

      btn = types.InlineKeyboardButton("💸 Enter manually",callback_data="enter_price_mam")
      btn1 = types.InlineKeyboardButton("🔧 Add next component",callback_data="add_next_component")
      btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

      markup.row(btn1,btn)
      markup.row(btn2)

      bot.send_message(
        message.chat.id,
        "🔍 Found several options. Choose one:",
        reply_markup=markup
      )
      return

    computer = get_current_computer(user_id)
    computer['motherboard'] = mam_name

    user_data['awaiting_input'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🔧 Change next component",callback_data="ch_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    
    if is_build_complete(computer):
      btn3 = types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete")
      markup.row(btn3)

    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
      message.chat.id, 
      f"✅ New Motherboard: '{mam_name}' was added! Now you can change next component.",reply_markup=markup
    )
  
@bot.callback_query_handler(func=lambda call: call.data == "choose_comp")
def choose_comp(call):
  user_id = call.from_user.id
  chat_id = call.message.chat.id
  user_data = get_user_data(user_id)
  computers = user_data['computers']
  markup = types.InlineKeyboardMarkup()

  if len(user_data['computers']) == 1:
    computer = get_current_computer(user_id)
    btn1 = types.InlineKeyboardButton(f"Computer: {computer['name']}",callback_data=f"comp_{computer['id']}")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

  elif len(user_data['computers']) == 0:
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")
    markup.row(btn2)
    
    bot.edit_message_text(
      chat_id=call.message.chat.id,
      message_id=call.message.message_id,
      text="❌ You need to create ur first computer",
      reply_markup=markup
    )
    return

  else:
    for computer in computers:
      btn = types.InlineKeyboardButton(f"Computer: {computer['name']}",callback_data=f"comp_{computer['id']}")
      markup.add(btn)
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.add(btn2)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text="👾 Choose your computer:",
    reply_markup=markup
  )
  
@bot.callback_query_handler(func=lambda call: call.data.startswith("comp_"))
def option_with_computers(call):
  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("🆙 Change component", callback_data="ch_component")
  btn2 = types.InlineKeyboardButton("👀 View all components",callback_data="view_components") 
  btn3 = types.InlineKeyboardButton("🗑️ Delete component", callback_data="del_component") 
  btn4 = types.InlineKeyboardButton("🤖 Check the build using AI", callback_data="ai_check")
  btn5 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu") 

  markup.row(btn1,btn2)
  markup.row(btn3,btn4)
  markup.row(btn5)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text="🦾 Choose option:",
    reply_markup=markup
  )

@bot.callback_query_handler(func=lambda call: call.data == "ch_component")
def change_component(call):
  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("🔧 Change CPU",callback_data="change_cpu")
  btn2 = types.InlineKeyboardButton("💾 Change RAM",callback_data="change_ram")
  btn3 = types.InlineKeyboardButton("🖳 Change GPU",callback_data="change_gpu")
  btn4 = types.InlineKeyboardButton("📦 Change Storage",callback_data="change_stor")
  btn5 = types.InlineKeyboardButton("📁 Change Motherboard",callback_data="change_mam")
  btn6 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

  markup.row(btn1)
  markup.row(btn2,btn3)
  markup.row(btn4,btn5)
  markup.row(btn6)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text="🧐 Choose component:",
    reply_markup=markup
  )

@bot.callback_query_handler(func=lambda call: call.data == "del_component")
def delete_component(call):
  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("🔧 Delete CPU",callback_data="delete_cpu")
  btn2 = types.InlineKeyboardButton("💾 Delete RAM",callback_data="delete_ram")
  btn3 = types.InlineKeyboardButton("🖳 Delete GPU",callback_data="delete_gpu")
  btn4 = types.InlineKeyboardButton("📦 Delete Storage",callback_data="delete_stor")
  btn5 = types.InlineKeyboardButton("📁 Delete Motherboard",callback_data="delete_mam")
  btn6 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")

  markup.row(btn1)
  markup.row(btn2,btn3)
  markup.row(btn4,btn5)
  markup.row(btn6)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text="🗑️ Choose component to delete:",
    reply_markup=markup
  )

@bot.callback_query_handler(func=lambda call: call.data == "view_components")
def view_components(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)
  computer = get_current_computer(user_id)

  if not computer:
    bot.send_message(call.message.chat.id, "❌ No computer found!")
    return

  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
  markup.row(btn1)

  bot.edit_message_text(
    chat_id = call.message.chat.id,
    message_id = call.message.message_id,
    text =  f"🖥️ **Computer Components:**\n\n"
            f"📅 Created: {computer['created_at'].strftime('%d.%m.%Y')}\n\n"
            f"**Components:**\n"
            f"🔧 **CPU:** {computer['cpu'] or '❌ Not set'}\n"
            f"💾 **RAM:** {computer['ram'] or '❌ Not set'}\n" 
            f"🖳 **GPU:** {computer['gpu'] or '❌ Not set'}\n"
            f"📦 **Storage:** {computer['storage'] or '❌ Not set'}\n"
            f"📁 **Motherboard:** {computer['motherboard'] or '❌ Not set'}\n"
            f"💰 **Total price: {computer['total_price'] or '❌ Not calculated'}$",
    reply_markup=markup,
    parse_mode="Markdown"
  )

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_"))        
def change_option(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)
  computer = get_current_computer(user_id)

  if call.data == "change_cpu":
    user_data['awaiting_input'] = 'change_cpu'

    current_value = computer['cpu'] or "Not set"
    bot.send_message(
        call.message.chat.id, 
        f"🔧 Change CPU\nCurrent: {current_value}\n\nEnter new CPU model:"
    )

  elif call.data == "change_ram":
    user_data['awaiting_input'] = "change_ram"

    current_value = computer['ram'] or "Not set"
    bot.send_message(
        call.message.chat.id, 
        f"💾 Change RAM\nCurrent: {current_value}\n\nEnter new RAM model:"
    )

  elif call.data == "change_gpu":
    user_data['awaiting_input'] = "change_gpu"

    current_value = computer['gpu'] or "Not set"
    bot.send_message(
        call.message.chat.id, 
        f"🖳 Change GPU\nCurrent: {current_value}\n\nEnter new GPU model:"
    )

  elif call.data == "change_stor":
    user_data['awaiting_input'] = "change_stor"

    current_value = computer['storage'] or "Not set"
    bot.send_message(
        call.message.chat.id, 
        f"📦 Change Storage\nCurrent: {current_value}\n\nEnter new Storage model:"
    )

  elif call.data == "change_mam":
    user_data['awaiting_input'] = "change_mam"

    current_value = computer['motherboard'] or "Not set"
    bot.send_message(
        call.message.chat.id, 
        f"📁 Change Motherboard\nCurrent: {current_value}\n\nEnter new Motherboard model:"
    )
  
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_option(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)
  computer = get_current_computer(user_id)

  if call.data == "delete_cpu":
    computer['cpu'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🗑️ Delete next component",callback_data="del_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
    call.message.chat.id, 
    f"🔧 **💔 CPU deleted**\n\nComponent has been removed from {computer['name']}",
    reply_markup=markup,
    parse_mode="Markdown"
    )

  elif call.data == "delete_ram":
    computer['ram'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🗑️ Delete next component",callback_data="del_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
    call.message.chat.id, 
    f"🔧 **💔 RAM deleted**\n\nComponent has been removed from {computer['name']}",
    reply_markup=markup,
    parse_mode="Markdown"
    )
  
  elif call.data == "delete_gpu":
    computer['gpu'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🗑️ Delete next component",callback_data="del_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
    call.message.chat.id, 
    f"🔧 **💔 GPU deleted**\n\nComponent has been removed from {computer['name']}",
    reply_markup=markup,
    parse_mode="Markdown"
    )

  elif call.data == "delete_stor":
    computer['storage'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🗑️ Delete next component",callback_data="del_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
    call.message.chat.id, 
    f"🔧 **💔 Storage deleted**\n\nComponent has been removed from {computer['name']}",
    reply_markup=markup,
    parse_mode="Markdown"
    )

  elif call.data == "delete_mam":
    computer['motherboard'] = None

    auto_save(user_id)

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🗑️ Delete next component",callback_data="del_component")
    btn2 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu")
    markup.row(btn1)
    markup.row(btn2)

    bot.send_message(
    call.message.chat.id, 
    f"🔧 **💔 Motherboard deleted**\n\nComponent has been removed from {computer['name']}",
    reply_markup=markup,
    parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_price_"))
def manually_price_enter(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)

  component_type = call.data.replace("enter_price_","")
  user_data['awaiting_input'] = f"manual_name_{component_type}"

  bot.send_message(
      call.message.chat.id, 
      f"✍️ Now enter name of: {component_type.upper()}:"
    )
  bot.answer_callback_query(call.id) 

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def show_buttons_with_components(call):
  user_id = call.from_user.id
  user_data = get_user_data(user_id)
  computer = get_current_computer(user_id)

  data = call.data.split(":")
  component_selection_part = data[0]
  component_name = data[2]
  component_price = int(data[3])
  component_label = ""
  
  component_map = {
    "select_cpu" : ("cpu","cpu_price","CPU"),
    "select_ram" : ("ram","ram_price","RAM"),
    "select_gpu" : ("gpu","gpu_price","GPU"),
    "select_stor" : ("storage","stor_price","Storage"),
    "select_mam" : ("motherboard","motherboard_pice","Mother_board")
  }

  if component_selection_part in component_map:
    key,key_price,label = component_map[component_selection_part]
    computer[key] = component_name
    computer[key_price] = component_price
    component_label = label

  auto_save(user_id)

  markup = types.InlineKeyboardMarkup()

  markup.row(
    types.InlineKeyboardButton("🔧 Add next component", callback_data="add_next_component"),
    types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu"))
  
  if is_build_complete(computer):
    markup.row(types.InlineKeyboardButton("🎉 Build Complete!", callback_data="build_complete"))

  progress = get_build_progress(computer)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text=f"✅ Selected {component_label}: '{component_name}' - ${component_price} was added!\n{progress}",
    reply_markup=markup
  )

@bot.callback_query_handler(func=lambda call:call.data == "back_menu")
def back_menu(call):
  markup = types.InlineKeyboardMarkup()

  btn1 = types.InlineKeyboardButton("🖥️ Create new system",callback_data="tab1")
  btn2 = types.InlineKeyboardButton("👾 View all systems",callback_data="tab2")
  btn3 = types.InlineKeyboardButton("🔄 Upgrade system",callback_data="tab3")
  btn4 = types.InlineKeyboardButton("📚 View tutorials",callback_data="tab4")

  markup.row(btn1)
  markup.row(btn2,btn3)
  markup.row(btn4)

  bot.edit_message_text(
    chat_id=call.message.chat.id, 
    message_id=call.message.message_id,
    text="✨ Welcome to the Telegram bot where you can create and test your system ✨",
    reply_markup=markup
  )
  bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "build_complete")
def build_complete(call):
  user_id = call.from_user.id
  computer = get_current_computer(user_id)
    
  markup = types.InlineKeyboardMarkup()
  btn1 = types.InlineKeyboardButton("👀 View Components", callback_data="view_components")
  btn2 = types.InlineKeyboardButton("🔄 Upgrade system", callback_data="ch_component")
  btn3 = types.InlineKeyboardButton("🖥️ Create New", callback_data="new_comp")
  btn4 = types.InlineKeyboardButton("🤖 Check the build using AI", callback_data="ai_check")
  btn5 = types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")
    
  markup.row(btn1, btn2)
  markup.row(btn3,btn4)
  markup.row(btn5)

  bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text= f"🎉 Build Complete! 🎉\n\n"
          f"🖥️ {computer['name']} is ready!\n\n"
          f"All components have been added:\n"
          f"🔧 {computer['cpu']}\n"
          f"💾 {computer['ram']}\n"
          f"🖳 {computer['gpu']}\n"
          f"📦 {computer['storage']}\n"
          f"📁 {computer['motherboard']}\n"
          f"💰 {computer['total_price']}\n\n"
          f"Your dream computer is assembled!",
    reply_markup=markup,
    parse_mode=None
  )

@bot.callback_query_handler(func=lambda call: call.data == "ai_check")
def ai_check(call):
  user_id = call.from_user.id
  computer = get_current_computer(user_id)

  response = analyze_build_with_ai(computer)

  markup = types.InlineKeyboardMarkup()
  btn1 = types.InlineKeyboardButton("🔄 Upgrade system", callback_data="ch_component")
  btn2 = types.InlineKeyboardButton("🖥️ Create New", callback_data="new_comp")
  btn3 = types.InlineKeyboardButton("⬅️ Back to menu", callback_data="back_menu")

  markup.row(btn1,btn2)
  markup.row(btn3)

  bot.edit_message_text(
    chat_id= call.message.chat.id,
    message_id = call.message.message_id,
    text = f"🖥️ **{computer['name']}**\n\n"
           f"All components have been added:\n"
           f"🔧 {computer['cpu']}\n"
           f"💾 {computer['ram']}\n"
           f"🖳 {computer['gpu']}\n"
           f"📦 {computer['storage']}\n"
           f"📁 {computer['motherboard']}\n"
           f"💰 {computer['total_price']}\n\n"
           f"**That what AI thinks about ur build**\n\n"
           f"{response}",
    reply_markup=markup,
    parse_mode="Markdown"
  )

if __name__ == "__main__":
  print("🔐 Loading configuration...")
  print(f"✅ Google API Key loaded: {'Yes' if GOOGLE_API_KEY else 'No'}")
  print(f"✅ Bot Token loaded: {'Yes' if BOT_TOKEN else 'No'}")
  print("🖥️ Computer Builder Bot with Database is running...")
  print("💾 Data will be saved in 'computers.db' file")
  bot.infinity_polling()