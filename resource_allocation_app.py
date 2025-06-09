import streamlit as st
import pandas as pd
import xlsxwriter
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import calendar
import os

# ─────────────────────────────────────────────────────────────
# Streamlit Page Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MS Perfect Resources", layout="wide")
st.title("MS Perfect Resources")

# Check for AgGrid availability
try:
    from st_aggrid import AgGrid, GridOptionsBuilder
    aggrid_available = True
except ImportError:
    aggrid_available = False
    st.error("Please install streamlit-aggrid with `pip install streamlit-aggrid` to enable inline editing.")
    st.info("Displaying read-only data editor instead.")

# ─────────────────────────────────────────────────────────────
# 1) Default Data Constructors
# ─────────────────────────────────────────────────────────────

def default_engineers():
    # Generate month columns for the next 12 months
    current_date = datetime.now()
    month_columns = {}
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        month_key = f"PTO_{month_date.strftime('%Y_%m')}"
        month_columns[month_key] = [0, 0]  # Default 0 PTO days for each engineer
    
    base_data = {
        "Team": ["Team A", "Team B"],
        "Engineer Name": ["Jane Doe", "John Smith"],
        "Role": ["Backend Dev", "Infra Eng"],
        "Weekly Hours": [40, 40],
        "Annual PTO Days": [0, 0],  # Auto-calculated from monthly values
    }
    
    # Merge base data with month columns
    return pd.DataFrame({**base_data, **month_columns, "Notes": ["", ""]})


def default_future_projects():
    return pd.DataFrame({
        "Project Name": ["Future Project Alpha", "Future Project Beta"],
        "Expected Start Date": ["2025-07-01", "2025-08-15"],
        "Expected End Date": ["2025-09-30", "2025-11-30"],
        "Required Skills": ["Backend, Database", "Frontend, UI/UX"],
        "Estimated Engineer Count": [2, 1],
        "Priority": ["High", "Medium"],
        "Status": ["Planning", "On Hold"],
        "Notes": ["Customer-facing feature", "Internal tooling"]
    })

def default_monthly_assignments():
    """Default monthly assignments structure"""
    current_date = datetime.now()
    months = []
    for i in range(6):  # Default to 6 months ahead
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    return pd.DataFrame({
        "Engineer Name": [],
        "Feature": [],
        "Month": [],
        "Allocation %": [],
        "Notes": []
    })

# ─────────────────────────────────────────────────────────────
# 2) Monthly Assignment Functions
# ─────────────────────────────────────────────────────────────

def generate_monthly_utilization_chart(monthly_df, engineers_df):
    """Generate a simple summary of engineer utilization over time"""
    
    # Get all engineers with valid names, handling different data types
    all_engineers = []
    for name in engineers_df['Engineer Name'].tolist():
        if name is not None and str(name).strip() and str(name) != 'nan':
            all_engineers.append(str(name).strip())
    
    # If no engineers, return empty dataframe with expected columns
    if not all_engineers:
        empty_summary = pd.DataFrame(columns=['Engineer', 'Current Utilization', 'Current Availability', 
                                             'Avg. Monthly Availability', 'Annual PTO Days', 'Status'])
        empty_details = pd.DataFrame(columns=['Engineer', 'Month', 'Features', 'Total Allocation %', 
                                            'Effective Allocation %', 'Available %', 'PTO Days', 'Working Days'])
        return empty_summary, empty_details
    
    # Generate default months if no data - always show next 6 months
    current_date = datetime.now()
    months = []
    for i in range(6):  # Always show 6 months
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Create utilization data
    utilization_data = []
    availability_details = []
    
    for month in months:
        # Filter monthly data for this specific month
        if not monthly_df.empty and 'Month' in monthly_df.columns:
            month_data = monthly_df[monthly_df['Month'] == month]
        else:
            month_data = pd.DataFrame()
        
        for engineer in all_engineers:
            # Ensure string comparison
            engineer_str = str(engineer)
            
            # Initialize allocation tracking
            total_allocation = 0
            features = []
            feature_allocations = {}
            
            # Find assignments for this engineer in this month
            if not month_data.empty:
                engineer_month_data = month_data[month_data['Engineer Name'].astype(str) == engineer_str]
                
                for _, row in engineer_month_data.iterrows():
                    try:
                        # Get allocation value - it should already be numeric
                        allocation = float(row['Allocation %'])
                        if allocation > 0:
                            total_allocation += allocation
                            feature_name = row['Feature']
                            features.append(f"{feature_name} ({allocation}%)")
                            feature_allocations[feature_name] = allocation
                    except Exception as e:
                        # Log error for debugging
                        pass
            
            # Get PTO days for this specific month
            pto_days = 0
            working_days_in_month = 22  # Typical working days in a month
            
            # Find PTO for this engineer and month
            engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == engineer_str]
            
            if not engineer_matches.empty:
                engineer_row = engineer_matches.iloc[0]
                
                # Look for monthly PTO column
                month_pto_key = f"PTO_{month.replace('-', '_')}"
                
                if month_pto_key in engineers_df.columns:
                    pto_days = float(engineer_row.get(month_pto_key, 0))
                else:
                    # Fallback to annual PTO divided by 12 if monthly not available
                    annual_pto = float(engineer_row.get('Annual PTO Days', 0))
                    pto_days = annual_pto / 12
            
            # Calculate working days and ratio
            effective_working_days = max(0, working_days_in_month - pto_days)
            working_days_ratio = effective_working_days / working_days_in_month if working_days_in_month > 0 else 1
            
            # Calculate effective allocation and availability
            effective_allocation = total_allocation * working_days_ratio
            available_capacity = max(0, 100 - effective_allocation)
            
            utilization_data.append({
                'Engineer': engineer,
                'Month': month,
                'Total Allocation': total_allocation,
                'Effective Allocation': effective_allocation,
                'Available Capacity': available_capacity,
                'PTO Impact': (1 - working_days_ratio) * 100,
                'Features': ', '.join(features) if features else 'None',
                'Working Days': effective_working_days,
                'PTO Days': pto_days,
                'Status': 'Over-allocated' if effective_allocation > 100 else 
                         'Fully Occupied' if effective_allocation >= 85 else
                         'Available'
            })
            
            # Store detailed availability data
            availability_details.append({
                'Engineer': engineer,
                'Month': month,
                'Features': feature_allocations,
                'Total Allocation %': total_allocation,
                'Effective Allocation %': round(effective_allocation, 1),
                'Available %': round(available_capacity, 1),
                'PTO Days': round(pto_days, 1),
                'Working Days': round(effective_working_days, 1)
            })
    
    # Create utilization dataframe
    utilization_df = pd.DataFrame(utilization_data)
    availability_df = pd.DataFrame(availability_details)
    
    # Create detailed availability summary
    availability_summary = []
    for engineer in all_engineers:
        engineer_data = utilization_df[utilization_df['Engineer'] == engineer]
        
        if not engineer_data.empty:
            # Current month data (first month)
            current_data = engineer_data.iloc[0]
            
            # Find first month where engineer becomes fully occupied
            fully_occupied = engineer_data[engineer_data['Effective Allocation'] >= 85]
            if not fully_occupied.empty:
                first_full_month = fully_occupied.iloc[0]['Month']
                status = f"Fully occupied from {first_full_month}"
            else:
                status = "Has availability"
            
            # Find over-allocated months
            over_allocated = engineer_data[engineer_data['Effective Allocation'] > 100]
            if not over_allocated.empty:
                over_months = ', '.join(over_allocated['Month'].tolist())
                status += f" | Over-allocated in: {over_months}"
            
            # Average availability across all months
            avg_availability = engineer_data['Available Capacity'].mean()
            
            # Get annual PTO
            annual_pto = 0
            engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == engineer]
            if not engineer_matches.empty:
                annual_pto = engineer_matches['Annual PTO Days'].iloc[0]
            
            availability_summary.append({
                'Engineer': engineer,
                'Current Utilization': f"{current_data['Effective Allocation']:.1f}%",
                'Current Availability': f"{current_data['Available Capacity']:.1f}%",
                'Avg. Monthly Availability': f"{avg_availability:.1f}%",
                'Annual PTO Days': annual_pto,
                'Status': status
            })
        else:
            # This should never happen since we create data for all engineers and months
            # but keeping as safety net
            availability_summary.append({
                'Engineer': engineer,
                'Current Utilization': "0.0%",
                'Current Availability': "100.0%",
                'Avg. Monthly Availability': "100.0%",
                'Annual PTO Days': 0,
                'Status': "Fully available"
            })
    
    summary_df = pd.DataFrame(availability_summary)
    
    # Ensure the dataframes have the expected columns even if empty
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=['Engineer', 'Current Utilization', 'Current Availability', 
                                          'Avg. Monthly Availability', 'Annual PTO Days', 'Status'])
    if availability_df.empty:
        availability_df = pd.DataFrame(columns=['Engineer', 'Month', 'Features', 'Total Allocation %', 
                                              'Effective Allocation %', 'Available %', 'PTO Days', 'Working Days'])
    
    return summary_df, availability_df

