import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# =========================================
# إعداد الصفحة
# =========================================
st.set_page_config(page_title="Restaurant Dashboard", layout="wide")
st.title("🍽️ Restaurant Sales Dashboard")

# =========================================
# تحميل وتنظيف البيانات
# =========================================
@st.cache_data
def load_data():
    df = pd.read_excel("restaurant_sales_dataset.xlsx")

    # حذف القيم الفارغة المهمة
    df = df.dropna(subset=["food_item"])

    # ✅ تصحيح مشكلة inplace
    df["price_per_item"] = df["price_per_item"].fillna(df["price_per_item"].median())
    df["customer_rating"] = df["customer_rating"].fillna(df["customer_rating"].mean())

    # إزالة القيم غير المنطقية
    df = df[df["quantity"] > 0]
    df = df[df["price_per_item"] < 100]

    # حذف التكرار
    df = df.drop_duplicates()

    # تحويل التاريخ
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # إنشاء عمود إجمالي السعر
    df["total_price"] = df["quantity"] * df["price_per_item"]

    return df

df = load_data()

# =========================================
# الفلاتر (Sidebar)
# =========================================
st.sidebar.header("🔎 Filters")

selected_items = st.sidebar.multiselect(
    "Choose Food Items",
    options=df["food_item"].unique(),
    default=df["food_item"].unique()
)

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df["order_date"].min(), df["order_date"].max()]
)

# تطبيق الفلاتر
filtered_df = df[
    (df["food_item"].isin(selected_items)) &
    (df["order_date"] >= pd.to_datetime(date_range[0])) &
    (df["order_date"] <= pd.to_datetime(date_range[1]))
]

# =========================================
# المؤشرات (Metrics)
# =========================================
col1, col2, col3 = st.columns(3)

col1.metric("💰 Total Revenue", f"{filtered_df['total_price'].sum():,.2f}")
col2.metric("🧾 Total Orders", len(filtered_df))
col3.metric("⭐ Avg Rating", f"{filtered_df['customer_rating'].mean():.2f}")

# =========================================
# ترتيب البيانات
# =========================================
st.subheader("📋 Sorted Data")

sort_option = st.selectbox(
    "Sort by",
    ["price_per_item", "quantity", "customer_rating", "order_date", "total_price"]
)

sorted_df = filtered_df.sort_values(by=sort_option, ascending=False)

st.dataframe(sorted_df.head(50), width="stretch")

# =========================================
# تحليل المبيعات
# =========================================
st.subheader("📊 Sales by Food Item")

sales = filtered_df.groupby("food_item")["total_price"].sum().sort_values()

fig, ax = plt.subplots()
sales.plot(kind="bar", ax=ax)
ax.set_title("Total Sales per Item")
ax.set_xlabel("Food Item")
ax.set_ylabel("Total Sales")

st.pyplot(fig)

# =========================================
# أفضل المنتجات
# =========================================
st.subheader("🔥 Top Selling Items")

top_items = filtered_df["food_item"].value_counts().head(5)
st.bar_chart(top_items)

# =========================================
# المبيعات عبر الزمن
# =========================================
st.subheader("📈 Sales Over Time")

time_sales = filtered_df.groupby("order_date")["total_price"].sum()
st.line_chart(time_sales)

# =========================================
# حفظ نسخة نظيفة (اختياري)
# =========================================
if st.button("💾 Save Cleaned Data"):
    df.to_excel("cleaned_restaurant_data.xlsx", index=False)
    st.success("✅ Data saved successfully!")