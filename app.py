import streamlit as st
import toml
import json
import os
from datetime import datetime
import pandas as pd
import altair as alt

import os
port = int(os.environ.get('PORT', 8501))




# ---------------------- Persistence ----------------------
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        data = json.load(open(DATA_FILE))
        # Ensure split_ratio exists
        if "split_ratio" not in data:
            data["split_ratio"] = [0.5, 0.5]
        return data
    return {"partner1": "", "partner2": "", "expenses": [], "split_ratio": [0.5, 0.5]}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ---------------------- Config & Theme ----------------------
CONFIG = toml.load("config.toml")
credentials = CONFIG["credentials"]

st.set_page_config(
    page_title="SplitNest",
    page_icon="💞",
    layout="centered",
    initial_sidebar_state="expanded",
)

theme = CONFIG.get("theme", {})
st.markdown(f"""
<style>
  .reportview-container {{background-color: {theme.get("backgroundColor","#f0f2f6")};}}
  .sidebar .sidebar-content {{background-color: {theme.get("secondaryBackgroundColor","#ffffff")};}}
  .sidebar .sidebar-header {{background-color: {theme.get("primaryColor","#4CAF50")}; color: white;}}
  .sidebar .sidebar-item {{color: {theme.get("textColor","#000000")};}}
  body {{color: {theme.get("textColor","#000000")}; font-family: {theme.get("font","sans serif")};}}
  .stButton>button {{background-color: {theme.get("primaryColor","#4CAF50")}; color: white; border-radius:8px;}}
  .stButton>button:hover {{filter: brightness(90%);}}
</style>
""", unsafe_allow_html=True)

# ---------------------- Authentication ----------------------
def authenticate_user():
    st.sidebar.title("💞 SplitNest Login")
    user = st.sidebar.text_input("Username", key="auth_user")
    pwd = st.sidebar.text_input("Password", type="password", key="auth_pwd")
    if user and pwd:
        if user in credentials["usernames"]:
            idx = credentials["usernames"].index(user)
            if pwd == credentials["passwords"][idx]:
                st.sidebar.success(f"Welcome, {user}!")
                return True
            else:
                st.sidebar.error("Invalid password")
        else:
            st.sidebar.error("Unknown username")
    return False

if not authenticate_user():
    st.stop()

# ---------------------- Sidebar: Partners & Ratio ----------------------
st.sidebar.title("💞 SplitNest")

if not data["partner1"] or not data["partner2"]:
    st.sidebar.subheader("👫 Enter Partner Names")
    p1 = st.sidebar.text_input("Partner 1", key="p1")
    p2 = st.sidebar.text_input("Partner 2", key="p2")
    if p1 and p2:
        data["partner1"], data["partner2"] = p1, p2
        save_data(data)
        st.sidebar.success(f"Partners set: {p1} & {p2}")
else:
    st.sidebar.success(f"Partners: {data['partner1']} & {data['partner2']}")

# Global split ratio slider
ratio_pct = st.sidebar.slider(
    f"{data['partner1']}'s share (%)", 
    min_value=0, max_value=100, 
    value=int(data["split_ratio"][0]*100),
    key="global_ratio"
)
data["split_ratio"] = [ratio_pct/100, (100-ratio_pct)/100]
save_data(data)

# Reset data
if st.sidebar.button("🧹 Reset All Data"):
    data = {"partner1":"", "partner2":"", "expenses":[], "split_ratio":[0.5,0.5]}
    save_data(data)
    st.rerun()

# ---------------------- Main Menu ----------------------
menu = st.sidebar.radio("Menu", [
    "➕ Add Expense",
    "💰 View Balance",
    "📊 Visualize Spending",
    "📝 Show All Expenses",
    "📥 Export to CSV"
])

