import duckdb
import pandas as pd
from minio import Minio
import io
from datetime import datetime

# 连接到 MinIO
minio_client = Minio(
    '172.16.1.16:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

bucket_name = 'ecommerce-data-lake'
object_name = 'orders/orders_2023_2024.parquet'

# 从 MinIO 读取 Parquet 文件
try:
    response = minio_client.get_object(bucket_name, object_name)
    parquet_data = response.data
    
    # 将数据写入临时文件供 DuckDB 读取
    with open('temp_orders.parquet', 'wb') as f:
        f.write(parquet_data)
    
    print("✅ 成功从 MinIO 下载 Parquet 文件")
    
except Exception as e:
    print(f"❌ 从 MinIO 读取数据失败: {e}")
    exit()

# 创建 DuckDB 连接
conn = duckdb.connect('my_database.db')

# 从 Parquet 文件创建表
conn.execute("CREATE TABLE orders AS SELECT * FROM read_parquet('temp_orders.parquet')")

print("✅ 数据已导入 DuckDB")

# ===========================================
# 数据概览和基础统计
# ===========================================

print("\n" + "="*50)
print("📊 数据概览")
print("="*50)

# 查看数据结构
print("\n🔍 数据结构:")
schema = conn.execute("DESCRIBE orders").fetchall()
for row in schema:
    print(f"  {row[0]}: {row[1]}")

# 基本统计信息
print("\n📈 基本统计:")
total_rows = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
date_range = conn.execute("SELECT MIN(order_date), MAX(order_date) FROM orders").fetchone()
unique_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM orders").fetchone()[0]
unique_products = conn.execute("SELECT COUNT(DISTINCT product_id) FROM orders").fetchone()[0]

print(f"  总订单数: {total_rows:,}")
print(f"  时间范围: {date_range[0]} 到 {date_range[1]}")
print(f"  用户数量: {unique_users:,}")
print(f"  产品数量: {unique_products:,}")

# ===========================================
# 销售分析
# ===========================================

print("\n" + "="*50)
print("💰 销售分析")
print("="*50)

# 总销售额和平均订单价值
sales_summary = conn.execute("""
    SELECT 
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as avg_order_value,
        SUM(quantity) as total_quantity
    FROM orders
""").fetchone()

print(f"\n💵 销售概况:")
print(f"  总销售额: ${sales_summary[0]:,.2f}")
print(f"  平均订单价值: ${sales_summary[1]:.2f}")
print(f"  总销售数量: {sales_summary[2]:,}")

# 按类别分析
print(f"\n🏷️ 按商品类别分析:")
category_analysis = conn.execute("""
    SELECT 
        category,
        COUNT(*) as order_count,
        SUM(total_amount) as revenue,
        AVG(total_amount) as avg_order_value,
        SUM(quantity) as total_quantity
    FROM orders
    GROUP BY category
    ORDER BY revenue DESC
""").fetchall()

for row in category_analysis:
    print(f"  {row[0]:<12} | 订单: {row[1]:>5,} | 销售额: ${row[2]:>10,.2f} | 均值: ${row[3]:>6.2f} | 数量: {row[4]:>6,}")

# ===========================================
# 时间分析
# ===========================================

print("\n" + "="*50)
print("📅 时间趋势分析")
print("="*50)

# 按月销售趋势
print(f"\n📈 月度销售趋势 (前12个月):")
monthly_sales = conn.execute("""
    SELECT 
        EXTRACT(YEAR FROM order_date) as year,
        EXTRACT(MONTH FROM order_date) as month,
        COUNT(*) as order_count,
        SUM(total_amount) as monthly_revenue
    FROM orders
    GROUP BY year, month
    ORDER BY year, month
    LIMIT 12
""").fetchall()

for row in monthly_sales:
    print(f"  {int(row[0])}-{int(row[1]):02d} | 订单: {row[2]:>4,} | 销售额: ${row[3]:>10,.2f}")

# 按星期几分析
print(f"\n📊 按星期几销售分析:")
weekday_sales = conn.execute("""
    SELECT 
        CASE EXTRACT(DOW FROM order_date)
            WHEN 0 THEN '周日'
            WHEN 1 THEN '周一'
            WHEN 2 THEN '周二'
            WHEN 3 THEN '周三'
            WHEN 4 THEN '周四'
            WHEN 5 THEN '周五'
            WHEN 6 THEN '周六'
        END as weekday,
        COUNT(*) as order_count,
        SUM(total_amount) as revenue,
        AVG(total_amount) as avg_order_value
    FROM orders
    GROUP BY EXTRACT(DOW FROM order_date)
    ORDER BY EXTRACT(DOW FROM order_date)
""").fetchall()

for row in weekday_sales:
    print(f"  {row[0]} | 订单: {row[1]:>4,} | 销售额: ${row[2]:>10,.2f} | 均值: ${row[3]:>6.2f}")

# ===========================================
# 用户分析
# ===========================================

print("\n" + "="*50)
print("👥 用户分析")
print("="*50)

# 用户购买频次分布
print(f"\n🛒 用户购买频次分布:")
user_frequency = conn.execute("""
    SELECT 
        order_count,
        COUNT(*) as user_count
    FROM (
        SELECT 
            user_id,
            COUNT(*) as order_count
        FROM orders
        GROUP BY user_id
    ) user_orders
    GROUP BY order_count
    ORDER BY order_count
    LIMIT 10
""").fetchall()

for row in user_frequency:
    print(f"  {row[0]:>2} 次订单: {row[1]:>4,} 个用户")

# Top 10 客户
print(f"\n🏆 Top 10 客户:")
top_customers = conn.execute("""
    SELECT 
        user_id,
        COUNT(*) as order_count,
        SUM(total_amount) as total_spent,
        AVG(total_amount) as avg_order_value
    FROM orders
    GROUP BY user_id
    ORDER BY total_spent DESC
    LIMIT 10
""").fetchall()

for i, row in enumerate(top_customers, 1):
    print(f"  {i:>2}. 用户{row[0]} | 订单: {row[1]:>2} | 总花费: ${row[2]:>8,.2f} | 均值: ${row[3]:>6.2f}")

# ===========================================
# 产品分析
# ===========================================

print("\n" + "="*50)
print("📦 产品分析")
print("="*50)

# 热销产品
print(f"\n🔥 Top 10 热销产品 (按销售额):")
top_products = conn.execute("""
    SELECT 
        product_id,
        COUNT(*) as order_count,
        SUM(quantity) as total_quantity,
        SUM(total_amount) as total_revenue,
        AVG(unit_price) as avg_price
    FROM orders
    GROUP BY product_id
    ORDER BY total_revenue DESC
    LIMIT 10
""").fetchall()

for i, row in enumerate(top_products, 1):
    print(f"  {i:>2}. 产品{row[0]} | 订单: {row[1]:>2} | 数量: {row[2]:>3} | 销售额: ${row[3]:>8,.2f} | 均价: ${row[4]:>6.2f}")

# 价格分析
print(f"\n💲 价格区间分析:")
price_analysis = conn.execute("""
    SELECT 
        CASE 
            WHEN unit_price < 50 THEN '0-50'
            WHEN unit_price < 100 THEN '50-100'
            WHEN unit_price < 150 THEN '100-150'
            ELSE '150+'
        END as price_range,
        COUNT(*) as order_count,
        SUM(total_amount) as revenue
    FROM orders
        GROUP BY 
        CASE 
            WHEN unit_price < 50 THEN '0-50'
            WHEN unit_price < 100 THEN '50-100'
            WHEN unit_price < 150 THEN '100-150'
            ELSE '150+'
        END
    ORDER BY 
        CASE 
            WHEN price_range = '0-50' THEN 1
            WHEN price_range = '50-100' THEN 2
            WHEN price_range = '100-150' THEN 3
            ELSE 4
        END
""").fetchall()

for row in price_analysis:
    print(f"  ${row[0]:<8} | 订单: {row[1]:>5,} | 销售额: ${row[2]:>10,.2f}")

# ===========================================
# 高级分析查询
# ===========================================

print("\n" + "="*50)
print("🔬 高级分析")
print("="*50)

# 客户终身价值分析
print(f"\n💎 客户价值分析:")
clv_analysis = conn.execute("""
    SELECT 
        CASE 
            WHEN total_spent < 100 THEN '低价值 (<$100)'
            WHEN total_spent < 500 THEN '中价值 ($100-500)'
            WHEN total_spent < 1000 THEN '高价值 ($500-1000)'
            ELSE '超高价值 (>$1000)'
        END as customer_segment,
        COUNT(*) as customer_count,
        SUM(total_spent) as segment_revenue,
        AVG(total_spent) as avg_customer_value
    FROM (
        SELECT 
            user_id,
            SUM(total_amount) as total_spent
        FROM orders
        GROUP BY user_id
    ) customer_totals
    GROUP BY 
        CASE 
            WHEN total_spent < 100 THEN '低价值 (<$100)'
            WHEN total_spent < 500 THEN '中价值 ($100-500)'
            WHEN total_spent < 1000 THEN '高价值 ($500-1000)'
            ELSE '超高价值 (>$1000)'
        END
    ORDER BY avg_customer_value
""").fetchall()

for row in clv_analysis:
    print(f"  {row[0]:<18} | 客户: {row[1]:>3,} | 贡献: ${row[2]:>10,.2f} | 均值: ${row[3]:>7,.2f}")

# 销售趋势分析（同比）
print(f"\n📈 年度同比分析:")
yearly_comparison = conn.execute("""
    SELECT 
        EXTRACT(YEAR FROM order_date) as year,
        COUNT(*) as order_count,
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as avg_order_value
    FROM orders
    GROUP BY EXTRACT(YEAR FROM order_date)
    ORDER BY year
""").fetchall()

for row in yearly_comparison:
    print(f"  {int(row[0])} 年 | 订单: {row[1]:>5,} | 销售额: ${row[2]:>12,.2f} | 均值: ${row[3]:>6.2f}")

# 清理临时文件
try:
    os.remove(temp_file_path)
    print(f"🗑️  已清理临时文件: {temp_file_path}")
except:
    pass

print("\n" + "="*50)
print("✅ 分析完成！")
print("="*50)

# 关闭连接
conn.close()