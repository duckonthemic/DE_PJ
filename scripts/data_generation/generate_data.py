"""
===============================================================================
FILE: generate_data.py
PURPOSE: Script sinh dữ liệu giả lập cho hệ thống E-commerce
AUTHOR: Data Engineering Team
VERSION: 1.0

HƯỚNG DẪN SỬ DỤNG:
    1. Đảm bảo đã cài đặt các thư viện: pip install faker pandas sqlalchemy psycopg2-binary python-dotenv
    2. Đảm bảo PostgreSQL đang chạy (docker-compose up -d postgres-source)
    3. Chạy script: python scripts/data_generation/generate_data.py

CẤU TRÚC CODE:
    1. Configuration - Cấu hình số lượng và tham số
    2. Database Connection - Kết nối database
    3. Generator Classes - Các class sinh dữ liệu
    4. Main Pipeline - Luồng chạy chính
===============================================================================
"""

import os
import sys
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import logging

# Third-party imports
from faker import Faker
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ============================================================================
# PHẦN 1: CONFIGURATION
# ============================================================================

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình logging - giúp debug khi có lỗi
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DataConfig:
    """
    💡 GIẢI THÍCH:
    Class chứa tất cả cấu hình cho việc sinh dữ liệu.
    Tách riêng để dễ điều chỉnh mà không phải sửa logic.
    
    Intern có thể thay đổi các giá trị ở đây để tạo dataset khác nhau.
    """
    
    # Số lượng records
    NUM_CUSTOMERS = 10_000      # 10,000 khách hàng
    NUM_CATEGORIES = 20        # 20 danh mục
    NUM_PRODUCTS = 1_000       # 1,000 sản phẩm
    NUM_ORDERS = 100_000       # 100,000 đơn hàng
    
    # Khoảng thời gian dữ liệu
    DATE_START = date(2024, 1, 1)    # Bắt đầu từ 1/1/2024
    DATE_END = date(2024, 12, 31)    # Kết thúc 31/12/2024
    
    # Phân bố đơn hàng theo tháng (seasonality)
    # Giá trị > 1 nghĩa là tháng đó có nhiều đơn hơn trung bình
    MONTHLY_WEIGHTS = {
        1: 0.7,   # Tháng 1: Sau Tết, ít đơn
        2: 1.3,   # Tháng 2: Tết Nguyên Đán, nhiều đơn
        3: 0.8,
        4: 0.9,
        5: 1.0,
        6: 1.0,
        7: 1.1,
        8: 1.0,
        9: 0.9,
        10: 1.1,
        11: 1.5,  # Tháng 11: Black Friday
        12: 1.8,  # Tháng 12: Giáng sinh, cao nhất
    }
    
    # Phân khúc khách hàng
    CUSTOMER_SEGMENTS = {
        'VIP': 0.05,        # 5% khách VIP - mua nhiều, giá trị cao
        'Regular': 0.30,    # 30% khách thường xuyên
        'Occasional': 0.45, # 45% khách thỉnh thoảng
        'New': 0.20,        # 20% khách mới
    }
    
    # Kênh bán hàng
    SALES_CHANNELS = {
        'Website': 0.45,      # 45% từ website
        'Mobile App': 0.30,   # 30% từ app
        'Marketplace': 0.15,  # 15% từ Shopee, Lazada...
        'Store': 0.10,        # 10% từ cửa hàng
    }
    
    # Phương thức thanh toán
    PAYMENT_METHODS = {
        'Credit Card': 0.25,
        'Bank Transfer': 0.30,
        'COD': 0.25,          # Cash on Delivery
        'E-Wallet': 0.20,
    }
    
    # Các gateway thanh toán theo method
    PAYMENT_GATEWAYS = {
        'Credit Card': ['VNPay', 'OnePay', 'Stripe'],
        'Bank Transfer': ['VNPay', 'Direct Bank'],
        'COD': [None],        # COD không cần gateway
        'E-Wallet': ['Momo', 'ZaloPay', 'VNPay'],
    }
    
    # Danh sách thành phố Việt Nam
    VN_CITIES = [
        'Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
        'Biên Hòa', 'Nha Trang', 'Huế', 'Buôn Ma Thuột', 'Đà Lạt',
        'Vũng Tàu', 'Quy Nhơn', 'Thanh Hóa', 'Nam Định', 'Thái Nguyên'
    ]


# ============================================================================
# PHẦN 2: DATABASE CONNECTION
# ============================================================================