# ---------------------- Add Expense ----------------------
if menu == "➕ Add Expense":
    st.header("➕ Add a New Expense")
    with st.form("expense_form", clear_on_submit=True):
        amt = st.number_input("Amount ($)", min_value=0.01, format="%.2f", key="amt")
        desc = st.text_input("Description", key="desc")
        payer = st.radio("Who paid?", [data["partner1"], data["partner2"]], key="payer")
        cat = st.selectbox("Category", ["Food","Entertainment","Bills","Other"], key="cat")
        rec = st.checkbox("Recurring?", key="rec")
        freq = "None"
        if rec:
            freq = st.selectbox("Frequency", ["Monthly","Weekly","Yearly"], key="freq")

        # Custom split?
        cust = st.checkbox("Use custom split?", key="cust")
        split = {data["partner1"]: amt*data["split_ratio"][0],
                 data["partner2"]: amt*data["split_ratio"][1]}
        if cust:
            method = st.radio("Split by", ["Percentage","Amount"], key="mth")
            if method=="Percentage":
                p1p = st.slider(f"{data['partner1']}%",0,100,int(data["split_ratio"][0]*100), key="p1p")
                split = {data["partner1"]: amt*p1p/100, data["partner2"]: amt*(100-p1p)/100}
            else:
                p1a = st.number_input(f"{data['partner1']} ($)", min_value=0.0, max_value=amt, value=amt*data["split_ratio"][0], key="p1a")
                split = {data["partner1"]: p1a, data["partner2"]: amt-p1a}
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            if amt>0 and desc:
                exp = {
                    "amount": amt, "description": desc, "paid_by": payer,
                    "category": cat, "recurring": rec, "recurrence": freq,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "split": split
                }
                data["expenses"].append(exp)
                save_data(data)
                st.success("Expense added!")
                st.rerun()
            else:
                st.error("Complete all fields.")

# ---------------------- View Balance ----------------------
elif menu == "💰 View Balance":
    st.header("💰 Current Balance")
    p1,p2 = data["partner1"], data["partner2"]
    paid = {p1:0,p2:0}
    owed = {p1:0,p2:0}
    for e in data["expenses"]:
        paid[e["paid_by"]] += e["amount"]
        owed[p1] += e["split"][p1]
        owed[p2] += e["split"][p2]

    st.write(f"{p1} paid: ${paid[p1]:.2f} | owes: ${owed[p1]:.2f}")
    st.write(f"{p2} paid: ${paid[p2]:.2f} | owes: ${owed[p2]:.2f}")

    net1, net2 = paid[p1]-owed[p1], paid[p2]-owed[p2]
    if net1>net2:
        st.success(f"{p2} owes {p1} ${net1-net2:.2f}")
    elif net2>net1:
        st.success(f"{p1} owes {p2} ${net2-net1:.2f}")
    else:
        st.info("All settled up!")

    st.subheader("Upcoming Recurring Expenses")
    recs = [e for e in data["expenses"] if e["recurring"]]
    if recs:
        for e in recs:
            st.write(f"📅 {e['recurrence']} | {e['description']} — ${e['amount']:.2f}")
    else:
        st.info("No recurring items.")

# ---------------------- Visualize Spending ----------------------
elif menu == "📊 Visualize Spending":
    st.header("📊 Spending Overview")
    if data["expenses"]:
        df = pd.DataFrame(data["expenses"])
        df["date"] = pd.to_datetime(df["date"])
        chart = alt.Chart(df).mark_bar().encode(
            x="category:N", y="sum(amount):Q", color="paid_by:N"
        ).properties(width=600, title="By Category & Payer")
        st.altair_chart(chart)
    else:
        st.info("Add some expenses first.")

# ---------------------- Show All Expenses ----------------------
elif menu == "📝 Show All Expenses":
    st.header("📝 Expense History")
    if data["expenses"]:
        for e in reversed(data["expenses"]):
            st.write(f"{e['date']} | {e['paid_by']} paid ${e['amount']:.2f} for {e['description']} split {e['split']}")
    else:
        st.info("No expenses yet.")

# ---------------------- Export to CSV ----------------------
elif menu == "📥 Export to CSV":
    st.header("📥 Download CSV")
    if data["expenses"]:
        df = pd.DataFrame(data["expenses"])
        csv = df.to_csv(index=False)
        st.download_button("Download", csv, "expenses.csv", "text/csv")
    else:
        st.info("No data to export.")
