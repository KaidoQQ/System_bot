import telebot
from telebot import types
from datetime import datetime

bot = telebot.TeleBot("8324620069:AAHdQ7Y13i7MqU7GH8eSdbZboGholXLNGd8")

user_data ={}

#===================== Function for retrieving user data =====================
def get_user_data(user_id):
  if user_id not in user_data:
    user_data[user_id] = {
      'current_computer' : None,
      'computers' : [],
      'awaiting_input' : None
    }
  return user_data[user_id]

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
    'ram' : None,
    'gpu' : None,
    'storage' : None,
    'motherboard' : None,
    'created_at' : created_at
  }

  user_data['computers'].append(new_computer)
  user_data['current_computer'] = computer_id

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


  elif user_data.get('awaiting_input') == 'cpu':
    cpu_name = message.text

    computer = get_current_computer(user_id)
    computer['cpu'] = cpu_name

    user_data['awaiting_input'] = None

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
      f"✅ New CPU: '{cpu_name}' was added!\n{progress}",
      reply_markup=markup
    )
        

  elif user_data.get('awaiting_input') == 'ram':
    ram_name = message.text

    computer = get_current_computer(user_id)
    computer['ram'] = ram_name

    user_data['awaiting_input'] = None

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
      f"✅ New RAM: '{ram_name}' was added!\n{progress}",
      reply_markup=markup
    )

  elif user_data.get('awaiting_input') == 'gpu':
    gpu_name = message.text

    computer = get_current_computer(user_id)
    computer['gpu'] = gpu_name

    user_data['awaiting_input'] = None

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
      f"✅ New GPU: '{gpu_name}' was added!\n{progress}",
      reply_markup=markup
    )
  
  elif user_data.get('awaiting_input') == 'storage':
    stor_name = message.text

    computer = get_current_computer(user_id)
    computer['storage'] = stor_name

    user_data['awaiting_input'] = None

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
      f"✅ New Storage: '{stor_name}' was added!\n{progress}",
      reply_markup=markup
    )

  elif user_data.get('awaiting_input') == 'motherboard':
    mam_name = message.text

    computer = get_current_computer(user_id)
    computer['motherboard'] = mam_name

    user_data['awaiting_input'] = None

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
      f"✅ New Motherboard: '{mam_name}' was added!\n{progress}",
      reply_markup=markup
    )



  elif user_data.get('awaiting_input') == "change_cpu":
    cpu_name = message.text

    computer = get_current_computer(user_id)
    computer['cpu'] = cpu_name

    user_data['awaiting_input'] = None

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

    computer = get_current_computer(user_id)
    computer['ram'] = ram_name

    user_data['awaiting_input'] = None

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

    computer = get_current_computer(user_id)
    computer['gpu'] = gpu_name

    user_data['awaiting_input'] = None

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

    computer = get_current_computer(user_id)
    computer['storage'] = stor_name

    user_data['awaiting_input'] = None

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

  elif user_data.get('awaiting_input') == 'change_mam':
    mam_name = message.text

    computer = get_current_computer(user_id)
    computer['motherboard'] = mam_name

    user_data['awaiting_input'] = None

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
  btn4 = types.InlineKeyboardButton("⬅️ Back to menu",callback_data="back_menu") 

  markup.row(btn1,btn2)
  markup.row(btn3)
  markup.row(btn4)

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
            f"📁 **Motherboard:** {computer['motherboard'] or '❌ Not set'}",
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

bot.infinity_polling()