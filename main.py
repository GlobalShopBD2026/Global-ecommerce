
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Global E-Commerce API")

# স্যাম্পল প্রোডাক্ট ডেটাবেস (ইন-মেমোরি)
products = [
    {"id": 1, "name": "Wireless Headphones", "price": 1500, "stock": 10},
    {"id": 2, "name": "Smart Watch", "price": 2500, "stock": 5},
    {"id": 3, "name": "Mechanical Keyboard", "price": 3200, "stock": 8},
]

cart = []
orders = []

class CartItem(BaseModel):
    product_id: int
    quantity: int = 1

class OrderRequest(BaseModel):
    customer_name: str
    phone: str
    address: str

@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Global E-Commerce</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f9; }
            .product { background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            button { background: #28a745; color: white; border: none; padding: 8px 14px; border-radius: 5px; cursor: pointer; }
            button:hover { background: #218838; }
            .box { background: white; padding: 15px; margin-top: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>Global E-Commerce Store</h1>
        <div id="product-list">লোড হচ্ছে...</div>

        <div class="box">
            <h2>আপনার কার্ট (<span id="cart-count">0</span>)</h2>
            <div id="cart-items">কার্ট খালি</div>
            <h3>মোট টাকা: <span id="cart-total">0</span> BDT</h3>
            <h4>অর্ডার করুন</h4>
            <input type="text" id="cust-name" placeholder="আপনার নাম" style="padding:8px; margin:5px 0; width:90%;"><br>
            <input type="text" id="cust-phone" placeholder="ফোন নম্বর" style="padding:8px; margin:5px 0; width:90%;"><br>
            <input type="text" id="cust-address" placeholder="ঠিকানা" style="padding:8px; margin:5px 0; width:90%;"><br>
            <button onclick="placeOrder()">Order Place</button>
            <p id="order-msg" style="color: green; font-weight: bold;"></p>
        </div>

        <script>
            async function loadProducts() {
                const res = await fetch('/products');
                const data = await res.json();
                const container = document.getElementById('product-list');
                container.innerHTML = '';
                data.forEach(p => {
                    container.innerHTML += `
                        <div class="product">
                            <h3>${p.name}</h3>
                            <p>দাম: ${p.price} BDT | স্টক: ${p.stock}</p>
                            <button onclick="addToCart(${p.id})">Add to Cart</button>
                        </div>
                    `;
                });
            }

            async function addToCart(productId) {
                await fetch('/cart', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({product_id: productId, quantity: 1})
                });
                loadCart();
            }

            async function loadCart() {
                const res = await fetch('/cart');
                const data = await res.json();
                document.getElementById('cart-count').innerText = data.total_items;
                document.getElementById('cart-total').innerText = data.total_price;
                const itemsDiv = document.getElementById('cart-items');
                if (data.items.length === 0) {
                    itemsDiv.innerHTML = 'কার্ট খালি';
                    return;
                }
                itemsDiv.innerHTML = data.items.map(i => `<p>${i.name} x ${i.quantity} = ${i.subtotal} BDT</p>`).join('');
            }

            async function placeOrder() {
                const name = document.getElementById('cust-name').value;
                const phone = document.getElementById('cust-phone').value;
                const address = document.getElementById('cust-address').value;
                const res = await fetch('/orders', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({customer_name: name, phone: phone, address: address})
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('order-msg').innerText = 'অর্ডার সফল হয়েছে! Order ID: ' + data.order_id;
                    loadCart();
                    loadProducts();
                } else {
                    alert(data.detail || 'অর্ডার সম্পন্ন করা যায়নি');
                }
            }

            loadProducts();
            loadCart();
        </script>
    </body>
    </html>
    """

@app.get("/products")
def get_products():
    return products

@app.post("/cart")
def add_to_cart(item: CartItem):
    product = next((p for p in products if p["id"] == item.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["stock"] < item.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    existing = next((c for c in cart if c["product_id"] == item.product_id), None)
    if existing:
        existing["quantity"] += item.quantity
    else:
        cart.append({"product_id": item.product_id, "quantity": item.quantity})
    return {"message": "Added to cart", "cart": cart}

@app.get("/cart")
def view_cart():
    detailed_items = []
    total_price = 0
    total_items = 0
    for c in cart:
        product = next((p for p in products if p["id"] == c["product_id"]), None)
        if product:
            subtotal = product["price"] * c["quantity"]
            total_price += subtotal
            total_items += c["quantity"]
            detailed_items.append({
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": c["quantity"],
                "subtotal": subtotal
            })
    return {"items": detailed_items, "total_items": total_items, "total_price": total_price}

@app.post("/orders")
def create_order(order: OrderRequest):
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")
    if not order.customer_name or not order.phone or not order.address:
        raise HTTPException(status_code=400, detail="All customer fields are required")

    cart_summary = view_cart()
    for item in cart:
        product = next((p for p in products if p["id"] == item["product_id"]), None)
        if product:
            product["stock"] -= item["quantity"]

    new_order = {
        "order_id": len(orders) + 1,
        "customer_name": order.customer_name,
        "phone": order.phone,
        "address": order.address,
        "items": cart_summary["items"],
        "total_price": cart_summary["total_price"],
        "status": "Pending"
    }
    orders.append(new_order)
    cart.clear()
    return new_order

@app.get("/orders")
def list_orders():
    return orders