class DatabaseConnection:
    """
    💡 GIẢI THÍCH:
    Class quản lý kết nối database.
    Sử dụng Context Manager (with statement) để tự động đóng kết nối.
    
    Ví dụ sử dụng:
        with DatabaseConnection() as db:
            db.execute_query("SELECT 1")
    """
    
    def __init__(self):
        """Khởi tạo connection string từ biến môi trường"""
        self.host = os.getenv('SOURCE_DB_HOST', 'localhost')
        self.port = os.getenv('SOURCE_DB_PORT', '5432')
        self.database = os.getenv('SOURCE_DB_NAME', 'ecommerce_source')
        self.user = os.getenv('SOURCE_DB_USER', 'postgres')
        self.password = os.getenv('SOURCE_DB_PASSWORD', 'postgres')
        
        self.engine = None
        self.connection_string = (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    def __enter__(self):
        """Được gọi khi dùng 'with' statement"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Được gọi khi kết thúc 'with' block"""
        self.close()
    
    def connect(self):
        """Tạo kết nối đến database"""
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"✅ Connected to database: {self.database}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Đóng kết nối"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def insert_dataframe(self, df: pd.DataFrame, table_name: str, schema: str = 'ecommerce'):
        """
        Insert DataFrame vào database using psycopg2 execute_values
        
        Args:
            df: Pandas DataFrame chứa data
            table_name: Tên bảng (không có schema)
            schema: Schema name (default: ecommerce)
        """
        from psycopg2.extras import execute_values
        import numpy as np
        
        try:
            # Get column names
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            
            # Replace NaN/NaT with None for proper NULL handling
            # Use where() to replace NaN/NaT values with None
            df_clean = df.where(pd.notnull(df), None)
            
            # Convert to records and handle any remaining NaT/NaN
            def clean_value(v):
                if v is pd.NaT or (hasattr(v, '__class__') and v.__class__.__name__ == 'NaTType'):
                    return None
                if isinstance(v, float) and np.isnan(v):
                    return None
                return v
            
            # Convert DataFrame to list of tuples with explicit NaT handling
            values = [tuple(clean_value(v) for v in row) for row in df_clean.values]
            
            # Get raw connection from engine
            conn = self.engine.raw_connection()
            try:
                cur = conn.cursor()
                # Use execute_values for efficient bulk insert
                insert_sql = f'INSERT INTO {schema}.{table_name} ({col_str}) VALUES %s'
                execute_values(cur, insert_sql, values, page_size=100)
                conn.commit()
                cur.close()
            finally:
                conn.close()
            
            logger.info(f"✅ Inserted {len(df)} rows into {schema}.{table_name}")
        except Exception as e:
            logger.error(f"❌ Failed to insert into {table_name}: {e}")
            raise
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Chạy query và trả về DataFrame"""
        return pd.read_sql(query, self.engine)
    
    def execute_statement(self, statement: str):
        """Chạy một SQL statement (không trả về data)"""
        with self.engine.connect() as conn:
            conn.execute(text(statement))
            conn.commit()


# ============================================================================
# PHẦN 3: GENERATOR CLASSES
# ============================================================================

class BaseGenerator:
    """
    💡 GIẢI THÍCH:
    Base class cho tất cả generator.
    Chứa các method và attribute chung.
    
    Sử dụng OOP pattern: Inheritance (kế thừa)
    """
    
    def __init__(self, config: DataConfig, seed: int = 42):
        """
        Args:
            config: DataConfig instance chứa cấu hình
            seed: Random seed để kết quả có thể reproduce được
        """
        self.config = config
        
        # Tạo Faker instance với locale Việt Nam
        self.fake = Faker(['vi_VN', 'en_US'])
        
        # Set seed cho cả Faker và random
        # Điều này đảm bảo chạy nhiều lần sẽ cho kết quả giống nhau
        Faker.seed(seed)
        random.seed(seed)
    
    @staticmethod
    def weighted_choice(options: Dict[str, float]) -> str:
        """
        Chọn ngẫu nhiên theo trọng số.
        
        💡 GIẢI THÍCH:
        Thay vì random đều (uniform), method này cho phép
        một số option có xác suất cao hơn.
        
        Ví dụ: options = {'A': 0.7, 'B': 0.2, 'C': 0.1}
        -> A có 70% cơ hội được chọn
        
        Args:
            options: Dict với key là giá trị, value là xác suất (tổng = 1)
        
        Returns:
            Một giá trị được chọn
        """
        items = list(options.keys())
        weights = list(options.values())
        return random.choices(items, weights=weights, k=1)[0]
    
    @staticmethod
    def generate_code(prefix: str, number: int, year: int = 2024) -> str:
        """
        Sinh mã code theo format chuẩn.
        
        Ví dụ: generate_code('ORD', 1, 2024) -> 'ORD-2024-000001'
        """
        return f"{prefix}-{year}-{str(number).zfill(6)}"


class CategoryGenerator(BaseGenerator):
    """
    Generator cho bảng categories.
    
    💡 GIẢI THÍCH:
    Categories là bảng lookup/dimension, thường được tạo trước
    vì các bảng khác phụ thuộc vào nó (products.category_id)
    """
    
    # Danh sách danh mục e-commerce phổ biến
    CATEGORY_LIST = [
        ('Điện thoại & Phụ kiện', 'Điện thoại di động và phụ kiện'),
        ('Laptop & Máy tính', 'Laptop, PC và linh kiện'),
        ('Điện gia dụng', 'Tủ lạnh, máy giặt, điều hòa'),
        ('Thời trang Nam', 'Quần áo, giày dép nam'),
        ('Thời trang Nữ', 'Quần áo, giày dép nữ'),
        ('Mẹ & Bé', 'Sản phẩm cho mẹ và em bé'),
        ('Sức khỏe & Làm đẹp', 'Mỹ phẩm, chăm sóc cá nhân'),
        ('Nhà cửa & Đời sống', 'Nội thất, trang trí nhà'),
        ('Thể thao & Du lịch', 'Đồ thể thao, outdoor'),
        ('Ô tô & Xe máy', 'Phụ kiện xe cộ'),
        ('Sách & VPP', 'Sách, văn phòng phẩm'),
        ('Đồ chơi', 'Đồ chơi trẻ em'),
        ('Thực phẩm & Đồ uống', 'Thực phẩm, nước giải khát'),
        ('Máy ảnh & Quay phim', 'Camera, máy ảnh, phụ kiện'),
        ('Đồng hồ', 'Đồng hồ đeo tay'),
        ('Trang sức', 'Trang sức, phụ kiện'),
        ('Thiết bị số', 'Tablet, ổ cứng, USB'),
        ('Gaming', 'Thiết bị chơi game'),
        ('Âm thanh', 'Loa, tai nghe, micro'),
        ('Voucher & Dịch vụ', 'Voucher, thẻ quà tặng'),
    ]
    
    def generate(self) -> pd.DataFrame:
        """
        Sinh dữ liệu cho bảng categories.
        
        Returns:
            DataFrame với columns: id, name, description, parent_id, is_active
        """
        categories = []
        
        for idx, (name, description) in enumerate(self.CATEGORY_LIST[:self.config.NUM_CATEGORIES], 1):
            categories.append({
                'name': name,
                'description': description,
                'parent_id': None,  # Tất cả là root category
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            })
        
        df = pd.DataFrame(categories)
        logger.info(f"Generated {len(df)} categories")
        return df


class ProductGenerator(BaseGenerator):
    """
    Generator cho bảng products.
    
    💡 GIẢI THÍCH:
    Products phụ thuộc vào categories, nên cần generate categories trước.
    Mỗi sản phẩm thuộc 1 category.
    """
    
    # Từ điển tên sản phẩm theo category
    PRODUCT_TEMPLATES = {
        'Điện thoại & Phụ kiện': ['iPhone', 'Samsung Galaxy', 'Xiaomi', 'OPPO', 'Vivo'],
        'Laptop & Máy tính': ['Laptop Dell', 'MacBook', 'Laptop HP', 'Laptop Asus', 'Laptop Lenovo'],
        'Điện gia dụng': ['Tủ lạnh', 'Máy giặt', 'Điều hòa', 'Lò vi sóng', 'Máy lọc không khí'],
        'Thời trang Nam': ['Áo sơ mi', 'Quần jean', 'Áo khoác', 'Giày da', 'Đồng hồ nam'],
        'Thời trang Nữ': ['Váy đầm', 'Áo kiểu', 'Quần tây', 'Giày cao gót', 'Túi xách'],
    }
    
    def __init__(self, config: DataConfig, category_ids: List[int], seed: int = 42):
        """
        Args:
            config: DataConfig instance
            category_ids: List các category_id đã được tạo trong DB
            seed: Random seed
        """
        super().__init__(config, seed)
        self.category_ids = category_ids
    
    def _generate_price(self) -> tuple:
        """
        Sinh giá bán và giá vốn.
        
        💡 GIẢI THÍCH:
        - unit_price: Giá bán cho khách
        - cost_price: Giá vốn (chi phí mua hàng)
        - Margin = (unit_price - cost_price) / unit_price
        - Thông thường margin từ 20-40%
        """
        # Giá từ 50k đến 50 triệu, phân bố theo log (nhiều sản phẩm giá thấp)
        price_ranges = [
            (50_000, 200_000, 0.30),      # 30% sản phẩm giá 50k-200k
            (200_000, 1_000_000, 0.35),   # 35% sản phẩm giá 200k-1tr
            (1_000_000, 5_000_000, 0.20), # 20% sản phẩm giá 1tr-5tr
            (5_000_000, 20_000_000, 0.10),# 10% sản phẩm giá 5tr-20tr
            (20_000_000, 50_000_000, 0.05),# 5% sản phẩm giá 20tr-50tr
        ]
        
        # Chọn range theo xác suất
        r = random.random()
        cumulative = 0
        for min_price, max_price, prob in price_ranges:
            cumulative += prob
            if r <= cumulative:
                unit_price = round(random.uniform(min_price, max_price), -3)  # Làm tròn nghìn
                break
        
        # Cost = 60-80% của giá bán
        margin = random.uniform(0.20, 0.40)
        cost_price = round(unit_price * (1 - margin), -3)
        
        return unit_price, cost_price
    
    def generate(self) -> pd.DataFrame:
        """
        Sinh dữ liệu cho bảng products.
        
        Returns:
            DataFrame với các cột theo schema
        """
        products = []
        
        for idx in range(1, self.config.NUM_PRODUCTS + 1):
            # Random category
            category_id = random.choice(self.category_ids)
            
            # Generate prices
            unit_price, cost_price = self._generate_price()
            
            products.append({
                'sku': f'SKU-{str(idx).zfill(6)}',
                'name': f'{self.fake.catch_phrase()} {self.fake.word().title()}',
                'description': self.fake.text(max_nb_chars=200),
                'category_id': category_id,
                'unit_price': unit_price,
                'cost_price': cost_price,
                'stock_quantity': random.randint(0, 1000),
                'is_active': random.random() > 0.05,  # 95% active
                'created_at': self.fake.date_time_between(
                    start_date='-2y',  # 2 năm trước
                    end_date='-6M'     # 6 tháng trước
                ),
                'updated_at': datetime.now(),
            })
        
        df = pd.DataFrame(products)
        logger.info(f"Generated {len(df)} products")
        return df


class CustomerGenerator(BaseGenerator):
    """
    Generator cho bảng customers.
    
    💡 GIẢI THÍCH:
    Customers là bảng dimension quan trọng.
    Mỗi customer có segment được assign dựa trên config.
    """
    
    def generate(self) -> pd.DataFrame:
        """
        Sinh dữ liệu cho bảng customers.
        
        Returns:
            DataFrame với các cột theo schema
        """
        customers = []
        
        # Tính ngày bắt đầu đăng ký (trước ngày bắt đầu data 1 năm)
        reg_start = self.config.DATE_START - timedelta(days=365)
        reg_end = self.config.DATE_END
        
        for idx in range(1, self.config.NUM_CUSTOMERS + 1):
            # Generate registration date
            reg_date = self.fake.date_between(start_date=reg_start, end_date=reg_end)
            
            # Assign segment dựa trên weighted choice
            segment = self.weighted_choice(self.config.CUSTOMER_SEGMENTS)
            
            # Random gender
            gender = random.choice(['Male', 'Female', 'Other'])
            
            # Generate name dựa trên gender
            if gender == 'Male':
                first_name = self.fake.first_name_male()
            elif gender == 'Female':
                first_name = self.fake.first_name_female()
            else:
                first_name = self.fake.first_name()
            
            customers.append({
                'customer_code': self.generate_code('CUST', idx),
                'email': f"customer{idx}@{self.fake.free_email_domain()}",
                'first_name': first_name,
                'last_name': self.fake.last_name(),
                'phone': self.fake.phone_number()[:20],
                'date_of_birth': self.fake.date_of_birth(minimum_age=18, maximum_age=70),
                'gender': gender,
                'address_line1': self.fake.street_address()[:255],
                'address_line2': None,
                'city': random.choice(self.config.VN_CITIES),
                'state': None,
                'postal_code': self.fake.postcode()[:20],
                'country': 'Vietnam',
                'segment': segment,
                'registration_date': reg_date,
                'is_active': random.random() > 0.02,  # 98% active
                'created_at': datetime.combine(reg_date, datetime.min.time()),
                'updated_at': datetime.now(),
            })
        
        df = pd.DataFrame(customers)
        logger.info(f"Generated {len(df)} customers")
        return df


class OrderGenerator(BaseGenerator):
    """
    Generator cho bảng orders và order_items.
    
    💡 GIẢI THÍCH:
    Orders là bảng fact chính. Mỗi order có:
    - 1 customer (FK)
    - 1-N order_items
    - 0-N payments
    
    Cần generate orders trước, sau đó generate order_items.
    """
    
    def __init__(self, config: DataConfig, customer_ids: List[int], 
                 product_data: pd.DataFrame, seed: int = 42):
        """
        Args:
            config: DataConfig instance
            customer_ids: List customer_id đã tạo
            product_data: DataFrame products (cần id và unit_price)
            seed: Random seed
        """
        super().__init__(config, seed)
        self.customer_ids = customer_ids
        self.product_data = product_data
        
        # Cache product info for faster lookup
        self.product_prices = dict(zip(
            product_data['id'].tolist(),
            product_data['unit_price'].tolist()
        ))
        self.product_ids = product_data['id'].tolist()
    
    def _distribute_orders_by_date(self) -> List[date]:
        """
        Phân bổ đơn hàng theo ngày với seasonality.
        
        💡 GIẢI THÍCH:
        Thay vì random đều các ngày, ta tạo distribution theo tháng
        để mô phỏng mùa cao điểm (cuối năm) và thấp điểm (sau Tết).
        
        Returns:
            List các ngày, mỗi ngày xuất hiện nhiều lần tương ứng số đơn
        """
        order_dates = []
        
        # Tính số ngày trong range
        total_days = (self.config.DATE_END - self.config.DATE_START).days
        
        # Tính số đơn trung bình mỗi ngày (base)
        avg_orders_per_day = self.config.NUM_ORDERS / total_days
        
        current_date = self.config.DATE_START
        while current_date <= self.config.DATE_END:
            # Lấy weight của tháng
            month_weight = self.config.MONTHLY_WEIGHTS.get(current_date.month, 1.0)
            
            # Thêm variation theo ngày trong tuần (cuối tuần nhiều hơn)
            weekday_weight = 1.2 if current_date.weekday() >= 5 else 1.0
            
            # Tính số đơn cho ngày này
            daily_orders = int(avg_orders_per_day * month_weight * weekday_weight)
            
            # Thêm random variation ±20%
            daily_orders = int(daily_orders * random.uniform(0.8, 1.2))
            
            # Append ngày này n lần
            order_dates.extend([current_date] * max(1, daily_orders))
            
            current_date += timedelta(days=1)
        
        # Shuffle và cắt về đúng số lượng cần
        random.shuffle(order_dates)
        return order_dates[:self.config.NUM_ORDERS]
    
    def _generate_order_items(self, order_id: int, num_items: int) -> List[Dict]:
        """
        Sinh order_items cho một order.
        
        💡 GIẢI THÍCH:
        Pareto distribution: 20% sản phẩm chiếm 80% doanh số
        -> Sản phẩm đầu list có xác suất được chọn cao hơn
        """
        items = []
        used_products = set()  # Tránh duplicate product trong 1 order
        
        for _ in range(num_items):
            # Chọn product với Pareto distribution
            # random.paretovariate(1.5) cho số nhỏ nhiều hơn số lớn
            while True:
                # Chọn index theo Pareto
                idx = min(
                    int(random.paretovariate(1.5) - 1),
                    len(self.product_ids) - 1
                )
                product_id = self.product_ids[idx]
                
                if product_id not in used_products:
                    used_products.add(product_id)
                    break
            
            # Quantity: phần lớn mua 1-2 sản phẩm
            quantity = random.choices([1, 2, 3, 4, 5], weights=[0.5, 0.3, 0.1, 0.05, 0.05])[0]
            
            # Giá tại thời điểm mua (có thể discount)
            base_price = self.product_prices[product_id]
            discount_percent = random.choices(
                [0, 5, 10, 15, 20],
                weights=[0.5, 0.2, 0.15, 0.1, 0.05]
            )[0]
            
            unit_price = base_price  # Giá gốc
            line_total = quantity * unit_price * (1 - discount_percent / 100)
            
            items.append({
                'order_id': order_id,
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_percent': discount_percent,
                'line_total': round(line_total, 2),
                'created_at': datetime.now(),
            })
        
        return items
    
    def generate(self) -> tuple:
        """
        Sinh dữ liệu cho bảng orders và order_items.
        
        Returns:
            Tuple (orders_df, order_items_df)
        """
        orders = []
        all_order_items = []
        
        # Phân bổ ngày cho orders
        order_dates = self._distribute_orders_by_date()
        
        # Status distribution
        status_weights = {
            'Completed': 0.70,   # 70% hoàn thành
            'Delivered': 0.10,   # 10% đã giao
            'Shipped': 0.05,     # 5% đang ship
            'Processing': 0.05, # 5% đang xử lý
            'Pending': 0.03,    # 3% chờ
            'Cancelled': 0.05,  # 5% hủy
            'Refunded': 0.02,   # 2% hoàn tiền
        }
        
        for idx, order_date in enumerate(order_dates, 1):
            # Random customer
            customer_id = random.choice(self.customer_ids)
            
            # Random status
            status = self.weighted_choice(status_weights)
            
            # Random channel
            channel = self.weighted_choice(self.config.SALES_CHANNELS)
            
            # Số items trong order (1-5, phần lớn 1-2)
            num_items = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.35, 0.15, 0.07, 0.03])[0]
            
            # Generate order items trước để tính total
            order_id = idx  # Temporary ID, sẽ được DB assign
            items = self._generate_order_items(order_id, num_items)
            
            # Tính totals
            subtotal = sum(item['line_total'] for item in items)
            
            # Discount ở order level (coupon)
            order_discount = random.choices([0, subtotal * 0.05, subtotal * 0.10], weights=[0.7, 0.2, 0.1])[0]
            
            # Tax 10% VAT
            tax = (subtotal - order_discount) * 0.10
            
            # Shipping fee
            shipping = random.choices([0, 20000, 30000, 50000], weights=[0.3, 0.4, 0.2, 0.1])[0]
            
            total = subtotal - order_discount + tax + shipping
            
            # Generate timestamp
            hour = random.choices(
                range(24),
                weights=[1,1,1,1,1,2,3,5,7,8,9,10,10,9,8,7,8,9,10,10,8,6,4,2]  # Peak 10am-10pm
            )[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            order_timestamp = datetime.combine(order_date, datetime.min.time()) + timedelta(
                hours=hour, minutes=minute, seconds=second
            )
            
            orders.append({
                'order_number': self.generate_code('ORD', idx),
                'customer_id': customer_id,
                'order_date': order_date,
                'order_timestamp': order_timestamp,
                'status': status,
                'subtotal': round(subtotal, 2),
                'discount_amount': round(order_discount, 2),
                'tax_amount': round(tax, 2),
                'shipping_fee': shipping,
                'total_amount': round(total, 2),
                'channel': channel,
                'shipping_address': self.fake.address(),
                'shipping_city': random.choice(self.config.VN_CITIES),
                'shipping_phone': self.fake.phone_number()[:20],
                'customer_note': self.fake.sentence() if random.random() < 0.1 else None,
                'internal_note': None,
                'created_at': order_timestamp,
                'updated_at': datetime.now(),
            })
            
            all_order_items.extend(items)
            
            # Progress log
            if idx % 10000 == 0:
                logger.info(f"Generated {idx}/{self.config.NUM_ORDERS} orders...")
        
        orders_df = pd.DataFrame(orders)
        items_df = pd.DataFrame(all_order_items)
        
        logger.info(f"Generated {len(orders_df)} orders and {len(items_df)} order items")
        
        return orders_df, items_df


class PaymentGenerator(BaseGenerator):
    """
    Generator cho bảng payments.
    
    💡 GIẢI THÍCH:
    Payments track việc thanh toán cho orders.
    - Một order có thể có nhiều payments (trả góp, partial payment)
    - Có thể có orders chưa có payment (Pending, COD chưa giao)
    - Payment status có thể khác order status
    """
    
    def __init__(self, config: DataConfig, orders_df: pd.DataFrame, seed: int = 42):
        """
        Args:
            config: DataConfig instance
            orders_df: DataFrame orders đã generate
            seed: Random seed
        """
        super().__init__(config, seed)
        self.orders_df = orders_df
    
    def generate(self) -> pd.DataFrame:
        """
        Sinh dữ liệu cho bảng payments.
        
        💡 Logic nghiệp vụ:
        - Orders với status Completed/Delivered/Shipped có payment Completed
        - Orders Cancelled có payment Failed hoặc Refunded
        - Orders Pending/Processing có thể có payment Pending hoặc không có payment
        
        Returns:
            DataFrame payments
        """
        payments = []
        payment_idx = 1
        
        for _, order in self.orders_df.iterrows():
            order_status = order['status']
            order_date = order['order_date']
            order_id = order.name + 1  # DataFrame index + 1 = DB id
            
            # Xác định xem order này có payment không
            should_have_payment = True
            payment_status = 'Completed'
            
            if order_status in ['Completed', 'Delivered', 'Shipped']:
                payment_status = 'Completed'
            elif order_status == 'Processing':
                payment_status = random.choice(['Completed', 'Processing'])
            elif order_status == 'Pending':
                # 50% Pending orders chưa có payment
                should_have_payment = random.random() > 0.5
                payment_status = 'Pending'
            elif order_status == 'Cancelled':
                # 70% cancelled orders có payment failed, 30% không có payment
                should_have_payment = random.random() > 0.3
                payment_status = 'Failed'
            elif order_status == 'Refunded':
                payment_status = 'Refunded'
            
            if not should_have_payment:
                continue
            
            # Payment method & gateway
            method = self.weighted_choice(self.config.PAYMENT_METHODS)
            gateways = self.config.PAYMENT_GATEWAYS[method]
            gateway = random.choice(gateways)
            
            # Payment date
            if payment_status == 'Completed':
                # Completed payment trong vòng 0-3 ngày sau order
                payment_date = order_date + timedelta(days=random.randint(0, 3))
                paid_at = datetime.combine(payment_date, datetime.min.time()) + timedelta(
                    hours=random.randint(8, 22),
                    minutes=random.randint(0, 59)
                )
            else:
                payment_date = order_date
                paid_at = None
            
            # Amount (có thể thanh toán thiếu/thừa cho reconciliation)
            amount = order['total_amount']
            
            # 5% cases có amount khác order total (để test reconciliation)
            if random.random() < 0.05:
                variance = random.uniform(-0.1, 0.1)  # ±10%
                amount = round(amount * (1 + variance), 2)
            
            payments.append({
                'payment_code': self.generate_code('PAY', payment_idx),
                'order_id': order_id,
                'amount': amount,
                'payment_method': method,
                'payment_gateway': gateway,
                'status': payment_status,
                'payment_date': payment_date,
                'paid_at': paid_at,
                'transaction_ref': self.fake.uuid4()[:20] if gateway else None,
                'gateway_response': None,
                'created_at': datetime.combine(order_date, datetime.min.time()),
                'updated_at': datetime.now(),
            })
            
            payment_idx += 1
        
        df = pd.DataFrame(payments)
        logger.info(f"Generated {len(df)} payments")
        return df


class InvoiceGenerator(BaseGenerator):
    """
    Generator cho bảng invoices và invoice_items.
    
    💡 GIẢI THÍCH:
    Invoices là bản ghi kế toán. Trong hệ thống thực:
    - Invoice có thể được tạo tự động khi order hoàn thành
    - Hoặc được tạo manual bởi kế toán
    - Amount có thể khác order (chiết khấu hậu mãi, điều chỉnh...)
    """
    
    def __init__(self, config: DataConfig, orders_df: pd.DataFrame, 
                 order_items_df: pd.DataFrame, seed: int = 42):
        super().__init__(config, seed)
        self.orders_df = orders_df
        self.order_items_df = order_items_df
    
    def generate(self) -> tuple:
        """
        Sinh dữ liệu cho invoices và invoice_items.
        
        💡 Logic nghiệp vụ:
        - Chỉ tạo invoice cho orders đã Completed
        - Invoice amount = order amount (có thể ±5% để test reconciliation)
        - accounting_period = YYYY-MM của invoice_date
        
        Returns:
            Tuple (invoices_df, invoice_items_df)
        """
        invoices = []
        all_invoice_items = []
        invoice_idx = 1
        
        # Chỉ tạo invoice cho orders completed
        completed_orders = self.orders_df[
            self.orders_df['status'].isin(['Completed', 'Delivered'])
        ]
        
        for _, order in completed_orders.iterrows():
            order_id = order.name + 1  # DataFrame index + 1 = DB id
            order_date = order['order_date']
            
            # Invoice date: 0-5 ngày sau order date
            invoice_date = order_date + timedelta(days=random.randint(0, 5))
            
            # Due date: 30 ngày sau invoice date
            due_date = invoice_date + timedelta(days=30)
            
            # Status
            invoice_status = random.choices(
                ['Paid', 'Issued', 'Closed'],
                weights=[0.85, 0.10, 0.05]
            )[0]
            
            # Amount (có thể khác order để test reconciliation)
            subtotal = order['subtotal']
            tax = order['tax_amount']
            
            # 3% cases có adjustment
            if random.random() < 0.03:
                adjustment = random.uniform(-0.05, 0.05)
                subtotal = round(subtotal * (1 + adjustment), 2)
                tax = round(subtotal * 0.10, 2)
            
            total = subtotal + tax
            
            # Accounting period
            accounting_period = invoice_date.strftime('%Y-%m')
            
            invoices.append({
                'invoice_number': self.generate_code('INV', invoice_idx),
                'order_id': order_id,
                'customer_id': order['customer_id'],
                'invoice_date': invoice_date,
                'due_date': due_date,
                'subtotal': subtotal,
                'tax_amount': tax,
                'total_amount': round(total, 2),
                'status': invoice_status,
                'accounting_period': accounting_period,
                'notes': None,
                'created_at': datetime.combine(invoice_date, datetime.min.time()),
                'updated_at': datetime.now(),
            })
            
            # Generate invoice items
            order_items = self.order_items_df[self.order_items_df['order_id'] == order_id]
            
            for _, item in order_items.iterrows():
                all_invoice_items.append({
                    'invoice_id': invoice_idx,
                    'product_id': item['product_id'],
                    'description': f'Sản phẩm #{item["product_id"]}',
                    'quantity': item['quantity'],
                    'unit_price': item['unit_price'],
                    'tax_rate': 10,  # VAT 10%
                    'line_total': item['line_total'],
                    'created_at': datetime.now(),
                })
            
            invoice_idx += 1
        
        invoices_df = pd.DataFrame(invoices)
        items_df = pd.DataFrame(all_invoice_items)
        
        logger.info(f"Generated {len(invoices_df)} invoices and {len(items_df)} invoice items")
        
        return invoices_df, items_df


# ============================================================================
# PHẦN 4: MAIN PIPELINE
# ============================================================================

def main():
    """
    Main function chạy toàn bộ pipeline sinh dữ liệu.
    
    💡 THỨ TỰ QUAN TRỌNG:
    1. Categories (không phụ thuộc gì)
    2. Products (phụ thuộc categories)
    3. Customers (không phụ thuộc gì)
    4. Orders & Order Items (phụ thuộc customers, products)
    5. Payments (phụ thuộc orders)
    6. Invoices & Invoice Items (phụ thuộc orders, customers)
    """
    logger.info("="*60)
    logger.info("Starting Data Generation Pipeline")
    logger.info("="*60)
    
    config = DataConfig()
    
    # Kết nối database
    with DatabaseConnection() as db:
        
        # 1. Generate và insert Categories
        logger.info("\n📦 Step 1: Generating Categories...")
        cat_gen = CategoryGenerator(config)
        categories_df = cat_gen.generate()
        db.insert_dataframe(categories_df, 'categories')
        
        # Lấy category IDs từ DB
        cat_ids = db.execute_query("SELECT id FROM ecommerce.categories")['id'].tolist()
        
        # 2. Generate và insert Products
        logger.info("\n📦 Step 2: Generating Products...")
        prod_gen = ProductGenerator(config, cat_ids)
        products_df = prod_gen.generate()
        db.insert_dataframe(products_df, 'products')
        
        # Lấy product data từ DB
        product_data = db.execute_query("SELECT id, unit_price FROM ecommerce.products")
        
        # 3. Generate và insert Customers
        logger.info("\n👥 Step 3: Generating Customers...")
        cust_gen = CustomerGenerator(config)
        customers_df = cust_gen.generate()
        db.insert_dataframe(customers_df, 'customers')
        
        # Lấy customer IDs
        cust_ids = db.execute_query("SELECT id FROM ecommerce.customers")['id'].tolist()
        
        # 4. Generate và insert Orders & Order Items
        logger.info("\n🛒 Step 4: Generating Orders and Order Items...")
        order_gen = OrderGenerator(config, cust_ids, product_data)
        orders_df, items_df = order_gen.generate()
        
        # Insert orders first
        db.insert_dataframe(orders_df, 'orders')
        
        # Get actual order IDs and update items
        order_ids = db.execute_query(
            "SELECT id, order_number FROM ecommerce.orders"
        )
        order_id_map = dict(zip(range(1, len(orders_df) + 1), order_ids['id'].tolist()))
        items_df['order_id'] = items_df['order_id'].map(order_id_map)
        
        db.insert_dataframe(items_df, 'order_items')
        
        # 5. Generate và insert Payments
        logger.info("\n💳 Step 5: Generating Payments...")
        pay_gen = PaymentGenerator(config, orders_df)
        payments_df = pay_gen.generate()
        
        # Update order_id mapping
        payments_df['order_id'] = payments_df['order_id'].map(order_id_map)
        db.insert_dataframe(payments_df, 'payments')
        
        # 6. Generate và insert Invoices & Invoice Items
        logger.info("\n📄 Step 6: Generating Invoices...")
        inv_gen = InvoiceGenerator(config, orders_df, items_df)
        invoices_df, inv_items_df = inv_gen.generate()
        
        # Update mappings
        invoices_df['order_id'] = invoices_df['order_id'].map(order_id_map)
        db.insert_dataframe(invoices_df, 'invoices')
        
        # Get invoice IDs
        invoice_ids = db.execute_query("SELECT id FROM ecommerce.invoices")['id'].tolist()
        inv_id_map = dict(zip(range(1, len(invoices_df) + 1), invoice_ids))
        inv_items_df['invoice_id'] = inv_items_df['invoice_id'].map(inv_id_map)
        
        db.insert_dataframe(inv_items_df, 'invoice_items')
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("✅ Data Generation Complete!")
        logger.info("="*60)
        
        summary = db.execute_query("""
            SELECT 'categories' as table_name, COUNT(*) as row_count FROM ecommerce.categories
            UNION ALL SELECT 'products', COUNT(*) FROM ecommerce.products
            UNION ALL SELECT 'customers', COUNT(*) FROM ecommerce.customers
            UNION ALL SELECT 'orders', COUNT(*) FROM ecommerce.orders
            UNION ALL SELECT 'order_items', COUNT(*) FROM ecommerce.order_items
            UNION ALL SELECT 'payments', COUNT(*) FROM ecommerce.payments
            UNION ALL SELECT 'invoices', COUNT(*) FROM ecommerce.invoices
            UNION ALL SELECT 'invoice_items', COUNT(*) FROM ecommerce.invoice_items
        """)
        
        print("\n📊 Summary:")
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
