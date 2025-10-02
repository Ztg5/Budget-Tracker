import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import matplotlib.pyplot as plt
import re
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(
    page_title="Personal Budget Tracker", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Database setup
def init_database():
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS net_worth_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Clean description function
def clean_description(description):
    """Clean up transaction descriptions"""
    if pd.isna(description) or description == "":
        return ""
    
    text = str(description).strip()
    
    # Remove common payment processing prefixes
    prefixes_to_remove = [
        r'^TST\*\s*',       # TST* LAKEWOOD TRUCK PA -> LAKEWOOD TRUCK PA
        r'^SQ \*\s*',       # SQ * COFFEE SHOP -> COFFEE SHOP
        r'^PP\*\s*',        # PP* PAYPAL -> PAYPAL
        r'^SP \*\s*',       # SP * SPOTIFY -> SPOTIFY
        r'^PAYPAL \*\s*',   # PAYPAL * AMAZON -> AMAZON
        r'^POS\s*',         # POS WALMART -> WALMART
        r'^DEBIT\s*',       # DEBIT PURCHASE -> PURCHASE
    ]
    
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    text = ' '.join(text.split())
    
    return text

# File upload and parsing
def parse_uploaded_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Please upload a CSV or Excel file"
        
        return df, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def clean_transaction_data(df, date_col, desc_col, amount_col, category_col=None):
    try:
        clean_df = pd.DataFrame()
        
        # Clean dates
        clean_df['date'] = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d')
        
        # Clean descriptions
        clean_df['raw_description'] = df[desc_col].astype(str)
        clean_df['description'] = clean_df['raw_description'].apply(clean_description)
        
        # Clean amounts - handle various formats
        amounts = df[amount_col].astype(str)
        amounts = amounts.str.replace('$', '', regex=False)
        amounts = amounts.str.replace(',', '', regex=False)
        amounts = amounts.str.replace('(', '-', regex=False)
        amounts = amounts.str.replace(')', '', regex=False)
        amounts = amounts.str.strip()
        
        clean_df['amount'] = pd.to_numeric(amounts, errors='coerce').abs()
        
        # Handle categories
        if category_col and category_col in df.columns:
            clean_df['category'] = df[category_col].astype(str).str.strip()
        else:
            clean_df['category'] = 'Uncategorized'
        
        # Remove invalid rows
        clean_df = clean_df.dropna(subset=['date', 'amount'])
        clean_df = clean_df[clean_df['amount'] > 0]
        clean_df = clean_df[clean_df['description'] != '']
        
        # Select only the columns we need
        return clean_df[['date', 'description', 'amount', 'category']], None
        
    except Exception as e:
        return None, f"Error processing data: {str(e)}"

# Database operations
def add_transaction(date, description, amount, category):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (date, description, amount, category)
        VALUES (?, ?, ?, ?)
    ''', (date, description, amount, category))
    conn.commit()
    conn.close()

def update_transaction(transaction_id, date, description, amount, category):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transactions 
        SET date = ?, description = ?, amount = ?, category = ?
        WHERE id = ?
    ''', (date, description, amount, category, transaction_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def add_bulk_transactions(df):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    
    count = 0
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO transactions (date, description, amount, category)
            VALUES (?, ?, ?, ?)
        ''', (row['date'], row['description'], row['amount'], row['category']))
        count += 1
    
    conn.commit()
    conn.close()
    return count

def get_transactions():
    conn = sqlite3.connect('budget_tracker.db')
    df = pd.read_sql_query('SELECT * FROM transactions ORDER BY date DESC', conn)
    conn.close()
    return df

def clear_all_transactions():
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions')
    conn.commit()
    conn.close()

# Net Worth database operations
def add_net_worth_item(item_type, name, category, amount, notes=""):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO net_worth_items (item_type, name, category, amount, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (item_type, name, category, amount, notes))
    conn.commit()
    conn.close()

def update_net_worth_item(item_id, name, category, amount, notes=""):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE net_worth_items 
        SET name = ?, category = ?, amount = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (name, category, amount, notes, item_id))
    conn.commit()
    conn.close()

def delete_net_worth_item(item_id):
    conn = sqlite3.connect('budget_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM net_worth_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

def get_net_worth_items():
    conn = sqlite3.connect('budget_tracker.db')
    df = pd.read_sql_query('SELECT * FROM net_worth_items ORDER BY item_type, category, name', conn)
    conn.close()
    return df

# Initialize database
init_database()

# Custom CSS for clean, modern look
st.markdown("""
    <style>
    /* Hide sidebar by default */
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    /* Main content styling */
    .main {
        padding: 2rem;
    }
    
    /* Navigation styling */
    .nav-container {
        background-color: #f8f9fa;
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
    }
    
    /* Button styling */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Headers */
    h1 {
        font-weight: 700;
        color: #1f1f1f;
        margin-bottom: 1.5rem;
    }
    
    h2, h3 {
        font-weight: 600;
        color: #2f2f2f;
    }
    
    /* Clean dividers */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e0e0e0;
    }
    
    /* Table styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Top Navigation Bar
st.markdown('<div class="nav-container">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Transactions", use_container_width=True, type="primary" if st.session_state.get('page', 'Transactions') == 'Transactions' else "secondary"):
        st.session_state.page = 'Transactions'
        st.rerun()

with col2:
    if st.button("View & Manage", use_container_width=True, type="primary" if st.session_state.get('page', 'Transactions') == 'View' else "secondary"):
        st.session_state.page = 'View'
        st.rerun()

with col3:
    if st.button("Spending Analytics", use_container_width=True, type="primary" if st.session_state.get('page', 'Transactions') == 'Analytics' else "secondary"):
        st.session_state.page = 'Analytics'
        st.rerun()

with col4:
    if st.button("Net Worth", use_container_width=True, type="primary" if st.session_state.get('page', 'Transactions') == 'Net Worth' else "secondary"):
        st.session_state.page = 'Net Worth'
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Initialize page if not set
if 'page' not in st.session_state:
    st.session_state.page = 'Transactions'

page = st.session_state.page

# PAGE 1: Add/Upload Transactions
if page == "Transactions":
    st.header("Add Transactions")
    
    # Tab selection
    tab1, tab2 = st.tabs(["Add Single Transaction", "Upload File"])
    
    # TAB 1: Manual Entry
    with tab1:
        st.subheader("Add New Transaction")
        
        col1, col2 = st.columns(2)
        
        with col1:
            transaction_date = st.date_input("Date", value=date.today(), key="manual_date")
            description = st.text_input("Description", placeholder="e.g., Starbucks Coffee", key="manual_desc")
        
        with col2:
            amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, key="manual_amount")
            
            categories = [
                "Food & Dining", 
                "Transportation", 
                "Shopping", 
                "Bills & Utilities", 
                "Entertainment", 
                "Healthcare", 
                "Income", 
                "Other"
            ]
            
            category = st.selectbox("Category", categories, key="manual_category")
        
        # Show cleaned description preview
        if description:
            cleaned = clean_description(description)
            if cleaned != description:
                st.info(f"💡 Cleaned description: **{cleaned}**")
        
        st.write("")  # spacing
        
        if st.button("Add Transaction", type="primary", use_container_width=True, key="add_single"):
            if description and description.strip() and amount and amount > 0:
                final_description = clean_description(description) or description
                try:
                    add_transaction(str(transaction_date), final_description, amount, category)
                    st.success(f"Added: ${amount:.2f} - {final_description} ({category})")
                    st.info("Go to 'View & Manage' to see it")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.error("Please enter a description and amount greater than $0.00")
    
    # TAB 2: File Upload
    with tab2:
        st.subheader("Upload Credit Card Statement")
        
        st.markdown("""
        **Upload your credit card or bank statement to import transactions**
        
        Supported formats: CSV, Excel (.xlsx, .xls)  
        Automatic description cleaning  
        Handles various amount formats  
        """)
        
        uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx', 'xls'], key="file_upload")
        
        if uploaded_file is not None:
            # Parse the file
            df, error = parse_uploaded_file(uploaded_file)
            
            if error:
                st.error(f"{error}")
            else:
                st.success(f"File loaded! Found {len(df)} rows")
                
                # Preview original data
                st.subheader("File Preview")
                st.dataframe(df.head(), use_container_width=True)
                
                # Column mapping
                st.subheader("Map Your Columns")
                st.markdown("Tell us which columns contain your transaction data:")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    date_col = st.selectbox("Date Column", df.columns, key="upload_date_col")
                with col2:
                    desc_col = st.selectbox("Description Column", df.columns, key="upload_desc_col")
                with col3:
                    amount_col = st.selectbox("Amount Column", df.columns, key="upload_amount_col")
                with col4:
                    category_options = ["None (I'll categorize later)"] + list(df.columns)
                    category_col_selection = st.selectbox("Category Column (Optional)", category_options, key="upload_cat_col")
                    category_col = None if category_col_selection == "None (I'll categorize later)" else category_col_selection
                
                # Preview processed data
                if st.button("Preview Processed Data", key="preview_upload"):
                    clean_df, clean_error = clean_transaction_data(df, date_col, desc_col, amount_col, category_col)
                    
                    if clean_error:
                        st.error(f"{clean_error}")
                    else:
                        st.subheader("Processed Data Preview")
                        
                        # Show before/after for descriptions
                        preview_df = clean_df.head(10).copy()
                        st.dataframe(preview_df, use_container_width=True)
                        
                        # Show cleaning examples
                        st.subheader("Description Cleaning Examples")
                        cleaning_examples = []
                        for i, (_, row) in enumerate(df.head(5).iterrows()):
                            original = str(row[desc_col])
                            cleaned = clean_description(original)
                            if original != cleaned:
                                cleaning_examples.append({"Original": original, "Cleaned": cleaned})
                        
                        if cleaning_examples:
                            st.dataframe(pd.DataFrame(cleaning_examples), use_container_width=True)
                        else:
                            st.info("No descriptions needed cleaning in the preview.")
                        
                        # Statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Valid Transactions", len(clean_df))
                        with col2:
                            st.metric("Total Amount", f"${clean_df['amount'].sum():.2f}")
                        with col3:
                            unique_days = clean_df['date'].nunique()
                            st.metric("Date Range", f"{unique_days} days")
                        
                        # Store in session state for import
                        st.session_state.processed_df = clean_df
                        st.session_state.show_import = True
                
                # Import button (if data is processed)
                if st.session_state.get('show_import', False) and 'processed_df' in st.session_state:
                    st.markdown("---")
                    if st.button("Import All Transactions", type="primary", key="import_upload"):
                        try:
                            clean_df = st.session_state.processed_df
                            imported_count = add_bulk_transactions(clean_df)
                            st.success(f"Successfully imported {imported_count} transactions!")
                            st.info("Go to 'View & Manage' to see your imported data")
                            
                            # Clear session state
                            st.session_state.show_import = False
                            if 'processed_df' in st.session_state:
                                del st.session_state.processed_df
                            st.balloons()
                        except Exception as e:
                            st.error(f"Import failed: {str(e)}")

# PAGE 2: View & Manage Transactions (OPTIMIZED VERSION)
# Replace the entire "elif page == "View":" section with this code

elif page == "View":
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("View & Manage Transactions")
    with col2:
        st.write("")
        if st.button("Reset Data", help="Delete all transactions", type="secondary"):
            st.session_state.show_reset_confirm = True
    
    # Reset confirmation
    if st.session_state.get('show_reset_confirm', False):
        st.warning("⚠️ Delete ALL transactions? This cannot be undone")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Yes, Delete All", type="primary"):
                try:
                    clear_all_transactions()
                    st.session_state.show_reset_confirm = False
                    st.success("All transactions deleted")
                    st.info("Navigate away and back to see the empty list")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        with col2:
            if st.button("Cancel"):
                st.session_state.show_reset_confirm = False
                st.rerun()
    
    df = get_transactions()
    
    if df.empty:
        st.info("No transactions yet. Add some manually or upload a file")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories = ["All"] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox("Filter by Category", categories)
        
        with col2:
            search_term = st.text_input("🔍 Search Description")
        
        with col3:
            df['date'] = pd.to_datetime(df['date'])
            min_date = df['date'].min().date()
            max_date = df['date'].max().date()
            
            date_range = st.date_input(
                "Date Range", 
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        if search_term:
            filtered_df = filtered_df[
                filtered_df['description'].str.contains(search_term, case=False, na=False)
            ]
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df['date'] >= pd.Timestamp(start_date)) &
                (filtered_df['date'] <= pd.Timestamp(end_date))
            ]
        
        # Display results
        st.subheader(f"Showing {len(filtered_df)} transactions")
        
        if not filtered_df.empty:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Transactions", len(filtered_df))
            with col2:
                st.metric("Total Amount", f"${filtered_df['amount'].sum():.2f}")
            with col3:
                st.metric("Average Transaction", f"${filtered_df['amount'].mean():.2f}")
            
            # OPTIMIZED TABLE: Use selection instead of individual buttons
            st.subheader("Transactions")
            st.info("💡 Click a row to select it, then use the action buttons below")
            
            # Prepare display dataframe
            display_df = filtered_df.copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:.2f}")
            display_df = display_df[['id', 'date', 'description', 'amount', 'category']]
            
            # Show interactive table
            event = st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="transaction_table"
            )
            
            # Handle selected transaction
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                selected_id = int(display_df.iloc[selected_idx]['id'])
                selected_row = filtered_df[filtered_df['id'] == selected_id].iloc[0]
                
                st.markdown("---")
                st.info(f"**Selected:** {selected_row['description']} - ${selected_row['amount']:.2f} - {selected_row['category']}")
                
                # Action buttons
                action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
                
                with action_col1:
                    if st.button("✏️ Edit", type="primary", use_container_width=True):
                        st.session_state.editing_id = selected_id
                        st.rerun()
                
                with action_col2:
                    if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                        st.session_state.deleting_id = selected_id
                        st.rerun()
            
            # Edit form
            if 'editing_id' in st.session_state:
                edit_id = st.session_state.editing_id
                edit_row = df[df['id'] == edit_id].iloc[0]
                
                st.markdown("---")
                st.subheader(f"✏️ Editing Transaction ID {edit_id}")
                
                edit_col1, edit_col2, edit_col3, edit_col4 = st.columns(4)
                
                with edit_col1:
                    edit_date = st.date_input(
                        "Date", 
                        value=pd.to_datetime(edit_row['date']).date(),
                        key="edit_date"
                    )
                
                with edit_col2:
                    edit_description = st.text_input(
                        "Description", 
                        value=edit_row['description'],
                        key="edit_desc"
                    )
                
                with edit_col3:
                    edit_amount = st.number_input(
                        "Amount ($)", 
                        value=float(edit_row['amount']),
                        min_value=0.01,
                        step=0.01,
                        key="edit_amount"
                    )
                
                with edit_col4:
                    categories = [
                        "Food & Dining", "Transportation", "Shopping", 
                        "Bills & Utilities", "Entertainment", "Healthcare", 
                        "Income", "Other"
                    ]
                    current_index = categories.index(edit_row['category']) if edit_row['category'] in categories else 0
                    edit_category = st.selectbox(
                        "Category", 
                        categories,
                        index=current_index,
                        key="edit_category"
                    )
                
                button_col1, button_col2, button_col3 = st.columns([1, 1, 2])
                
                with button_col1:
                    if st.button("💾 Save Changes", type="primary", use_container_width=True):
                        try:
                            final_description = clean_description(edit_description) or edit_description
                            update_transaction(edit_id, str(edit_date), final_description, edit_amount, edit_category)
                            st.success(f"✅ Updated transaction ID {edit_id}")
                            del st.session_state.editing_id
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                
                with button_col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        del st.session_state.editing_id
                        st.rerun()
            
            # Delete confirmation
            if 'deleting_id' in st.session_state:
                delete_id = st.session_state.deleting_id
                delete_row = df[df['id'] == delete_id].iloc[0]
                
                st.markdown("---")
                st.warning(f"⚠️ Delete transaction ID {delete_id}?")
                st.write(f"**{delete_row['description']}** - ${delete_row['amount']:.2f} - {delete_row['category']}")
                
                confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 2])
                
                with confirm_col1:
                    if st.button("🗑️ Confirm Delete", type="primary", use_container_width=True):
                        try:
                            delete_transaction(delete_id)
                            st.success(f"✅ Deleted transaction ID {delete_id}")
                            del st.session_state.deleting_id
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                
                with confirm_col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        del st.session_state.deleting_id
                        st.rerun()
        
        else:
            st.info("No transactions match your filters.")
# PAGE 3: Analytics (ENHANCED WITH PLOTLY)
# Replace the entire "elif page == "Analytics":" section with this code

elif page == "Analytics":
    st.header("Spending Analytics")
    
    df = get_transactions()
    
    if df.empty:
        st.info("Add some transactions to see analytics!")
    else:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        df['day_of_week'] = df['date'].dt.day_name()
        df['weekday'] = df['date'].dt.weekday
        
        # Date Range Filter
        st.subheader("Filter by Time Period")
        
        all_months = df['month'].unique()
        all_months = sorted(all_months, reverse=True)
        month_options = ["All Time", "Custom Date Range"] + [str(m) for m in all_months]
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            selected_period = st.selectbox("Select Time Period", month_options, key="time_period_selector")
        
        with col2:
            if selected_period == "Custom Date Range":
                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    min_date = df['date'].min().date()
                    start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=df['date'].max().date(), key="custom_start_date")
                with sub_col2:
                    max_date = df['date'].max().date()
                    end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date, key="custom_end_date")
            else:
                st.write("")
        
        # Apply filtering
        if selected_period == "All Time":
            filtered_df = df.copy()
            period_label = "All Time"
        elif selected_period == "Custom Date Range":
            filtered_df = df[(df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))].copy()
            period_label = f"{start_date} to {end_date}"
        else:
            selected_month_period = pd.Period(selected_period)
            filtered_df = df[df['month'] == selected_month_period].copy()
            period_label = selected_period
        
        if filtered_df.empty:
            st.warning("No transactions in the selected date range.")
        else:
            filtered_df['month'] = filtered_df['date'].dt.to_period('M')
            filtered_df['day_of_week'] = filtered_df['date'].dt.day_name()
            filtered_df['weekday'] = filtered_df['date'].dt.weekday
            
            st.info(f"Viewing: {period_label} ({len(filtered_df)} transactions)")
            
            # Summary cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Spent", f"${filtered_df['amount'].sum():.2f}")
            with col2:
                st.metric("Avg per Transaction", f"${filtered_df['amount'].mean():.2f}")
            with col3:
                st.metric("Total Transactions", len(filtered_df))
            with col4:
                days_range = (filtered_df['date'].max() - filtered_df['date'].min()).days + 1
                st.metric("Daily Average", f"${(filtered_df['amount'].sum() / days_range):.2f}")
            
            # Chart Row 1: Category Pie Chart and Time Trend
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Spending by Category")
                category_spending = filtered_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                
                fig = go.Figure(data=[go.Pie(
                    labels=category_spending.index,
                    values=category_spending.values,
                    hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>%{percent}<extra></extra>',
                    textposition='auto',
                    textinfo='label+percent'
                )])
                
                fig.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Spending Over Time")
                
                if len(filtered_df['month'].unique()) == 1:
                    # Single month - show daily
                    daily_spending = filtered_df.groupby(filtered_df['date'].dt.date)['amount'].sum().reset_index()
                    daily_spending.columns = ['date', 'amount']
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=daily_spending['date'],
                        y=daily_spending['amount'],
                        hovertemplate='<b>%{x}</b><br>$%{y:,.2f}<extra></extra>',
                        marker_color='lightcoral'
                    ))
                    
                    fig.update_layout(
                        title='Daily Spending This Month',
                        xaxis_title='Date',
                        yaxis_title='Amount ($)',
                        height=400,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Multiple months - show monthly with trend line
                    monthly_spending = filtered_df.groupby('month')['amount'].sum().reset_index()
                    monthly_spending['month_str'] = monthly_spending['month'].astype(str)
                    
                    fig = go.Figure()
                    
                    # Bar chart
                    fig.add_trace(go.Bar(
                        x=monthly_spending['month_str'],
                        y=monthly_spending['amount'],
                        name='Monthly Spending',
                        hovertemplate='<b>%{x}</b><br>$%{y:,.2f}<extra></extra>',
                        marker_color='lightgreen'
                    ))
                    
                    # Add trend line if we have enough data points
                    if len(monthly_spending) >= 3:
                        import numpy as np
                        x_numeric = np.arange(len(monthly_spending))
                        z = np.polyfit(x_numeric, monthly_spending['amount'], 1)
                        p = np.poly1d(z)
                        
                        fig.add_trace(go.Scatter(
                            x=monthly_spending['month_str'],
                            y=p(x_numeric),
                            name='Trend',
                            mode='lines',
                            line=dict(color='red', width=2, dash='dash'),
                            hovertemplate='Trend: $%{y:,.2f}<extra></extra>'
                        ))
                    
                    fig.update_layout(
                        title='Monthly Spending Trend',
                        xaxis_title='Month',
                        yaxis_title='Amount ($)',
                        height=400,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            # Chart Row 2: Day of Week and Category Breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Spending by Day of Week")
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                dow_spending = filtered_df.groupby('day_of_week')['amount'].sum().reindex(day_order)
                dow_counts = filtered_df.groupby('day_of_week')['amount'].count().reindex(day_order)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=day_order,
                    y=dow_spending.values,
                    text=[f'{count} txns' for count in dow_counts.values],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Total: $%{y:,.2f}<extra></extra>',
                    marker_color='orange'
                ))
                
                fig.update_layout(
                    title='Total Spending by Day of Week',
                    xaxis_title='Day of Week',
                    yaxis_title='Amount ($)',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Insights
                best_day = dow_spending.idxmax()
                worst_day = dow_spending.idxmin()
                st.write(f"**Highest spending day:** {best_day} (${dow_spending[best_day]:.2f})")
                st.write(f"**Lowest spending day:** {worst_day} (${dow_spending[worst_day]:.2f})")
            
            with col2:
                st.subheader("Category Comparison")
                category_stats = filtered_df.groupby('category').agg({
                    'amount': ['sum', 'count', 'mean']
                }).round(2)
                category_stats.columns = ['Total', 'Count', 'Average']
                category_stats = category_stats.sort_values('Total', ascending=True)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=category_stats.index,
                    x=category_stats['Total'],
                    orientation='h',
                    text=[f"${val:,.2f}" for val in category_stats['Total']],
                    textposition='auto',
                    hovertemplate='<b>%{y}</b><br>Total: $%{x:,.2f}<br>Transactions: %{customdata}<extra></extra>',
                    customdata=category_stats['Count'],
                    marker_color='lightblue'
                ))
                
                fig.update_layout(
                    title='Spending by Category (Horizontal)',
                    xaxis_title='Amount ($)',
                    yaxis_title='Category',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Biggest Purchases Table
            st.subheader("Top 10 Purchases")
            biggest_purchases = filtered_df.nlargest(10, 'amount')[['date', 'description', 'amount', 'category']]
            biggest_purchases['date'] = biggest_purchases['date'].dt.strftime('%Y-%m-%d')
            biggest_purchases['amount'] = biggest_purchases['amount'].apply(lambda x: f"${x:.2f}")
            st.dataframe(biggest_purchases, use_container_width=True, hide_index=True)
            
            top_purchase = filtered_df.loc[filtered_df['amount'].idxmax()]
            st.write(f"**Largest purchase:** ${top_purchase['amount']:.2f} at {top_purchase['description']}")
            
            # Repeat Merchants Analysis
            st.subheader("Merchant Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Most Frequent Merchants")
                merchant_stats = filtered_df.groupby('description').agg({
                    'amount': ['count', 'sum', 'mean']
                }).round(2)
                merchant_stats.columns = ['Visits', 'Total Spent', 'Avg per Visit']
                repeat_merchants = merchant_stats[merchant_stats['Visits'] >= 2]
                repeat_merchants = repeat_merchants.sort_values('Visits', ascending=False)
                
                if not repeat_merchants.empty:
                    st.dataframe(repeat_merchants.head(10), use_container_width=True)
                    most_frequent = repeat_merchants.index[0]
                    visit_count = repeat_merchants.iloc[0]['Visits']
                    total_spent = repeat_merchants.iloc[0]['Total Spent']
                    st.write(f"**Most visited:** {most_frequent} ({int(visit_count)} times, ${total_spent:.2f} total)")
                else:
                    st.info("No repeat merchants found")
            
            with col2:
                st.markdown("#### Highest Spending Merchants")
                merchant_totals = filtered_df.groupby('description')['amount'].agg(['sum', 'count']).round(2)
                merchant_totals.columns = ['Total Spent', 'Transactions']
                merchant_totals = merchant_totals.sort_values('Total Spent', ascending=False)
                
                st.dataframe(merchant_totals.head(10), use_container_width=True)
                biggest_merchant = merchant_totals.index[0]
                merchant_total = merchant_totals.iloc[0]['Total Spent']
                merchant_count = merchant_totals.iloc[0]['Transactions']
                st.write(f"**Biggest merchant:** {biggest_merchant} (${merchant_total:.2f} across {int(merchant_count)} visits)")
            
            # Spending Insights
            st.subheader("Detailed Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Transaction Size Distribution")
                total_spent = filtered_df['amount'].sum()
                total_transactions = len(filtered_df)
                
                small_txn = len(filtered_df[filtered_df['amount'] < 25])
                medium_txn = len(filtered_df[(filtered_df['amount'] >= 25) & (filtered_df['amount'] < 100)])
                large_txn = len(filtered_df[filtered_df['amount'] >= 100])
                
                distribution_data = pd.DataFrame({
                    'Range': ['Under $25', '$25-$100', 'Over $100'],
                    'Count': [small_txn, medium_txn, large_txn],
                    'Percentage': [
                        f"{small_txn/total_transactions*100:.1f}%",
                        f"{medium_txn/total_transactions*100:.1f}%",
                        f"{large_txn/total_transactions*100:.1f}%"
                    ]
                })
                
                st.dataframe(distribution_data, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### Weekend vs Weekday")
                weekend_spending = filtered_df[filtered_df['weekday'].isin([5, 6])]['amount'].sum()
                weekday_spending = total_spent - weekend_spending
                
                weekend_count = len(filtered_df[filtered_df['weekday'].isin([5, 6])])
                weekday_count = total_transactions - weekend_count
                
                comparison_data = pd.DataFrame({
                    'Period': ['Weekdays', 'Weekends'],
                    'Total Spent': [f"${weekday_spending:.2f}", f"${weekend_spending:.2f}"],
                    'Transactions': [weekday_count, weekend_count],
                    'Percentage': [
                        f"{weekday_spending/total_spent*100:.1f}%",
                        f"{weekend_spending/total_spent*100:.1f}%"
                    ]
                })
                
                st.dataframe(comparison_data, use_container_width=True, hide_index=True)

# PAGE 4: Net Worth
elif page == "Net Worth":
    st.header("Net Worth Tracker")
    
    # Asset and Liability Categories
    ASSET_CATEGORIES = [
        "Cash & Bank Accounts",
        "Investment Accounts",
        "Retirement Accounts (401k, IRA)",
        "Real Estate",
        "Vehicles",
        "Business Assets",
        "Crypto & Digital Assets",
        "Other Assets"
    ]
    
    LIABILITY_CATEGORIES = [
        "Credit Card Debt",
        "Student Loans",
        "Mortgage",
        "Auto Loans",
        "Personal Loans",
        "Business Debt",
        "Other Liabilities"
    ]
    
    # Get current net worth items
    nw_df = get_net_worth_items()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Overview", "Add/Edit Items", "Details"])
    
    # TAB 1: Overview
    with tab1:
        if nw_df.empty:
            st.info("No assets or liabilities added yet. Go to 'Add/Edit Items' to get started!")
        else:
            # Calculate totals
            assets_df = nw_df[nw_df['item_type'] == 'Asset']
            liabilities_df = nw_df[nw_df['item_type'] == 'Liability']
            
            total_assets = assets_df['amount'].sum() if not assets_df.empty else 0
            total_liabilities = liabilities_df['amount'].sum() if not liabilities_df.empty else 0
            net_worth = total_assets - total_liabilities
            
            # Summary Cards
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Assets", f"${total_assets:,.2f}")
            with col2:
                st.metric("Total Liabilities", f"${total_liabilities:,.2f}")
            with col3:
                delta_color = "normal" if net_worth >= 0 else "inverse"
                st.metric("Net Worth", f"${net_worth:,.2f}")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Asset Allocation")
                if not assets_df.empty:
                    asset_by_category = assets_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                    
                    # Create interactive Plotly pie chart
                    fig = go.Figure(data=[go.Pie(
                        labels=asset_by_category.index,
                        values=asset_by_category.values,
                        hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>',
                        textposition='inside',
                        textinfo='label+percent',
                        marker=dict(
                            colors=px.colors.qualitative.Set3,
                            line=dict(color='white', width=2)
                        )
                    )])
                    
                    fig.update_layout(
                        title='Asset Allocation by Category',
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Asset breakdown table
                    st.markdown("**Asset Breakdown:**")
                    asset_summary = assets_df.groupby('category')['amount'].agg(['sum', 'count']).round(2)
                    asset_summary.columns = ['Total Value', 'Items']
                    asset_summary['Percentage'] = (asset_summary['Total Value'] / total_assets * 100).round(1)
                    
                    # Format the display
                    display_asset_summary = asset_summary.copy()
                    display_asset_summary['Total Value'] = display_asset_summary['Total Value'].apply(lambda x: f"${x:,.2f}")
                    display_asset_summary['Percentage'] = display_asset_summary['Percentage'].apply(lambda x: f"{x}%")
                    
                    display_asset_summary = display_asset_summary.sort_values('Items', ascending=False)
                    st.dataframe(display_asset_summary, use_container_width=True)
                else:
                    st.info("No assets added yet.")
            
            with col2:
                st.subheader("Liability Breakdown")
                if not liabilities_df.empty:
                    liability_by_category = liabilities_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                    
                    # Create interactive Plotly pie chart
                    fig = go.Figure(data=[go.Pie(
                        labels=liability_by_category.index,
                        values=liability_by_category.values,
                        hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>',
                        textposition='inside',
                        textinfo='label+percent',
                        marker=dict(
                            colors=px.colors.sequential.Reds[2:],
                            line=dict(color='white', width=2)
                        )
                    )])
                    
                    fig.update_layout(
                        title='Liability Breakdown by Category',
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Liability breakdown table
                    st.markdown("**Liability Breakdown:**")
                    liability_summary = liabilities_df.groupby('category')['amount'].agg(['sum', 'count']).round(2)
                    liability_summary.columns = ['Total Amount', 'Items']
                    liability_summary['Percentage'] = (liability_summary['Total Amount'] / total_liabilities * 100).round(1)
                    
                    # Format the display
                    display_liability_summary = liability_summary.copy()
                    display_liability_summary['Total Amount'] = display_liability_summary['Total Amount'].apply(lambda x: f"${x:,.2f}")
                    display_liability_summary['Percentage'] = display_liability_summary['Percentage'].apply(lambda x: f"{x}%")
                    
                    display_liability_summary = display_liability_summary.sort_values('Items', ascending=False)
                    st.dataframe(display_liability_summary, use_container_width=True)
                else:
                    st.info("No liabilities added yet.")
            
            # Net Worth Summary
            st.subheader("Financial Health Metrics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if total_liabilities > 0:
                    debt_to_asset_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
                    st.metric("Debt-to-Asset Ratio", f"{debt_to_asset_ratio:.1f}%")
                else:
                    st.metric("Debt-to-Asset Ratio", "0%")
            
            with col2:
                if total_assets > 0:
                    net_worth_ratio = (net_worth / total_assets * 100)
                    st.metric("Net Worth Ratio", f"{net_worth_ratio:.1f}%")
                else:
                    st.metric("Net Worth Ratio", "N/A")
            
            with col3:
                liquid_categories = ["Cash & Bank Accounts", "Investment Accounts"]
                liquid_assets = assets_df[assets_df['category'].isin(liquid_categories)]['amount'].sum() if not assets_df.empty else 0
                st.metric("Liquid Assets", f"${liquid_assets:,.2f}")
    
    # TAB 2: Add/Edit Items
    with tab2:
        st.subheader("Add New Item")
        
        add_col1, add_col2 = st.columns(2)
        
        with add_col1:
            item_type = st.selectbox("Type", ["Asset", "Liability"], key="add_type")
            item_name = st.text_input("Name", placeholder="e.g., Chase Checking, Primary Residence", key="add_name")
            
            if item_type == "Asset":
                item_category = st.selectbox("Category", ASSET_CATEGORIES, key="add_category")
            else:
                item_category = st.selectbox("Category", LIABILITY_CATEGORIES, key="add_category")
        
        with add_col2:
            item_amount = st.number_input("Amount ($)", min_value=0.01, step=100.00, key="add_amount")
            item_notes = st.text_area("Notes (Optional)", placeholder="Add any notes about this item", key="add_notes", height=100)
        
        if st.button("Add Item", type="primary"):
            if item_name and item_amount > 0:
                try:
                    add_net_worth_item(item_type, item_name, item_category, item_amount, item_notes)
                    st.success(f"Added {item_type}: {item_name} - ${item_amount:,.2f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding item: {str(e)}")
            else:
                st.error("Please enter a name and amount.")
        
        # Display existing items for editing/deleting
        if not nw_df.empty:
            st.markdown("---")
            st.subheader("Manage Existing Items")
            
            # Separate assets and liabilities
            for item_type in ["Asset", "Liability"]:
                st.markdown(f"### {item_type}s")
                type_df = nw_df[nw_df['item_type'] == item_type]
                
                if not type_df.empty:
                    for _, item in type_df.iterrows():
                        edit_col1, edit_col2 = st.columns(2)
                        
                        with edit_col1:
                            edit_name = st.text_input("Name", value=item['name'], key=f"edit_name_{item['id']}")
                            
                            if item_type == "Asset":
                                categories = ASSET_CATEGORIES
                            else:
                                categories = LIABILITY_CATEGORIES
                            
                            current_cat_index = categories.index(item['category']) if item['category'] in categories else 0
                            edit_category = st.selectbox("Category", categories, index=current_cat_index, key=f"edit_cat_{item['id']}")
                        
                        with edit_col2:
                            edit_amount = st.number_input("Amount ($)", value=float(item['amount']), min_value=0.01, step=100.00, key=f"edit_amount_{item['id']}")
                            edit_notes = st.text_area("Notes", value=item['notes'] if pd.notna(item['notes']) else "", key=f"edit_notes_{item['id']}")
                        
                        action_col1, action_col2 = st.columns(2)
                        
                        with action_col1:
                            if st.button("Update", key=f"update_{item['id']}", type="primary"):
                                try:
                                    update_net_worth_item(item['id'], edit_name, edit_category, edit_amount, edit_notes)
                                    st.success(f"Updated {edit_name}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating: {str(e)}")
                        
                        with action_col2:
                            if st.button("Delete", key=f"delete_{item['id']}", type="secondary"):
                                try:
                                    delete_net_worth_item(item['id'])
                                    st.success(f"Deleted {item['name']}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting: {str(e)}")
            else:
                st.info(f"No {item_type.lower()}s added yet")
    
    # TAB 3: Details
    with tab3:
        st.subheader("Detailed Item List")
        
        if nw_df.empty:
            st.info("No items to display.")
        else:
            # Display all items in a table
            display_df = nw_df[['item_type', 'name', 'category', 'amount', 'notes']].copy()
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
            display_df = display_df.rename(columns={
                'item_type': 'Type',
                'name': 'Name',
                'category': 'Category',
                'amount': 'Amount',
                'notes': 'Notes'
            })
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Summary by type
            st.subheader("Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Assets by Category:**")
                assets_df = nw_df[nw_df['item_type'] == 'Asset']
                if not assets_df.empty:
                    asset_summary = assets_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                    for cat, amount in asset_summary.items():
                        st.write(f"• {cat}: ${amount:,.2f}")
                else:
                    st.write("No assets")
            
            with col2:
                st.markdown("**Liabilities by Category:**")
                liabilities_df = nw_df[nw_df['item_type'] == 'Liability']
                if not liabilities_df.empty:
                    liability_summary = liabilities_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                    for cat, amount in liability_summary.items():
                        st.write(f"• {cat}: ${amount:,.2f}")
                else:
                    st.write("No liabilities")

# Footer (removed sidebar info since sidebar is hidden)