def create_monthly_assignment_matrix(engineers_df, features, num_months=6):
    """Create a matrix view for monthly assignments"""
    current_date = datetime.now()
    months = []
    
    for i in range(num_months):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Create a matrix dataframe
    matrix_data = []
    
    # Get valid engineer names
    valid_engineers = []
    for name in engineers_df['Engineer Name']:
        if name is not None and str(name).strip() and str(name) != 'nan':
            valid_engineers.append(str(name))
    
    for engineer in valid_engineers:
        for feature in features:
            row = {'Engineer': engineer, 'Feature': feature}
            for month in months:
                row[month] = 0  # Default allocation
            matrix_data.append(row)
    
    return pd.DataFrame(matrix_data), months

# ─────────────────────────────────────────────────────────────
# 3) Generate Excel File with Charts (Including Monthly Assignments)
# ─────────────────────────────────────────────────────────────

def generate_excel(engineers_df, monthly_df=None):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Write data to separate sheets
        engineers_df.to_excel(writer, sheet_name='Engineer Capacity', index=False)
        
        # Add future projects sheet if it exists in session state
        if 'future_projects_df' in st.session_state and not st.session_state.future_projects_df.empty:
            st.session_state.future_projects_df.to_excel(writer, sheet_name='Future Projects', index=False)
        
        # Add monthly assignments sheet
        if monthly_df is not None and not monthly_df.empty:
            monthly_df.to_excel(writer, sheet_name='Monthly Assignments', index=False)
            
            # Create pivot table for monthly assignments
            pivot_df = monthly_df.pivot_table(
                index=['Engineer Name', 'Feature'],
                columns='Month',
                values='Allocation %',
                fill_value=0
            )
            pivot_df.to_excel(writer, sheet_name='Monthly Assignment Matrix')

        workbook = writer.book
    
    output.seek(0)
    return output

# ─────────────────────────────────────────────────────────────
# 4) Generate Future Projects Timeline Chart
# ─────────────────────────────────────────────────────────────

def generate_future_projects_timeline(future_projects_df):
    """Generate a timeline chart for future projects"""
    
    if future_projects_df.empty:
        return None
    
    # Prepare data for timeline
    timeline_data = []
    
    for _, row in future_projects_df.iterrows():
        try:
            project_name = row.get('Project Name', 'Unnamed Project')
            start_date = pd.to_datetime(row.get('Expected Start Date', '2025-07-01'))
            end_date = pd.to_datetime(row.get('Expected End Date', '2025-08-01'))
            priority = row.get('Priority', 'Medium')
            status = row.get('Status', 'Planning')
            
            timeline_data.append({
                'Project': project_name,
                'Start': start_date,
                'Finish': end_date,
                'Priority': priority,
                'Status': status,
                'Engineers': row.get('Estimated Engineer Count', 1)
            })
        except:
            continue
    
    if not timeline_data:
        return None
    
    timeline_df = pd.DataFrame(timeline_data)
    
    # Create color mapping for priority
    color_map = {'High': '#FF6B6B', 'Medium': '#4ECDC4', 'Low': '#45B7D1', 'Planning': '#96CEB4'}
    timeline_df['Color'] = timeline_df['Priority'].map(color_map).fillna('#95A5A6')
    
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="Finish", 
        y="Project",
        color="Priority",
        color_discrete_map=color_map,
        title="Future Projects Timeline",
        hover_data=['Status', 'Engineers']
    )
    
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_layout(height=400)
    
    return fig

# ─────────────────────────────────────────────────────────────
# 5) Main App Logic
# ─────────────────────────────────────────────────────────────

# Check for AgGrid availability at the start
try:
    from st_aggrid import AgGrid, GridOptionsBuilder
    aggrid_available = True
except ImportError:
    aggrid_available = False

# Initialize all dataframes at the start
engineer_file = "engineers.csv"
future_projects_file = "future_projects.csv"
monthly_assignments_file = "monthly_assignments.csv"

