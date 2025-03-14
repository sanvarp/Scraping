import requests
import time
import concurrent.futures  
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


PROXY = "http://brd-customer-hl_ccb2cea0-zone-candidate_santiago:7y5rev14p75j@brd.superproxy.io:33335"
PROXIES = {
    "http": PROXY,
    "https": PROXY,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://tienda.surtiapp.com.co/"
}

def get_product_details(product_id: str):
    """
    Obtiene los detalles de un producto a partir de su ID usando la API interna.
    """
    url = f"https://tienda.surtiapp.com.co/api/ProductDetail/SelectedProduct/{product_id}"
    try:
        response = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=5)  
        response.raise_for_status()
        data = response.json()
        
        product_info = data.get("Value", {}).get("ProductDetailInformation", {})

        return {
            "product_URL": f"https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/ProductDetail/{product_id}",
            "subcategory": product_info.get("ClassificationName", "N/A"),
            "price": product_info.get("Price", 0.0),
            "discount_percentage": product_info.get("DiscountPercentage", 0.0),
            "discount_price": product_info.get("NewPrice", 0.0),
            "product_name": product_info.get("Name", "N/A"),
            "available_quantity": product_info.get("MaxQuantity", 0),
            "date_scrape": time.strftime("%Y-%m-%d %H:%M:%S")  
        }
    except requests.RequestException as e:
        return {"product_id": product_id, "error": f"Error obteniendo detalles: {str(e)}"}

def scrape_category(url: str):
    """
    Extrae información de los productos en la categoría, con optimización para velocidad.
    """
    start_time = time.time()

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)


    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//*[@data-product]"))
        )
    except Exception:
        print("⚠️ No se encontraron productos después de esperar 5 segundos.")


    product_elements = driver.find_elements(By.XPATH, "//*[@data-product]")
    products = []
    processed_ids = set()

    for product in product_elements:
        try:
            product_id = product.get_attribute("data-product")
            if not product_id or product_id in processed_ids:
                continue  # Evitar duplicados

            processed_ids.add(product_id)

            
            try:
                name = product.find_element(By.CLASS_NAME, "product-card-title").text.strip()
            except:
                name = "N/A"

            products.append({
                "product_name": name,
                "product_id": product_id
            })

        except Exception as e:
            print(f"❌ Error procesando un producto: {str(e)}")
            continue  

    driver.quit()

    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_product_details, [p["product_id"] for p in products]))

    
    product_details_dict = {p["product_URL"]: p for p in results}

    final_products = []
    for product in products:
        product_id = product["product_id"]
        details = product_details_dict.get(f"https://tienda.surtiapp.com.co/product/{product_id}", {})

        final_products.append({
            "product_URL": details.get("product_URL", "N/A"),
            "subcategory": details.get("subcategory", "N/A"),
            "price": details.get("price", 0.0),
            "discount_percentage": details.get("discount_percentage", 0.0),
            "discount_price": details.get("discount_price", 0.0),
            "product_name": details.get("product_name", product["product_name"]),
            "available_quantity": details.get("available_quantity", 0),
            "date_scrape": details.get("date_scrape", "N/A"),
        })

        print(f"✅ Producto encontrado: {product['product_name']} (ID: {product_id})")

    total_time = time.time() - start_time
    print(f"\n⏳ Tiempo total de ejecución: {total_time:.2f} segundos 🚀")

    return final_products
