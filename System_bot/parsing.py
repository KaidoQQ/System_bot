import requests
from bs4 import BeautifulSoup
import time
import random
import sqlite3
import re


def get_amazon(url):
  headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
  }

  try:
    response = requests.get(url,headers=headers)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text,'html.parser')

      price = soup.select_one('.a-price-whole')

      if price:
        raw_price = price.get_text()
        clean_price = re.sub(r'\D', '', raw_price)
        return int(clean_price)
      else:
        print("Cant get a price")
    else:
      print("Cant enter to site")
      return None
  except Exception as e:
    print(f"Error {e}")
    return None
  
def update_base():
  print("🚀 Start...")
  conn = sqlite3.connect('computers.db',check_same_thread=False)
  cursor = conn.cursor()

  cursor.execute('SELECT component_name, average_price_dollar, component_url FROM components_price WHERE component_url IS NOT NULL AND component_url != ""')
  items = cursor.fetchall()

  for item in items:
    name = item[0]
    old_price = item[1]
    url = item[2]

    new_price = get_amazon(url)
    if new_price:
      if new_price != old_price:
        print(f"For {name} was found new price {new_price}")

        cursor.execute('UPDATE components_price SET average_price_dollar = ? WHERE component_name = ?',(new_price, name))
        conn.commit()
        print("✅ Success")
      else:
        print("Price the same as new")
    else:
      print("⚠️ Error")

    time.sleep(random.randint(2,5))
  
  conn.close()
  print("🏁 UPDATE IS FINISHED")

if __name__ == "__main__":
  update_base()