# Initialize Engineers DataFrame
# Always try to load from CSV first to get the latest saved data
try:
    loaded_df = pd.read_csv(engineer_file)
    # Remove old PTO Days column if it exists (legacy cleanup)
    if 'PTO Days' in loaded_df.columns:
        loaded_df = loaded_df.drop(columns=['PTO Days'])
        # Save immediately to persist the removal
        loaded_df.to_csv(engineer_file, index=False)
        st.info("ℹ️ Legacy 'PTO Days' column removed. Using monthly PTO management instead.")
    # Clean up Engineer Name column - convert to string, handle NaN, and strip whitespace
    loaded_df['Engineer Name'] = loaded_df['Engineer Name'].fillna('').astype(str).str.strip()
    # Remove completely empty rows
    loaded_df = loaded_df[loaded_df.astype(str).ne('').any(axis=1)]
    
    # Ensure all required columns exist
    if "Team" not in loaded_df.columns:
        loaded_df["Team"] = ""
    if "Annual PTO Days" not in loaded_df.columns:
        loaded_df["Annual PTO Days"] = 0
    if "Notes" not in loaded_df.columns:
        loaded_df["Notes"] = ""
    if "Role" not in loaded_df.columns:
        loaded_df["Role"] = ""
    if "Weekly Hours" not in loaded_df.columns:
        loaded_df["Weekly Hours"] = 40
    
    # Add monthly PTO columns if they don't exist
    current_date = datetime.now()
    pto_columns_added = False
    
    # First, add columns for the next 12 months from current date
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        month_key = f"PTO_{month_date.strftime('%Y_%m')}"
        if month_key not in loaded_df.columns:
            loaded_df[month_key] = 0
            pto_columns_added = True
    
    # Check for any existing monthly assignments and add PTO columns for those months
    try:
        if os.path.exists(monthly_assignments_file):
            temp_monthly = pd.read_csv(monthly_assignments_file)
            if not temp_monthly.empty and 'Month' in temp_monthly.columns:
                for month in temp_monthly['Month'].unique():
                    month_key = f"PTO_{month.replace('-', '_')}"
                    if month_key not in loaded_df.columns:
                        loaded_df[month_key] = 0
                        pto_columns_added = True
    except:
        pass
    
    # Recalculate Annual PTO Days
    pto_columns = [col for col in loaded_df.columns if col.startswith("PTO_")]
    if pto_columns:
        # Ensure all PTO values are numeric
        for col in pto_columns:
            loaded_df[col] = pd.to_numeric(loaded_df[col], errors='coerce').fillna(0)
        loaded_df['Annual PTO Days'] = loaded_df[pto_columns].sum(axis=1)
    
    # Save if we made changes
    if pto_columns_added:
        loaded_df.to_csv(engineer_file, index=False)
    
    st.session_state.engineers_df = loaded_df
except FileNotFoundError:
    # Only use default if file doesn't exist
    if "engineers_df" not in st.session_state:
        st.session_state.engineers_df = default_engineers()
        st.session_state.engineers_df.to_csv(engineer_file, index=False)
except Exception as e:
    st.error(f"Error loading engineers data: {str(e)}")
    st.info("Using default data instead.")
    if "engineers_df" not in st.session_state:
        st.session_state.engineers_df = default_engineers()

# Initialize Monthly Assignments DataFrame - always reload to get latest
try:
    loaded_monthly_df = pd.read_csv(monthly_assignments_file)
    # Ensure Engineer Name is string type and stripped
    loaded_monthly_df['Engineer Name'] = loaded_monthly_df['Engineer Name'].fillna('').astype(str).str.strip()
    # Ensure Allocation % is numeric
    if 'Allocation %' in loaded_monthly_df.columns:
        loaded_monthly_df['Allocation %'] = pd.to_numeric(loaded_monthly_df['Allocation %'], errors='coerce').fillna(0)
    st.session_state.monthly_assignments_df = loaded_monthly_df
except FileNotFoundError:
    if "monthly_assignments_df" not in st.session_state:
        st.session_state.monthly_assignments_df = default_monthly_assignments()
except Exception as e:
    st.error(f"Error loading monthly assignments: {str(e)}")
    if "monthly_assignments_df" not in st.session_state:
        st.session_state.monthly_assignments_df = default_monthly_assignments()

engineers_df = st.session_state.engineers_df

# Ensure Engineer Name column is string type and stripped
engineers_df['Engineer Name'] = engineers_df['Engineer Name'].fillna('').astype(str).str.strip()

# Remove PTO Days column if it still exists (for already loaded data)
if 'PTO Days' in engineers_df.columns:
    engineers_df = engineers_df.drop(columns=['PTO Days'])
    st.session_state.engineers_df = engineers_df
    # Save immediately to persist the removal
    engineers_df.to_csv(engineer_file, index=False)
    st.info("ℹ️ Legacy 'PTO Days' column has been removed and data saved. Using Annual PTO Days (auto-calculated from monthly values).")

# Ensure required columns exist with proper defaults
if "Team" not in engineers_df.columns:
    engineers_df["Team"] = ""
if "Annual PTO Days" not in engineers_df.columns:
    engineers_df["Annual PTO Days"] = 0
if "Notes" not in engineers_df.columns:
    engineers_df["Notes"] = ""
if "Role" not in engineers_df.columns:
    engineers_df["Role"] = ""
if "Weekly Hours" not in engineers_df.columns:
    engineers_df["Weekly Hours"] = 40

# Add monthly PTO columns if they don't exist
current_date = datetime.now()
pto_columns_added = False

# First, add columns for the next 12 months from current date
for i in range(12):
    month_date = current_date + timedelta(days=30*i)
    month_key = f"PTO_{month_date.strftime('%Y_%m')}"
    if month_key not in engineers_df.columns:
        engineers_df[month_key] = 0
        pto_columns_added = True

# Also check if we have any monthly assignments and add PTO columns for those months
if 'monthly_assignments_df' in st.session_state:
    monthly_df_temp = st.session_state.monthly_assignments_df
    if not monthly_df_temp.empty and 'Month' in monthly_df_temp.columns:
        for month in monthly_df_temp['Month'].unique():
            month_key = f"PTO_{month.replace('-', '_')}"
            if month_key not in engineers_df.columns:
                engineers_df[month_key] = 0
                pto_columns_added = True
                st.info(f"Added PTO column for {month}")

# Recalculate Annual PTO Days to ensure it's correct
pto_columns = [col for col in engineers_df.columns if col.startswith("PTO_")]
if pto_columns:
    # Ensure all PTO values are numeric
    for col in pto_columns:
        engineers_df[col] = pd.to_numeric(engineers_df[col], errors='coerce').fillna(0)
    engineers_df['Annual PTO Days'] = engineers_df[pto_columns].sum(axis=1)

# Update session state after adding columns
st.session_state.engineers_df = engineers_df

# Save if we added new columns or made changes
if pto_columns_added:
    engineers_df.to_csv(engineer_file, index=False)

st.header("👥 Engineer Management")

# Add a reload button in the header
col1, col2, col3 = st.columns([6, 1, 1])
with col1:
    st.write("")  # Empty space
with col2:
    if st.button("🔄 Reload from File", key="reload_engineers"):
        # Clear session state and reload from CSV
        if 'engineers_df' in st.session_state:
            del st.session_state['engineers_df']
        st.rerun()
with col3:
    if st.button("🔧 Fix PTO", key="fix_pto", help="Reset all PTO columns to ensure proper calculation"):
        # Fix PTO columns
        engineers_df = st.session_state.engineers_df
        
        # Check for monthly assignments and add missing PTO columns
        if 'monthly_assignments_df' in st.session_state:
            monthly_df_temp = st.session_state.monthly_assignments_df
            if not monthly_df_temp.empty and 'Month' in monthly_df_temp.columns:
                for month in monthly_df_temp['Month'].unique():
                    month_key = f"PTO_{month.replace('-', '_')}"
                    if month_key not in engineers_df.columns:
                        engineers_df[month_key] = 0
                        st.info(f"Added missing PTO column: {month_key}")
        
        # Ensure all PTO values are numeric
        pto_columns = [col for col in engineers_df.columns if col.startswith("PTO_")]
        for col in pto_columns:
            engineers_df[col] = pd.to_numeric(engineers_df[col], errors='coerce').fillna(0)
        
        # Recalculate annual PTO
        engineers_df['Annual PTO Days'] = engineers_df[pto_columns].sum(axis=1)
        
        # Save changes
        st.session_state.engineers_df = engineers_df
        engineers_df.to_csv(engineer_file, index=False)
        st.success("Fixed PTO data and added missing columns!")
        st.rerun()

