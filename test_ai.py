import trending_updater
import json, requests
text = trending_updater.preprocess_html(trending_updater.get_amazon_trending('https://www.amazon.in/gp/movers-and-shakers/electronics'))
print("Extracted text length:", len(text))
prompt = f"""
Below is a list of Amazon products with prices. Pick the TOP 5 products with the BEST DISCOUNT percentage.
Return ONLY a valid JSON array of objects with keys: "name", "price", "mrp", "discount_percent", "link", "image".

CRITICAL TRUST RULES:
1. "price" & "mrp": MUST be strings containing ONLY numbers/commas/dots (e.g. "499"). NEVER use percentage in price.
2. "discount_percent": MUST be a valid number between 1 and 99. If "mrp" is missing from the text, estimate a realistic MRP that is 30% to 70% higher than the price, and output that MRP and the calculated discount_percent.
3. "name": Keep it slightly shortened for readability.
4. DIVERSITY: DO NOT select more than ONE Air Conditioner (AC) or similar repetitive large appliances. Pick diverse items (e.g., smartphones, gadgets, clothing, accessories, kitchen tools).
5. Ensure the response starts with [ and ends with ]. No markdown formatting.

DATA:
{text}
"""
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={trending_updater.GEMINI_API_KEY}"
r = requests.post(url, json={'contents': [{'parts': [{'text': prompt}]}]})
print(r.text)
