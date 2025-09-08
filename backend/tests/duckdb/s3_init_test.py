from minio import Minio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

# 创建 MinIO 客户端
minio_client = Minio(
    '172.16.1.16:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False  # 本地测试使用 HTTP
)

# 创建存储桶
bucket_name = 'ecommerce-data-lake'
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

# 生成并上传示例数据
def upload_to_minio():
    # 创建订单数据
    orders_data = {
        'order_id': range(1, 10001),
        'user_id': np.random.randint(1, 1000, 10000),
        'product_id': np.random.randint(1, 500, 10000),
        'order_date': pd.date_range('2023-01-01', '2024-12-31', periods=10000),
        'quantity': np.random.randint(1, 5, 10000),
        'unit_price': np.round(np.random.uniform(10, 200, 10000), 2),
        'category': np.random.choice(['Electronics', 'Clothing', 'Books', 'Home'], 10000)
    }
    
    df_orders = pd.DataFrame(orders_data)
    df_orders['total_amount'] = df_orders['quantity'] * df_orders['unit_price']
    
    # 转换为 Parquet 字节流
    parquet_buffer = io.BytesIO()
    df_orders.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    
    # 上传到 MinIO
    minio_client.put_object(
        bucket_name,
        'orders/orders_2023_2024.parquet',
        parquet_buffer,
        parquet_buffer.getvalue().__len__(),
        content_type='application/octet-stream'
    )
    
    print("数据已上传到 MinIO")

upload_to_minio()