# Add tabs for better organization
eng_tab1, eng_tab2 = st.tabs(["Engineer Data", "Monthly PTO Management"])

with eng_tab1:
    # Quick add form
    with st.expander("➕ Quick Add Engineer", expanded=False):
        with st.form("quick_add_engineer"):
            new_name = st.text_input("Engineer Name", value="")
            new_team = st.text_input("Team", value="Unassigned")
            new_role = st.text_input("Role", value="TBD")
            new_hours = st.number_input("Weekly Hours", min_value=0, max_value=168, value=40)
            
            if st.form_submit_button("Add Engineer"):
                if new_name.strip():
                    # Create new row
                    new_row = {
                        "Engineer Name": new_name.strip(),  # Strip whitespace
                        "Team": new_team,
                        "Role": new_role,
                        "Weekly Hours": new_hours,
                        "Annual PTO Days": 0,
                        "Notes": ""
                    }
                    
                    # Add PTO columns
                    for col in engineers_df.columns:
                        if col.startswith("PTO_"):
                            new_row[col] = 0
                    
                    # Add to dataframe
                    new_engineer_df = pd.DataFrame([new_row])
                    engineers_df = pd.concat([engineers_df, new_engineer_df], ignore_index=True)
                    
                    # Update and save
                    st.session_state.engineers_df = engineers_df
                    st.session_state.full_engineers_data = engineers_df.to_dict('records')
                    engineers_df.to_csv(engineer_file, index=False)
                    st.success(f"Added engineer: {new_name}")
                    st.rerun()
                else:
                    st.error("Please enter an engineer name.")

    # Calculate Annual PTO Days as sum of monthly PTO
    pto_columns = [col for col in engineers_df.columns if col.startswith("PTO_")]
    if pto_columns:
        engineers_df['Annual PTO Days'] = engineers_df[pto_columns].sum(axis=1)
    
    # Display only non-PTO columns for basic info (excluding monthly PTO_ columns and old PTO Days)
    display_cols = [col for col in engineers_df.columns if not col.startswith("PTO_") and col != "PTO Days"]
    
    # IMPORTANT: Always get the latest data from session state
    engineers_df = st.session_state.engineers_df.copy()
    
    if aggrid_available:
        # Expander to rename engineer columns
        with st.expander("Rename Engineer Columns", expanded=False):
            eng_renames = {}
            for col in display_cols:
                new_col = st.text_input(f"Rename '{col}' to:", value=col, key=f"rename_eng_{col}")
                eng_renames[col] = new_col
            if st.button("Apply Engineer Renames", key="apply_eng_renames"):
                engineers_df = engineers_df.rename(columns=eng_renames)
                st.session_state.engineers_df = engineers_df
                engineers_df.to_csv(engineer_file, index=False)
                st.success("Engineer column names updated and saved!")

        gb_eng = GridOptionsBuilder.from_dataframe(engineers_df[display_cols])
        gb_eng.configure_default_column(editable=True)
        # Make Annual PTO Days read-only since it's calculated
        gb_eng.configure_column("Annual PTO Days", editable=False, 
                                cellStyle={'backgroundColor': '#f0f0f0'},
                                headerTooltip="Auto-calculated sum of monthly PTO days")
        
        eng_response = AgGrid(
            engineers_df[display_cols],
            gridOptions=gb_eng.build(),
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            fit_columns_on_grid_load=True,
            update_mode='VALUE_CHANGED',
            key='eng_grid'
        )
        
        # Update the dataframe with edited values
        if eng_response and eng_response['data'] is not None:
            edited_df = pd.DataFrame(eng_response['data'])
            
            # Check if data has changed
            data_changed = False
            for col in display_cols:
                if col != 'Annual PTO Days' and col in edited_df.columns:
                    if not engineers_df[col].equals(edited_df[col]):
                        data_changed = True
                        engineers_df[col] = edited_df[col]
            
            if data_changed:
                # Ensure Engineer Name is string type and stripped
                engineers_df['Engineer Name'] = engineers_df['Engineer Name'].fillna('').astype(str).str.strip()
                # Remove any rows with completely empty names before saving
                engineers_df = engineers_df[engineers_df['Engineer Name'] != '']
                st.session_state.engineers_df = engineers_df
                # Auto-save to CSV
                engineers_df.to_csv(engineer_file, index=False)
                st.success("✅ Engineer data auto-saved!")
    else:
        # FIXED: More robust data editor implementation
        st.info("ℹ️ Table editing is enabled. Changes are auto-saved. To add/delete engineers, use the controls above.")
        
        column_config = {
            "Annual PTO Days": st.column_config.NumberColumn(
                "Annual PTO Days",
                help="Auto-calculated sum of monthly PTO days",
                disabled=True,
            ),
            "Engineer Name": st.column_config.TextColumn(
                "Engineer Name",
                help="Enter the engineer's name",
                required=True,
            ),
            "Weekly Hours": st.column_config.NumberColumn(
                "Weekly Hours",
                help="Weekly working hours",
                min_value=0,
                max_value=168,
                step=1,
            )
        }
        
        # Store full dataframe in session state if not already there
        if 'full_engineers_data' not in st.session_state:
            st.session_state.full_engineers_data = engineers_df.to_dict('records')
        
        # Always sync from session state first
        engineers_df = pd.DataFrame(st.session_state.full_engineers_data)
        if engineers_df.empty:
            engineers_df = default_engineers()
            st.session_state.full_engineers_data = engineers_df.to_dict('records')
        
        # Ensure we have the PTO columns
        pto_columns = [col for col in engineers_df.columns if col.startswith("PTO_")]
        display_cols = [col for col in engineers_df.columns if not col.startswith("PTO_") and col != "PTO Days"]
        
        # Create display dataframe
        display_df = engineers_df[display_cols].copy()
        
        # Use data editor - DISABLED dynamic rows due to Streamlit bug
        edited_df = st.data_editor(
            display_df,
            key="engineers_data_editor",
            column_config=column_config,
            num_rows="fixed"  # Changed from "dynamic" to prevent data loss
        )
        
        # Process changes
        if edited_df is not None:
            try:
                # Check if data changed (rows should be same since num_rows="fixed")
                data_changed = not edited_df.equals(display_df)
                
                if data_changed:
                    # Build complete new dataframe
                    new_full_data = []
                    
                    for idx, row in edited_df.iterrows():
                        new_row = row.to_dict()
                        
                        # Add PTO columns from existing data
                        if idx < len(engineers_df):
                            for pto_col in pto_columns:
                                new_row[pto_col] = engineers_df.iloc[idx][pto_col]
                        
                        # Calculate Annual PTO
                        annual_pto = sum(new_row.get(col, 0) for col in pto_columns)
                        new_row['Annual PTO Days'] = annual_pto
                        
                        new_full_data.append(new_row)
                    
                    # Create new dataframe
                    new_engineers_df = pd.DataFrame(new_full_data)
                    
                    # Clean up
                    new_engineers_df['Engineer Name'] = new_engineers_df['Engineer Name'].fillna('').astype(str).str.strip()
                    new_engineers_df = new_engineers_df[new_engineers_df['Engineer Name'] != '']
                    
                    # Ensure column order
                    col_order = ['Team', 'Engineer Name', 'Role', 'Weekly Hours', 'Annual PTO Days'] + pto_columns + ['Notes']
                    existing_cols = [col for col in col_order if col in new_engineers_df.columns]
                    extra_cols = [col for col in new_engineers_df.columns if col not in col_order]
                    new_engineers_df = new_engineers_df[existing_cols + extra_cols]
                    
                    # Update all state
                    st.session_state.engineers_df = new_engineers_df
                    st.session_state.full_engineers_data = new_engineers_df.to_dict('records')
                    
                    # Save to CSV
                    new_engineers_df.to_csv(engineer_file, index=False)
                    st.success("✅ Engineer data auto-saved!")
                    
                    # Update local variable
                    engineers_df = new_engineers_df
                    
            except Exception as e:
                st.error(f"Error updating data: {str(e)}")
                st.info("Your changes were not saved. Please try again or use the '➕ Add Engineer Row' button above.")
                # Restore from session state on error
                if 'full_engineers_data' in st.session_state:
                    engineers_df = pd.DataFrame(st.session_state.full_engineers_data)
    
    # Option to delete engineers
    if len(engineers_df) > 0:
        with st.expander("🗑️ Delete Engineer", expanded=False):
            engineer_to_delete = st.selectbox(
                "Select engineer to delete:",
                options=engineers_df['Engineer Name'].tolist(),
                key="delete_engineer_select"
            )
            if st.button("Delete Selected Engineer", key="delete_engineer_btn"):
                engineers_df = engineers_df[engineers_df['Engineer Name'].str.strip() != engineer_to_delete.strip()]
                st.session_state.engineers_df = engineers_df
                st.session_state.full_engineers_data = engineers_df.to_dict('records')
                engineers_df.to_csv(engineer_file, index=False)
                st.success(f"Deleted engineer: {engineer_to_delete}")
                st.rerun()
    
    st.info("ℹ️ Annual PTO Days is automatically calculated as the sum of all monthly PTO values")

