import requests
def lookup(symbol):
  try:
    response = requests.get(f"https://finance.cs50.io/quote?symbol={symbol}")
    response.raise_for_status()
    stock = response.json()
  except:
    return None
   
  if "error" in stock:
    return None
  else:
    return {
      "symbol":stock["symbol"],
      "latestprice":stock["latestPrice"],
      "companyname":stock["companyName"]
    }  
def check_positveint(number):
  for i in number:
    if not (i >= "0" and i <= "9") or i == ".":
      return -1
  
  try:
    number = int(number)
  except:
    return -1
  if number <= 0:
    return -1
  return number
   
      

 