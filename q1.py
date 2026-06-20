import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================================
# 1. قراءة البيانات
# =========================================
file_path = "restaurant_sales_dataset.xlsx"
df = pd.read_excel(file_path)

print("🔍farst 5 roos")
print(df.head())

print("\n📊 generel data")
print(df.info())

# =========================================
# 2. تنظيف البيانات
# =========================================

print("\n🧹 data cleening")

# إزالة الصفوف التي لا تحتوي على اسم المنتج
df = df.dropna(subset=["food_item"])

# تعويض القيم المفقودة
df["price_per_item"].fillna(df["price_per_item"].median(), inplace=True)
df["customer_rating"].fillna(df["customer_rating"].mean(), inplace=True)

# إزالة الكميات غير المنطقية (<=0)
df = df[df["quantity"] > 0]

# إزالة الأسعار غير المنطقية (Outliers)
df = df[df["price_per_item"] < 100]

# حذف التكرار
df = df.drop_duplicates()

# =========================================
# 3. تحويل البيانات
# =========================================

# تحويل التاريخ
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

# إنشاء عمود إجمالي السعر
df["total_price"] = df["quantity"] * df["price_per_item"]

# =========================================
# 4. التحليل
# =========================================

print("\n📈data analtecs")

# أكثر المنتجات مبيعًا
print("\n🔥 عدد الطلبات لكل منتج:")
print(df["food_item"].value_counts())

# إجمالي المبيعات لكل منتج
sales_per_item = df.groupby("food_item")["total_price"].sum()
print("\n💰 إجمالي المبيعات لكل منتج:")
print(sales_per_item)

# أفضل المنتجات حسب التقييم
top_rated = df.groupby("food_item")["customer_rating"].mean().sort_values(ascending=False)
print("\n⭐ أفضل المنتجات تقييمًا:")
print(top_rated)

# =========================================
# 5. الفرز (Sorting)
# =========================================

print("\n🔃 فرز حسب السعر:")
print(df.sort_values(by="price_per_item", ascending=False).head())

print("\n🔃 فرز حسب التاريخ:")
print(df.sort_values(by="order_date").head())

print("\n🔃 فرز حسب التقييم:")
print(df.sort_values(by="customer_rating", ascending=False).head())

# =========================================
# 6. الرسم البياني
# =========================================

print("\n📊 vusual")

sales_per_item.sort_values().plot(kind="bar")
plt.title("Total Sales per Food Item")
plt.xlabel("Food Item")
plt.ylabel("Total Sales")
plt.tight_layout()
plt.show()

# =========================================
# 7. حفظ البيانات النظيفة
# =========================================

output_file = "cleaned_restaurant_data.xlsx"
df.to_excel(output_file, index=False)

print(f"\n✅ the end {output_file}")