with eng_tab2:
    st.subheader("Monthly PTO Days Management")
    st.info("Set PTO days for each engineer by month. Annual PTO Days will be automatically calculated.")
    
    # Select engineer to manage PTO
    engineer_names = engineers_df['Engineer Name'].tolist()
    # Filter out empty names and handle different data types
    valid_engineer_names = []
    for name in engineer_names:
        if name is not None and str(name).strip() and str(name) != 'nan':
            valid_engineer_names.append(str(name).strip())
    
    if not valid_engineer_names:
        st.warning("No engineers with names found. Please add engineer names in the Engineer Data tab first.")
    else:
        selected_engineer_pto = st.selectbox("Select Engineer for PTO Management:", valid_engineer_names, key="pto_mgmt_engineer")
        
        if selected_engineer_pto:
            # Find the engineer index safely
            engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == str(selected_engineer_pto)]
            
            if not engineer_matches.empty:
                engineer_idx = engineer_matches.index[0]
                
                # Display monthly PTO in columns
                st.write(f"**Monthly PTO for {selected_engineer_pto}:**")
                
                # Create 3 columns for 4 months each
                col_groups = [st.columns(4) for _ in range(3)]
                
                month_updated = False
                current_date = datetime.now()
                for i in range(12):
                    month_date = current_date + timedelta(days=30*i)
                    month_key = f"PTO_{month_date.strftime('%Y_%m')}"
                    month_display = month_date.strftime("%B %Y")
                    
                    col_idx = i % 4
                    row_idx = i // 4
                    
                    with col_groups[row_idx][col_idx]:
                        current_value = engineers_df.loc[engineer_idx, month_key] if month_key in engineers_df.columns else 0
                        new_value = st.number_input(
                            month_display,
                            min_value=0.0,
                            max_value=22.0,
                            value=float(current_value),
                            step=0.5,
                            key=f"pto_{selected_engineer_pto}_{month_key}"
                        )
                        if new_value != current_value:
                            engineers_df.loc[engineer_idx, month_key] = new_value
                            month_updated = True
                
                if month_updated:
                    # Recalculate Annual PTO Days
                    pto_columns = [col for col in engineers_df.columns if col.startswith("PTO_")]
                    engineers_df['Annual PTO Days'] = engineers_df[pto_columns].sum(axis=1)
                    # Ensure names are stripped
                    engineers_df['Engineer Name'] = engineers_df['Engineer Name'].fillna('').astype(str).str.strip()
                    st.session_state.engineers_df = engineers_df
                    # Auto-save PTO changes
                    engineers_df.to_csv(engineer_file, index=False)
                    st.success("✅ PTO data auto-saved!")
                    
                # Show total PTO days
                total_pto = engineers_df.loc[engineer_idx, 'Annual PTO Days']
                st.metric(f"Total Annual PTO Days for {selected_engineer_pto}", f"{total_pto:.1f} days")
                
                # Quick actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Clear All PTO", key=f"clear_pto_{selected_engineer_pto}"):
                        for col in engineers_df.columns:
                            if col.startswith("PTO_"):
                                engineers_df.loc[engineer_idx, col] = 0
                        engineers_df.loc[engineer_idx, 'Annual PTO Days'] = 0
                        st.session_state.engineers_df = engineers_df
                        # Auto-save
                        engineers_df.to_csv(engineer_file, index=False)
                        st.success("Cleared all PTO days and saved!")
                        st.rerun()
                
                with col2:
                    quick_fill = st.number_input("Quick fill value", min_value=0.0, max_value=5.0, value=0.0, step=0.5)
                    if st.button("Apply to All Months", key=f"fill_pto_{selected_engineer_pto}"):
                        for col in engineers_df.columns:
                            if col.startswith("PTO_"):
                                engineers_df.loc[engineer_idx, col] = quick_fill
                        engineers_df['Annual PTO Days'] = engineers_df[pto_columns].sum(axis=1)
                        st.session_state.engineers_df = engineers_df
                        # Auto-save
                        engineers_df.to_csv(engineer_file, index=False)
                        st.success(f"Set {quick_fill} days for all months and saved!")
                        st.rerun()
            else:
                st.error(f"Engineer '{selected_engineer_pto}' not found in the data.")

