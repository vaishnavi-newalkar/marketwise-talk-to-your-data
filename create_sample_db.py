"""
Create a sample SQLite database for testing
"""

import sqlite3
import os

def create_sample_database():
    """Create a sample e-commerce database"""
    
    db_path = "sample_ecommerce.db"
    
    # Remove if exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Customers table
    cursor.execute("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        city TEXT,
        country TEXT,
        signup_date DATE
    )
    """)
    
    # Create Products table
    cursor.execute("""
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT,
        price DECIMAL(10, 2),
        discontinued INTEGER DEFAULT 0
    )
    """)
    
    # Create Orders table
    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date DATE,
        total_amount DECIMAL(10, 2),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)
    
    # Create OrderItems table
    cursor.execute("""
    CREATE TABLE order_items (
        order_item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price DECIMAL(10, 2),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    """)
    
    # Insert sample customers
    customers = [
        (1, 'John Doe', 'john@example.com', 'New York', 'USA', '2023-01-15'),
        (2, 'Jane Smith', 'jane@example.com', 'London', 'UK', '2023-02-20'),
        (3, 'Bob Johnson', 'bob@example.com', 'Toronto', 'Canada', '2023-03-10'),
        (4, 'Alice Williams', 'alice@example.com', 'Sydney', 'Australia', '2023-04-05'),
        (5, 'Charlie Brown', 'charlie@example.com', 'Berlin', 'Germany', '2023-05-12'),
    ]
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers)
    
    # Insert sample products
    products = [
        (1, 'Laptop Pro', 'Electronics', 1200.00, 0),
        (2, 'Wireless Mouse', 'Electronics', 25.00, 0),
        (3, 'Office Chair', 'Furniture', 350.00, 0),
        (4, 'Desk Lamp', 'Furniture', 45.00, 1),  # Discontinued
        (5, 'USB Cable', 'Electronics', 10.00, 0),
        (6, 'Monitor Stand', 'Furniture', 80.00, 1),  # Discontinued
        (7, 'Keyboard', 'Electronics', 75.00, 0),
        (8, 'Headphones', 'Electronics', 150.00, 0),
    ]
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)
    
    # Insert sample orders
    orders = [
        (1, 1, '2023-06-01', 1225.00),
        (2, 2, '2023-06-05', 350.00),
        (3, 1, '2023-06-10', 45.00),
        (4, 3, '2023-06-15', 1360.00),
        (5, 4, '2023-06-20', 80.00),
        (6, 2, '2023-06-25', 235.00),
        (7, 5, '2023-07-01', 0.00),  # Empty order for testing
    ]
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    
    # Insert sample order items
    order_items = [
        # Order 1 (John): Laptop + Mouse
        (1, 1, 1, 1, 1200.00),
        (2, 1, 2, 1, 25.00),
        
        # Order 2 (Jane): Office Chair
        (3, 2, 3, 1, 350.00),
        
        # Order 3 (John): Desk Lamp (discontinued)
        (4, 3, 4, 1, 45.00),
        
        # Order 4 (Bob): Laptop + Keyboard + Headphones
        (5, 4, 1, 1, 1200.00),
        (6, 4, 7, 1, 75.00),
        (7, 4, 8, 1, 150.00),
        
        # Order 5 (Alice): Monitor Stand (discontinued)
        (8, 5, 6, 1, 80.00),
        
        # Order 6 (Jane): Keyboard + Headphones
        (9, 6, 7, 1, 75.00),
        (10, 6, 8, 1, 150.00),
    ]
    cursor.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Sample database created: {db_path}")
    print(f"📊 Database contains:")
    print(f"   - 5 customers")
    print(f"   - 8 products (2 discontinued)")
    print(f"   - 7 orders")
    print(f"   - 10 order items")
    print(f"\n🎯 Test scenarios available:")
    print(f"   - Customers who ordered only discontinued products (Alice)")
    print(f"   - Customers who never ordered (none in this sample)")
    print(f"   - Total revenue by customer")
    print(f"   - Products never ordered")
    
    return db_path

if __name__ == "__main__":
    create_sample_database()
