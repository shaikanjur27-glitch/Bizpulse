import os

import mysql.connector
import pandas as pd
import streamlit as st


# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="BizPulse | Business Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 BizPulse")
st.subheader("Business Intelligence & Decision Hub")
st.caption(
    "Understand customer satisfaction. "
    "Identify problems. Make better business decisions."
)


# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "bizpulse_db")
    )


def load_feedback():
    connection = get_connection()
    try:
        query = """
            SELECT feedback_id, customer_name, product_service,
                   category, rating, comments, feedback_date
            FROM customer_feedback
            ORDER BY feedback_date DESC
        """
        return pd.read_sql(query, connection)
    finally:
        connection.close()


# ---------------- NAVIGATION ----------------
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Feedback", "Business Recommendations"]
)

# Check database connectivity before loading data.
try:
    df = load_feedback()
except mysql.connector.Error as error:
    st.error(
        "Could not connect to MySQL. Check that MySQL Server is "
        "running, the database and table exist, and your credentials "
        "are correct."
    )
    st.code(str(error))
    st.stop()


# ---------------- ADD FEEDBACK ----------------
if page == "Add Feedback":
    st.header("Record Customer Feedback")

    with st.form("feedback_form", clear_on_submit=True):
        customer = st.text_input("Customer name")
        product = st.text_input("Product or service")

        category = st.selectbox(
            "Business category",
            ["Product Quality", "Customer Service",
             "Delivery", "Pricing", "Technology", "Other"]
        )

        rating = st.slider("Customer rating", 1, 5, 3)
        comments = st.text_area("Feedback or complaint")

        submitted = st.form_submit_button("Save Feedback")

    if submitted:
        if not customer.strip() or not product.strip():
            st.warning("Please enter the customer name and product/service.")
        else:
            connection = None
            try:
                connection = get_connection()
                cursor = connection.cursor()

                sql = """
                    INSERT INTO customer_feedback
                    (customer_name, product_service, category,
                     rating, comments)
                    VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    sql,
                    (
                        customer.strip(),
                        product.strip(),
                        category,
                        rating,
                        comments.strip()
                    )
                )

                connection.commit()
                st.success("Feedback saved successfully!")
                st.rerun()

            except mysql.connector.Error as error:
                st.error(f"Unable to save feedback: {error}")

            finally:
                if connection is not None and connection.is_connected():
                    connection.close()


# ---------------- DASHBOARD ----------------
elif page == "Dashboard":
    st.header("Customer Satisfaction Dashboard")

    if df.empty:
        st.info("No feedback available yet. Add your first record.")
    else:
        average_rating = df["rating"].mean()
        satisfaction_pct = (
            df["rating"].ge(4).mean() * 100
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Responses", len(df))
        col2.metric("Average Rating", f"{average_rating:.2f}/5")
        col3.metric("Positive Ratings", f"{satisfaction_pct:.1f}%")
        col4.metric(
            "Low Ratings",
            int(df["rating"].le(2).sum())
        )

        st.divider()

        left, right = st.columns(2)

        with left:
            st.subheader("Average Rating by Category")
            category_ratings = (
                df.groupby("category")["rating"]
                .mean()
                .sort_values()
            )
            st.bar_chart(category_ratings)

        with right:
            st.subheader("Feedback by Product or Service")
            product_counts = df["product_service"].value_counts()
            st.bar_chart(product_counts)

        st.subheader("Customer Feedback Records")
        search = st.text_input("Search by customer or product")

        filtered = df.copy()

        if search.strip():
            mask = (
                filtered["customer_name"].str.contains(
                    search, case=False, na=False
                )
                | filtered["product_service"].str.contains(
                    search, case=False, na=False
                )
            )
            filtered = filtered[mask]

        st.dataframe(filtered, use_container_width=True)


# ---------------- BUSINESS RECOMMENDATIONS ----------------
else:
    st.header("Business Recommendations")

    if df.empty:
        st.info("Add customer feedback to generate recommendations.")
    else:
        category_ratings = df.groupby("category")["rating"].mean()
        weak_categories = category_ratings[category_ratings < 3]

        low_ratings = df[df["rating"] <= 2]
        positive_ratings = df[df["rating"] >= 4]

        st.metric(
            "Positive Feedback Share",
            f"{len(positive_ratings) / len(df) * 100:.1f}%"
        )

        st.subheader("Recommended Actions")

        if not weak_categories.empty:
            for category_name, average in weak_categories.items():
                st.warning(
                    f"Review {category_name}: average rating is "
                    f"{average:.2f}/5. Investigate the underlying issues."
                )
        else:
            st.success(
                "No category has an average rating below 3. "
                "Continue monitoring customer feedback."
            )

        if not low_ratings.empty:
            st.write(
                f"**Follow-up:** Investigate {len(low_ratings)} "
                "feedback record(s) rated 1 or 2."
            )

            st.dataframe(
                low_ratings[
                    ["customer_name", "product_service",
                     "category", "rating", "comments"]
                ],
                use_container_width=True
            )

        st.caption(
            "Recommendations are based on recorded ratings, "
            "not on a predictive or AI model."
        )