if st.button("💾 Save Engineer Changes", key="save_eng_btn"):
    # Get the current engineers_df from session state
    engineers_df = st.session_state.engineers_df
    # Ensure Engineer Name is properly formatted before saving - strip whitespace
    engineers_df['Engineer Name'] = engineers_df['Engineer Name'].fillna('').astype(str).str.strip()
    # Remove any rows with completely empty names
    engineers_df = engineers_df[engineers_df['Engineer Name'] != '']
    st.session_state.engineers_df = engineers_df
    engineers_df.to_csv(engineer_file, index=False)
    st.success("✅ Engineer data saved to file!")

# ─────────────────────────────────────────────────────────────
# NEW SECTION: Monthly Feature Assignments
# ─────────────────────────────────────────────────────────────

st.header("📅 Monthly Feature Assignments")

# Get monthly_df from session state - use reference, not copy
monthly_df = st.session_state.monthly_assignments_df

# Ensure proper data types and strip whitespace
if 'Engineer Name' in monthly_df.columns:
    monthly_df['Engineer Name'] = monthly_df['Engineer Name'].fillna('').astype(str).str.strip()
    # Ensure Allocation % is numeric
    if 'Allocation %' in monthly_df.columns:
        monthly_df['Allocation %'] = pd.to_numeric(monthly_df['Allocation %'], errors='coerce').fillna(0)

# UI for adding monthly assignments
col1, col2, col3 = st.columns(3)

with col1:
    engineer_list = engineers_df['Engineer Name'].tolist()
    # Filter out empty names and handle different data types
    valid_engineers = []
    for name in engineer_list:
        if name is not None and str(name).strip() and str(name) != 'nan':
            valid_engineers.append(str(name).strip())
    
    if not valid_engineers:
        st.warning("No engineers with names found. Please add engineer names first.")
        selected_engineer = None
    else:
        selected_engineer = st.selectbox("Select Engineer", options=valid_engineers, key="monthly_engineer")

with col2:
    feature_name = st.text_input("Feature Name", key="monthly_feature")

with col3:
    # Generate month options
    current_date = datetime.now()
    month_options = []
    for i in range(12):  # Next 12 months
        month_date = current_date + timedelta(days=30*i)
        month_options.append(month_date.strftime("%Y-%m"))
    selected_month = st.selectbox("Month", options=month_options, key="monthly_month")

col4, col5 = st.columns(2)
with col4:
    allocation_percent = st.number_input("Allocation %", min_value=0, max_value=100, value=0, step=5, key="monthly_allocation")
with col5:
    notes = st.text_input("Notes", key="monthly_notes")

# Buttons in columns for better layout
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add Monthly Assignment", key="add_monthly_assignment", type="primary"):
        if selected_engineer and feature_name and allocation_percent > 0:
            new_assignment = {
                "Engineer Name": str(selected_engineer).strip(),  # Ensure it's stored as string and stripped
                "Feature": feature_name,
                "Month": selected_month,
                "Allocation %": allocation_percent,  # Store as number, not string
                "Notes": notes
            }
            # Get current dataframe
            current_df = st.session_state.monthly_assignments_df
            # Add new assignment
            new_df = pd.concat([current_df, pd.DataFrame([new_assignment])], ignore_index=True)
            # Ensure all engineer names are stripped
            new_df['Engineer Name'] = new_df['Engineer Name'].fillna('').astype(str).str.strip()
            # Update session state
            st.session_state.monthly_assignments_df = new_df
            # Auto-save
            new_df.to_csv(monthly_assignments_file, index=False)
            st.success(f"Added assignment: {selected_engineer} -> {feature_name} ({allocation_percent}%) for {selected_month}")
            # Clear the monthly_df cache
            if 'monthly_df' in locals():
                del monthly_df
            st.rerun()  # Force refresh to update utilization
        else:
            st.error("Please fill in all required fields")

with col2:
    # Save button right after Add button
    if st.button("💾 Save All Assignments", key="save_monthly_btn"):
        # Get latest data from session state
        save_df = st.session_state.monthly_assignments_df
        # Ensure Engineer Name is string type before saving and strip whitespace
        save_df['Engineer Name'] = save_df['Engineer Name'].fillna('').astype(str).str.strip()
        # Save to CSV
        save_df.to_csv(monthly_assignments_file, index=False)
        st.success("All monthly assignments saved!")
        st.rerun()  # Force refresh to update utilization

# Display selected engineer's assignments dynamically
if selected_engineer:
    st.subheader(f"📋 {selected_engineer}'s Current Assignments")
    
    # Get the latest monthly_df from session state
    current_monthly_df = st.session_state.monthly_assignments_df
    
    # Ensure we're comparing strings properly
    engineer_assignments = current_monthly_df[current_monthly_df['Engineer Name'].astype(str) == str(selected_engineer)].sort_values('Month')
    
    if not engineer_assignments.empty:
        # Create a formatted version for display
        display_df = engineer_assignments.copy()
        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
        
        # Display the dataframe
        st.dataframe(
            display_df[['Feature', 'Month', 'Allocation %', 'Notes']], 
            use_container_width=True,
            hide_index=True
        )
        
        # Quick stats for selected engineer
        col1, col2, col3 = st.columns(3)
        with col1:
            total_assignments = len(engineer_assignments)
            st.metric("Total Assignments", total_assignments)
        with col2:
            unique_features = engineer_assignments['Feature'].nunique()
            st.metric("Unique Features", unique_features)
        with col3:
            # Calculate average allocation
            avg_allocation = engineer_assignments['Allocation %'].mean()
            st.metric("Avg. Allocation", f"{avg_allocation:.1f}%")
    else:
        st.info(f"No assignments found for {selected_engineer}. Add one using the form above!")

# Separator
st.divider()

# Display all assignments grouped by engineer
current_monthly_df = st.session_state.monthly_assignments_df
if not current_monthly_df.empty:
    st.subheader("All Monthly Assignments")
    
    # Add view options
    view_mode = st.radio("View Mode:", ["By Month", "By Engineer", "All Assignments"], horizontal=True)
    
    if view_mode == "By Engineer":
        # Group by engineer for better visualization
        engineers_in_monthly = current_monthly_df['Engineer Name'].unique()
        
        for engineer in engineers_in_monthly:
            if str(engineer) != str(selected_engineer):  # Don't duplicate the selected engineer
                engineer_assignments = current_monthly_df[current_monthly_df['Engineer Name'] == engineer].sort_values('Month')
                
                with st.expander(f"📋 {engineer}'s Assignments ({len(engineer_assignments)} assignments)"):
                    if not engineer_assignments.empty:
                        display_df = engineer_assignments.copy()
                        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                        
                        st.dataframe(
                            display_df[['Feature', 'Month', 'Allocation %', 'Notes']], 
                            use_container_width=True,
                            hide_index=True
                        )
    
    elif view_mode == "By Month":
        # Group by month
        months = sorted(current_monthly_df['Month'].unique())
        
        for month in months:
            month_assignments = current_monthly_df[current_monthly_df['Month'] == month].sort_values('Engineer Name')
            
            with st.expander(f"📅 {month} Assignments ({len(month_assignments)} assignments)"):
                if not month_assignments.empty:
                    display_df = month_assignments.copy()
                    display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                    
                    st.dataframe(
                        display_df[['Engineer Name', 'Feature', 'Allocation %', 'Notes']], 
                        use_container_width=True,
                        hide_index=True
                    )
    
    else:  # All Assignments
        display_df = current_monthly_df.copy().sort_values(['Month', 'Engineer Name'])
        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
        
        st.dataframe(
            display_df[['Engineer Name', 'Feature', 'Month', 'Allocation %', 'Notes']], 
            use_container_width=True,
            hide_index=True
        )
    
    # Option to delete assignments
    if len(current_monthly_df) > 0:
        st.subheader("Delete Assignments")
        # Create a more user-friendly way to select assignments to delete
        delete_options = []
        for idx, row in current_monthly_df.iterrows():
            allocation = row['Allocation %']
            delete_options.append(f"{idx}: {row['Engineer Name']} - {row['Feature']} ({row['Month']}, {allocation}%)")
        
        selected_to_delete = st.selectbox("Select assignment to delete:", options=delete_options, key="delete_monthly_select")
        
        if st.button("🗑️ Delete Selected Assignment", key="delete_monthly_btn"):
            # Extract index from the selected option
            delete_idx = int(selected_to_delete.split(":")[0])
            updated_df = current_monthly_df.drop(index=delete_idx).reset_index(drop=True)
            st.session_state.monthly_assignments_df = updated_df
            # Auto-save
            updated_df.to_csv(monthly_assignments_file, index=False)
            st.success("Assignment deleted and saved!")
            st.rerun()  # Refresh the page to update the display
