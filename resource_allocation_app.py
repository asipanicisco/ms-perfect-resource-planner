import streamlit as st
import pandas as pd
import xlsxwriter
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar

# ─────────────────────────────────────────────────────────────
# Streamlit Page Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MS Perfect Resources", layout="wide")
st.title("MS Perfect Resources")

# ─────────────────────────────────────────────────────────────
# 1) Default Data Constructors
# ─────────────────────────────────────────────────────────────

def default_engineers():
    return pd.DataFrame({
        "Team": ["Team A", "Team B"],
        "PTO Days": [0, 0],
        "Engineer Name": ["Jane Doe", "John Smith"],
        "Role": ["Backend Dev", "Infra Eng"],
        "Weekly Hours": [40, 40],
        "Notes": ["", ""]
    })


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
    """Generate a chart showing engineer utilization and availability over time"""
    
    # Get all engineers
    all_engineers = engineers_df['Engineer Name'].tolist()
    
    # Generate default months if no data
    if monthly_df.empty:
        current_date = datetime.now()
        months = []
        for i in range(6):  # Default to 6 months
            month_date = current_date + timedelta(days=30*i)
            months.append(month_date.strftime("%Y-%m"))
    else:
        months = sorted(monthly_df['Month'].unique())
    
    # Create utilization data
    utilization_data = []
    availability_details = []
    
    for month in months:
        month_data = monthly_df[monthly_df['Month'] == month] if not monthly_df.empty else pd.DataFrame()
        
        for engineer in all_engineers:
            engineer_month_data = month_data[month_data['Engineer Name'] == engineer] if not month_data.empty else pd.DataFrame()
            
            # Calculate total allocation for this engineer in this month
            total_allocation = 0
            features = []
            feature_allocations = {}
            
            for _, row in engineer_month_data.iterrows():
                try:
                    allocation = float(str(row['Allocation %']).replace('%', '').strip())
                    total_allocation += allocation
                    feature_name = row['Feature']
                    features.append(f"{feature_name} ({allocation}%)")
                    feature_allocations[feature_name] = allocation
                except:
                    pass
            
            # Get PTO days for this engineer
            pto_days = 0
            working_days_in_month = 22  # Typical working days in a month
            if engineer in engineers_df['Engineer Name'].values:
                pto_row = engineers_df[engineers_df['Engineer Name'] == engineer]
                if not pto_row.empty:
                    pto_days = float(pto_row.iloc[0].get('PTO Days', 0))
            
            # Calculate PTO days for this specific month (distribute annual PTO across months)
            monthly_pto_days = pto_days / 12  # Assume PTO is annual, distribute evenly
            effective_working_days = max(0, working_days_in_month - monthly_pto_days)
            working_days_ratio = effective_working_days / working_days_in_month
            
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
                'Status': 'Over-allocated' if effective_allocation > 100 else 
                         'Fully Occupied' if effective_allocation >= 95 else
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
                'PTO Days (Monthly)': round(monthly_pto_days, 1),
                'Working Days': round(effective_working_days, 1)
            })
    
    utilization_df = pd.DataFrame(utilization_data)
    availability_df = pd.DataFrame(availability_details)
    
    # Create the visualization with subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Engineer Utilization Over Time', 'Engineer Availability Over Time'),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    # Plot 1: Utilization (Stacked Area Chart)
    for engineer in all_engineers:
        engineer_data = utilization_df[utilization_df['Engineer'] == engineer]
        
        # Add utilization trace
        fig.add_trace(go.Scatter(
            x=engineer_data['Month'],
            y=engineer_data['Effective Allocation'],
            mode='lines+markers',
            name=f"{engineer} - Utilized",
            line=dict(width=2),
            marker=dict(size=8),
            legendgroup=engineer,
            showlegend=True,
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Month: %{x}<br>' +
                          'Utilization: %{y:.1f}%<br>' +
                          'Features: %{text}<br>' +
                          'Working Days: %{customdata:.1f}<br>' +
                          '<extra></extra>',
            text=engineer_data['Features'],
            customdata=engineer_data['Working Days']
        ), row=1, col=1)
    
    # Plot 2: Availability (Bar Chart)
    # Group by month for better visualization
    for i, month in enumerate(months):
        month_data = utilization_df[utilization_df['Month'] == month]
        
        fig.add_trace(go.Bar(
            x=month_data['Engineer'],
            y=month_data['Available Capacity'],
            name=month,
            text=[f"{val:.0f}%" for val in month_data['Available Capacity']],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>' +
                          'Month: ' + month + '<br>' +
                          'Available: %{y:.1f}%<br>' +
                          'Allocated: %{customdata[0]:.1f}%<br>' +
                          'PTO Impact: %{customdata[1]:.1f}%<br>' +
                          '<extra></extra>',
            customdata=month_data[['Effective Allocation', 'PTO Impact']].values,
            marker_color=px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
        ), row=2, col=1)
    
    # Add reference lines to utilization plot
    fig.add_hline(y=100, line_dash="dash", line_color="red", 
                  annotation_text="Over-allocated", row=1, col=1)
    fig.add_hline(y=95, line_dash="dash", line_color="orange", 
                  annotation_text="Fully Occupied", row=1, col=1)
    
    # Update layout
    fig.update_xaxes(title_text="Month", row=1, col=1)
    fig.update_xaxes(title_text="Engineer", row=2, col=1)
    fig.update_yaxes(title_text="Utilization (%)", row=1, col=1, range=[0, max(120, utilization_df['Effective Allocation'].max() + 10)])
    fig.update_yaxes(title_text="Available Capacity (%)", row=2, col=1, range=[0, 105])
    
    fig.update_layout(
        height=800,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.45,
            xanchor="left",
            x=1.02
        ),
        title_text="Engineer Resource Utilization and Availability Analysis"
    )
    
    # Create detailed availability summary
    availability_summary = []
    for engineer in all_engineers:
        engineer_data = utilization_df[utilization_df['Engineer'] == engineer]
        
        if not engineer_data.empty:
            # Current month data
            current_data = engineer_data.iloc[0]
            
            # Find first month where engineer becomes fully occupied
            fully_occupied = engineer_data[engineer_data['Effective Allocation'] >= 95]
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
            
            availability_summary.append({
                'Engineer': engineer,
                'Current Utilization': f"{current_data['Effective Allocation']:.1f}%",
                'Current Availability': f"{current_data['Available Capacity']:.1f}%",
                'Avg. Monthly Availability': f"{avg_availability:.1f}%",
                'Annual PTO Days': engineers_df[engineers_df['Engineer Name'] == engineer]['PTO Days'].iloc[0] if engineer in engineers_df['Engineer Name'].values else 0,
                'Status': status
            })
        else:
            availability_summary.append({
                'Engineer': engineer,
                'Current Utilization': "0%",
                'Current Availability': "100%",
                'Avg. Monthly Availability': "100%",
                'Annual PTO Days': engineers_df[engineers_df['Engineer Name'] == engineer]['PTO Days'].iloc[0] if engineer in engineers_df['Engineer Name'].values else 0,
                'Status': "Fully available"
            })
    
    summary_df = pd.DataFrame(availability_summary)
    
    return fig, summary_df, availability_df