else:
    st.info("No monthly assignments yet. Use the form above to add assignments.")

# ─────────────────────────────────────────────────────────────
# Monthly Utilization Summary
# ─────────────────────────────────────────────────────────────

st.header("📊 Engineer Utilization Summary")

# Add manual refresh button
col1, col2 = st.columns([10, 2])
with col2:
    if st.button("🔄 Refresh", key="refresh_utilization"):
        # Force reload all data
        try:
            # Reload engineers
            loaded_df = pd.read_csv(engineer_file)
            if 'PTO Days' in loaded_df.columns:
                loaded_df = loaded_df.drop(columns=['PTO Days'])
            loaded_df['Engineer Name'] = loaded_df['Engineer Name'].fillna('').astype(str).str.strip()
            # Remove completely empty rows
            loaded_df = loaded_df[loaded_df.astype(str).ne('').any(axis=1)]
            
            # Ensure PTO columns exist
            current_date = datetime.now()
            for i in range(12):
                month_date = current_date + timedelta(days=30*i)
                month_key = f"PTO_{month_date.strftime('%Y_%m')}"
                if month_key not in loaded_df.columns:
                    loaded_df[month_key] = 0
            
            # Recalculate Annual PTO
            pto_columns = [col for col in loaded_df.columns if col.startswith("PTO_")]
            if pto_columns:
                loaded_df['Annual PTO Days'] = loaded_df[pto_columns].sum(axis=1)
            
            st.session_state.engineers_df = loaded_df
            
            # Reload monthly assignments
            loaded_monthly = pd.read_csv(monthly_assignments_file)
            loaded_monthly['Engineer Name'] = loaded_monthly['Engineer Name'].fillna('').astype(str).str.strip()
            loaded_monthly['Allocation %'] = pd.to_numeric(loaded_monthly['Allocation %'], errors='coerce').fillna(0)
            st.session_state.monthly_assignments_df = loaded_monthly
        except Exception as e:
            st.error(f"Error refreshing: {str(e)}")
        st.rerun()

# Always get the latest monthly assignments from session state
if 'monthly_assignments_df' in st.session_state:
    monthly_df = st.session_state.monthly_assignments_df
else:
    try:
        monthly_df = pd.read_csv(monthly_assignments_file)
        # Ensure proper data types
        monthly_df['Engineer Name'] = monthly_df['Engineer Name'].fillna('').astype(str)
        monthly_df['Allocation %'] = pd.to_numeric(monthly_df['Allocation %'], errors='coerce').fillna(0)
        st.session_state.monthly_assignments_df = monthly_df
    except:
        monthly_df = default_monthly_assignments()
        st.session_state.monthly_assignments_df = monthly_df

try:
    # First check if we have any engineers
    if engineers_df.empty or not any(engineers_df['Engineer Name'].str.strip() != ''):
        st.warning("No engineers found. Please add engineers in the Engineer Management section first.")
    else:
        # Generate utilization summary with current data
        availability_summary, availability_details = generate_monthly_utilization_chart(monthly_df, engineers_df)
        
        if availability_summary is not None and not availability_summary.empty:
            st.subheader("Engineer Availability Overview")
            
            # Color-code the availability summary
            def color_status(val):
                if 'Over-allocated' in str(val):
                    return 'background-color: #FF9999'
                elif 'Fully occupied' in str(val):
                    return 'background-color: #FFEB99'
                else:
                    return 'background-color: #CCFFCC'
            
            def color_availability(val):
                try:
                    # Remove % sign and convert to float
                    val_float = float(str(val).replace('%', ''))
                    if val_float <= 0:
                        return 'background-color: #FF9999'  # Red for no availability
                    elif val_float <= 20:
                        return 'background-color: #FFEB99'  # Yellow for low availability
                    else:
                        return 'background-color: #CCFFCC'  # Green for good availability
                except:
                    return ''
            
            # Check if required columns exist before styling
            if 'Status' in availability_summary.columns:
                styled_summary = availability_summary.style
                if 'Status' in availability_summary.columns:
                    styled_summary = styled_summary.map(color_status, subset=['Status'])
                if 'Current Availability' in availability_summary.columns and 'Avg. Monthly Availability' in availability_summary.columns:
                    styled_summary = styled_summary.map(color_availability, subset=['Current Availability', 'Avg. Monthly Availability'])
                st.dataframe(styled_summary, use_container_width=True)
            else:
                # Display without styling if columns are missing
                st.dataframe(availability_summary, use_container_width=True)
            
            # Show detailed monthly breakdown
            with st.expander("📋 Detailed Monthly Availability Breakdown"):
                # Create pivot table for better visualization
                if not availability_details.empty:
                    try:
                        pivot_data = []
                        for _, row in availability_details.iterrows():
                            pivot_data.append({
                                'Engineer': row['Engineer'],
                                'Month': row['Month'],
                                'Allocation %': row['Effective Allocation %'],
                                'Available %': row['Available %'],
                                'Working Days': row['Working Days']
                            })
                        
                        pivot_df = pd.DataFrame(pivot_data)
                        if not pivot_df.empty and len(pivot_df['Engineer'].unique()) > 0 and len(pivot_df['Month'].unique()) > 0:
                            pivot_table = pivot_df.pivot_table(
                                index='Engineer',
                                columns='Month',
                                values=['Available %', 'Allocation %'],
                                fill_value=100
                            )
                            
                            st.write("**Monthly Availability % by Engineer:**")
                            availability_pivot = pivot_table['Available %']
                            
                            # Apply color coding to the pivot table
                            def color_cell(val):
                                if val <= 0:
                                    return 'background-color: #FF9999; color: white'
                                elif val <= 20:
                                    return 'background-color: #FFEB99'
                                else:
                                    return 'background-color: #CCFFCC'
                            
                            styled_pivot = availability_pivot.style.map(color_cell)
                            st.dataframe(styled_pivot, use_container_width=True)
                            
                            st.write("**Monthly Allocation % by Engineer:**")
                            allocation_pivot = pivot_table['Allocation %']
                            
                            # Apply color coding to allocation
                            def color_allocation(val):
                                if val >= 100:
                                    return 'background-color: #FF9999; color: white'
                                elif val >= 80:
                                    return 'background-color: #FFEB99'
                                else:
                                    return 'background-color: #CCFFCC'
                            
                            styled_allocation = allocation_pivot.style.map(color_allocation)
                            st.dataframe(styled_allocation, use_container_width=True)
                        else:
                            st.info("No data available for pivot table. Add more assignments to see the breakdown.")
                    except Exception as e:
                        st.warning(f"Unable to create pivot table: {str(e)}")
                        st.info("Please check your data and try again.")
                else:
                    st.info("No availability details to show. Add monthly assignments to see the breakdown.")
            
            st.markdown("""
            **Status Indicators:**
            - Engineers are considered fully occupied at 85% allocation
            - Over-allocation occurs above 100%
            
            **Availability Colors:**
            - 🟢 Green: Good availability (>20%)
            - 🟡 Yellow: Low availability (1-20%)
            - 🔴 Red: No availability (0%)
            
            **Note:** PTO is calculated using monthly PTO values from the Engineer Management section
            """)
        else:
            st.info("No utilization data available. Add engineers and monthly assignments to see utilization summary.")
except Exception as e:
    st.error(f"Error generating utilization summary: {str(e)}")
    st.info("Please check your data and try again. If the problem persists, try refreshing the page or clearing your browser cache.")

# ─────────────────────────────────────────────────────────────
# Future Projects Section
# ─────────────────────────────────────────────────────────────

st.header("🚀 Future Projects Planning")

# Initialize Future Projects DataFrame
if "future_projects_df" not in st.session_state:
    try:
        loaded_future_df = pd.read_csv(future_projects_file)
        # Ensure string columns are properly typed
        string_columns = ['Project Name', 'Required Skills', 'Priority', 'Status', 'Notes']
        for col in string_columns:
            if col in loaded_future_df.columns:
                loaded_future_df[col] = loaded_future_df[col].fillna('').astype(str)
        st.session_state.future_projects_df = loaded_future_df
    except FileNotFoundError:
        st.session_state.future_projects_df = default_future_projects()

future_projects_df = st.session_state.future_projects_df

if st.button("➕ Add Future Project Row", key="add_future_row"):
    new_future_row = {col: "" if col not in ["Estimated Engineer Count"] else 1 for col in future_projects_df.columns}
    future_projects_df = pd.concat([future_projects_df, pd.DataFrame([new_future_row])], ignore_index=True)
    st.session_state.future_projects_df = future_projects_df

# Expander to rename future project columns
with st.expander("Rename Future Project Columns", expanded=False):
    future_renames = {}
    for col in future_projects_df.columns:
        new_col = st.text_input(f"Rename '{col}' to:", value=col, key=f"rename_future_{col}")
        future_renames[col] = new_col
    if st.button("Apply Future Project Renames", key="apply_future_renames"):
        future_projects_df = future_projects_df.rename(columns=future_renames)
        st.session_state.future_projects_df = future_projects_df
        # Save the renamed dataframe to CSV to persist changes
        future_projects_df.to_csv(future_projects_file, index=False)
        st.success("Future project column names updated and saved!")

# Expander for modifying future project columns
with st.expander("Modify Future Project Columns", expanded=False):
    future_cols = future_projects_df.columns.tolist()
    future_col_to_delete = st.selectbox("Select column to delete:", options=future_cols, key="delete_future_col")
    if st.button("Delete Column", key="del_future_col_btn"):
        if future_col_to_delete in future_projects_df.columns:
            future_projects_df.drop(columns=[future_col_to_delete], inplace=True)
            st.session_state.future_projects_df = future_projects_df
            # Save changes to CSV to persist
            future_projects_df.to_csv(future_projects_file, index=False)
            st.success(f"Deleted column '{future_col_to_delete}' and saved changes")
    
    new_future_col_name = st.text_input("New column name:", key="new_future_col_name")
    if st.button("Add Column", key="add_future_col_btn"):
        if new_future_col_name and new_future_col_name not in future_projects_df.columns:
            future_projects_df[new_future_col_name] = ""
            st.session_state.future_projects_df = future_projects_df
            # Save changes to CSV to persist
            future_projects_df.to_csv(future_projects_file, index=False)
            st.success(f"Added column '{new_future_col_name}' and saved changes")
        else:
            st.error("Invalid or duplicate column name.")

if aggrid_available:
    # Build grid options for future projects
    gb_future = GridOptionsBuilder.from_dataframe(future_projects_df)
    gb_future.configure_default_column(editable=True)
    future_response = AgGrid(
        future_projects_df,
        gridOptions=gb_future.build(),
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True,
        update_mode='VALUE_CHANGED',
        key='future_grid'
    )
    future_projects_df = pd.DataFrame(future_response['data'])
    st.session_state.future_projects_df = future_projects_df
else:
    # Fallback to regular data editor
    future_projects_df = st.data_editor(future_projects_df, key="future_projects_editor")
    st.session_state.future_projects_df = future_projects_df

if st.button("💾 Save Future Projects Changes", key="save_future_btn"):
    future_projects_df.to_csv(future_projects_file, index=False)
    st.success("Future projects data saved!")

# Future Projects Summary
st.subheader("📊 Future Projects Summary")
col1, col2, col3 = st.columns(3)

with col1:
    total_future_projects = len(future_projects_df)
    st.metric("Total Future Projects", total_future_projects)

with col2:
    try:
        total_engineers_needed = future_projects_df['Estimated Engineer Count'].astype(float).sum()
        st.metric("Total Engineers Needed", int(total_engineers_needed))
    except:
        st.metric("Total Engineers Needed", "N/A")

with col3:
    high_priority_count = len(future_projects_df[future_projects_df.get('Priority', '') == 'High'])
    st.metric("High Priority Projects", high_priority_count)

st.header("📈 Export and Visualization")

# Show Future Projects Timeline
if 'future_projects_df' in st.session_state:
    future_timeline = generate_future_projects_timeline(st.session_state.future_projects_df)
    if future_timeline is not None:
        st.subheader("Future Projects Timeline")
        st.plotly_chart(future_timeline, use_container_width=True)
    else:
        st.info("No future projects data available for timeline. Add projects in the Future Projects Planning section above.")

if st.button("Generate Excel File with All Data", key="export_excel"):
    try:
        excel_file = generate_excel(engineers_df, monthly_df)
        st.download_button(
            label="📥 Download Excel File",
            data=excel_file,
            file_name="Engineer_Resource_Allocation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("Excel file generated successfully with all data!")
    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        st.info("This might be due to invalid data. Please check your data and try again.")