def create_monthly_assignment_matrix(engineers_df, features, num_months=6):
    """Create a matrix view for monthly assignments"""
    current_date = datetime.now()
    months = []
    
    for i in range(num_months):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Create a matrix dataframe
    matrix_data = []
    
    for engineer in engineers_df['Engineer Name']:
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

engineer_file = "engineers.csv"
future_projects_file = "future_projects.csv"
monthly_assignments_file = "monthly_assignments.csv"

# Initialize Engineers DataFrame
if "engineers_df" not in st.session_state:
    try:
        st.session_state.engineers_df = pd.read_csv(engineer_file)
    except FileNotFoundError:
        st.session_state.engineers_df = default_engineers()

engineers_df = st.session_state.engineers_df

# Ensure required columns exist
if "Team" not in engineers_df.columns:
    engineers_df["Team"] = ""
if "PTO Days" not in engineers_df.columns:
    engineers_df["PTO Days"] = 0

st.header("👥 Engineer Management")

if st.button("➕ Add Engineer Row", key="add_eng_row"):
    new_row = {col: "" if col != "PTO Days" else 0 for col in engineers_df.columns}
    engineers_df = pd.concat([engineers_df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.engineers_df = engineers_df

# Check for AgGrid
try:
    from st_aggrid import AgGrid, GridOptionsBuilder
    aggrid_available = True
except ImportError:
    aggrid_available = False
    st.error("Please install streamlit-aggrid with `pip install streamlit-aggrid` to enable inline editing.")
    st.info("Displaying read-only data editor instead.")

if aggrid_available:
    # Expander to rename engineer columns
    with st.expander("Rename Engineer Columns", expanded=False):
        eng_renames = {}
        for col in engineers_df.columns:
            new_col = st.text_input(f"Rename '{col}' to:", value=col, key=f"rename_eng_{col}")
            eng_renames[col] = new_col
        if st.button("Apply Engineer Renames", key="apply_eng_renames"):
            engineers_df = engineers_df.rename(columns=eng_renames)
            st.session_state.engineers_df = engineers_df
            # Save the renamed dataframe to CSV to persist changes
            engineers_df.to_csv(engineer_file, index=False)
            st.success("Engineer column names updated and saved!")

    gb_eng = GridOptionsBuilder.from_dataframe(engineers_df)
    gb_eng.configure_default_column(editable=True)
    eng_response = AgGrid(
        engineers_df,
        gridOptions=gb_eng.build(),
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True,
        update_mode='VALUE_CHANGED',
        key='eng_grid'
    )
    engineers_df = pd.DataFrame(eng_response['data'])
    st.session_state.engineers_df = engineers_df
else:
    # Fallback to regular data editor
    engineers_df = st.data_editor(engineers_df, key="engineers_editor")
    st.session_state.engineers_df = engineers_df

if st.button("💾 Save Engineer Changes", key="save_eng_btn"):
    engineers_df.to_csv(engineer_file, index=False)
    st.success("Engineer data saved!")

# ─────────────────────────────────────────────────────────────
# NEW SECTION: Monthly Feature Assignments
# ─────────────────────────────────────────────────────────────

st.header("📅 Monthly Feature Assignments")

# Initialize Monthly Assignments DataFrame
if "monthly_assignments_df" not in st.session_state:
    try:
        st.session_state.monthly_assignments_df = pd.read_csv(monthly_assignments_file)
    except FileNotFoundError:
        st.session_state.monthly_assignments_df = default_monthly_assignments()

monthly_df = st.session_state.monthly_assignments_df

# UI for adding monthly assignments
col1, col2, col3 = st.columns(3)

with col1:
    engineer_list = engineers_df['Engineer Name'].tolist()
    selected_engineer = st.selectbox("Select Engineer", options=engineer_list, key="monthly_engineer")

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
    allocation_percent = st.number_input("Allocation %", min_value=0, max_value=100, value=0, key="monthly_allocation")
with col5:
    notes = st.text_input("Notes", key="monthly_notes")

if st.button("➕ Add Monthly Assignment", key="add_monthly_assignment"):
    if selected_engineer and feature_name and allocation_percent > 0:
        new_assignment = {
            "Engineer Name": selected_engineer,
            "Feature": feature_name,
            "Month": selected_month,
            "Allocation %": allocation_percent,
            "Notes": notes
        }
        monthly_df = pd.concat([monthly_df, pd.DataFrame([new_assignment])], ignore_index=True)
        st.session_state.monthly_assignments_df = monthly_df
        st.success(f"Added assignment: {selected_engineer} -> {feature_name} ({allocation_percent}%) for {selected_month}")
    else:
        st.error("Please fill in all required fields")

# Display current monthly assignments
if not monthly_df.empty:
    st.subheader("Current Monthly Assignments")
    
    # Group by engineer for better visualization
    engineers_in_monthly = monthly_df['Engineer Name'].unique()
    
    for engineer in engineers_in_monthly:
        with st.expander(f"📋 {engineer}'s Assignments"):
            engineer_assignments = monthly_df[monthly_df['Engineer Name'] == engineer].sort_values('Month')
            
            if aggrid_available:
                gb_monthly = GridOptionsBuilder.from_dataframe(engineer_assignments)
                gb_monthly.configure_default_column(editable=True)
                monthly_response = AgGrid(
                    engineer_assignments,
                    gridOptions=gb_monthly.build(),
                    allow_unsafe_jscode=True,
                    enable_enterprise_modules=False,
                    fit_columns_on_grid_load=True,
                    update_mode='VALUE_CHANGED',
                    key=f'monthly_grid_{engineer}'
                )
                # Update the main dataframe with changes
                updated_data = pd.DataFrame(monthly_response['data'])
                monthly_df.loc[monthly_df['Engineer Name'] == engineer] = updated_data
            else:
                st.dataframe(engineer_assignments)
    
    # Option to delete assignments
    st.subheader("Delete Assignments")
    if len(monthly_df) > 0:
        # Create a more user-friendly way to select assignments to delete
        delete_options = []
        for idx, row in monthly_df.iterrows():
            delete_options.append(f"{idx}: {row['Engineer Name']} - {row['Feature']} ({row['Month']}, {row['Allocation %']}%)")
        
        selected_to_delete = st.selectbox("Select assignment to delete:", options=delete_options, key="delete_monthly_select")
        
        if st.button("🗑️ Delete Selected Assignment", key="delete_monthly_btn"):
            # Extract index from the selected option
            delete_idx = int(selected_to_delete.split(":")[0])
            monthly_df = monthly_df.drop(index=delete_idx).reset_index(drop=True)
            st.session_state.monthly_assignments_df = monthly_df
            st.success("Assignment deleted!")
            st.rerun()  # Refresh the page to update the display

if st.button("💾 Save Monthly Assignments", key="save_monthly_btn"):
    monthly_df.to_csv(monthly_assignments_file, index=False)
    st.success("Monthly assignments saved!")

# ─────────────────────────────────────────────────────────────
# Monthly Utilization Timeline Chart
# ─────────────────────────────────────────────────────────────

st.header("📊 Engineer Utilization Timeline")

# First check if we have any engineers
if engineers_df.empty:
    st.warning("No engineers found. Please add engineers in the Engineer Management section first.")
elif not monthly_df.empty or st.checkbox("Show availability for all engineers (including those without assignments)", value=True):
    # Generate chart even if monthly_df is empty to show all engineers' availability
    utilization_chart, availability_summary, availability_details = generate_monthly_utilization_chart(monthly_df, engineers_df)
    
    if utilization_chart is not None:
        st.plotly_chart(utilization_chart, use_container_width=True)
        
        st.subheader("Engineer Availability Summary")
        
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
        
        styled_summary = availability_summary.style.map(color_status, subset=['Status']).map(
            color_availability, subset=['Current Availability', 'Avg. Monthly Availability'])
        st.dataframe(styled_summary, use_container_width=True)
        
        # Show detailed monthly breakdown
        with st.expander("📋 Detailed Monthly Availability Breakdown"):
            # Create pivot table for better visualization
            if not availability_details.empty:
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
        
        st.markdown("""
        **Timeline Legend:**
        - 🔴 Red line: Over-allocation threshold (100%)
        - 🟠 Orange line: Fully occupied threshold (95%)
        - Engineers are considered fully occupied at 95% to allow for buffer time
        
        **Availability Colors:**
        - 🟢 Green: Good availability (>20%)
        - 🟡 Yellow: Low availability (1-20%)
        - 🔴 Red: No availability (0%)
        
        **Note:** PTO is distributed evenly across months (Annual PTO ÷ 12)
        """)
else:
    st.info("No engineers found. Please add engineers in the Engineer Management section to see the utilization timeline.")

# ─────────────────────────────────────────────────────────────
# Future Projects Section
# ─────────────────────────────────────────────────────────────

st.header("🚀 Future Projects Planning")

# Initialize Future Projects DataFrame
if "future_projects_df" not in st.session_state:
    try:
        future_projects_df = pd.read_csv(future_projects_file)
    except FileNotFoundError:
        future_projects_df = default_future_projects()
    st.session_state.future_projects_df = future_projects_df

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
