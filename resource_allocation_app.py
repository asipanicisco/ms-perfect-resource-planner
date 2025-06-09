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
# Helper Functions for Quarterly Calculations
# Fiscal Year Convention: FY starts in August
# Example: August 2025 = Q1 FY26, July 2025 = Q4 FY25
# ─────────────────────────────────────────────────────────────

def get_fiscal_quarter(month_str):
    """Get fiscal quarter based on August start (Q1: Aug-Oct, Q2: Nov-Jan, Q3: Feb-Apr, Q4: May-Jul)
    
    Fiscal year starts in August, so:
    - August 2025 through July 2026 = FY26
    - August 2024 through July 2025 = FY25
    
    Examples:
    - July 2025 = Q4 FY25
    - August 2025 = Q1 FY26
    - January 2026 = Q2 FY26
    """
    try:
        month_date = datetime.strptime(month_str, "%Y-%m")
        month = month_date.month
        year = month_date.year
        
        # Fiscal year starts in August
        # If month is August or later, fiscal year is current year + 1
        # If month is before August, fiscal year is current year
        if month >= 8:  # August through December
            fiscal_year = year + 1
        else:  # January through July
            fiscal_year = year
        
        if month in [8, 9, 10]:  # Aug-Oct
            return f"Q1 FY{fiscal_year}"
        elif month in [11, 12]:  # Nov-Dec
            return f"Q2 FY{fiscal_year}"
        elif month in [1]:  # Jan
            return f"Q2 FY{fiscal_year}"
        elif month in [2, 3, 4]:  # Feb-Apr
            return f"Q3 FY{fiscal_year}"
        else:  # May-Jul (months 5, 6, 7)
            return f"Q4 FY{fiscal_year}"
    except:
        return "Unknown"

def get_quarter_months(quarter_str):
    """Get the months that belong to a specific quarter
    
    Since FY starts in August:
    - Q1 FY26 = Aug-Oct 2025
    - Q2 FY26 = Nov 2025 - Jan 2026
    - Q3 FY26 = Feb-Apr 2026
    - Q4 FY26 = May-Jul 2026
    """
    # Extract year from quarter string (e.g., "Q1 FY2026" -> 2026)
    try:
        parts = quarter_str.split()
        quarter_num = parts[0]
        fiscal_year = int(parts[1].replace("FY", ""))
        
        # Fiscal year 2026 starts in August 2025
        # So we need to subtract 1 from fiscal year to get the calendar year for Q1-Q2 start
        if quarter_num == "Q1":
            # Q1 is Aug-Oct of the previous calendar year
            return [f"{fiscal_year-1}-08", f"{fiscal_year-1}-09", f"{fiscal_year-1}-10"]
        elif quarter_num == "Q2":
            # Q2 is Nov-Dec of previous calendar year and Jan of fiscal year
            return [f"{fiscal_year-1}-11", f"{fiscal_year-1}-12", f"{fiscal_year}-01"]
        elif quarter_num == "Q3":
            # Q3 is Feb-Apr of the fiscal year
            return [f"{fiscal_year}-02", f"{fiscal_year}-03", f"{fiscal_year}-04"]
        else:  # Q4
            # Q4 is May-Jul of the fiscal year
            return [f"{fiscal_year}-05", f"{fiscal_year}-06", f"{fiscal_year}-07"]
    except:
        return []

def generate_team_utilization_summary(monthly_df, engineers_df):
    """Generate overall team utilization summary by quarter"""
    
    # Get all engineers with valid names
    all_engineers = []
    for name in engineers_df['Engineer Name'].tolist():
        if name is not None and str(name).strip() and str(name) != 'nan':
            all_engineers.append(str(name).strip())
    
    if not all_engineers or monthly_df.empty:
        return None
    
    # Generate months for next 12 months
    current_date = datetime.now()
    months = []
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Calculate quarterly team metrics
    quarterly_metrics = []
    
    # Group months by quarter
    quarters_dict = {}
    for month in months:
        quarter = get_fiscal_quarter(month)
        if quarter not in quarters_dict:
            quarters_dict[quarter] = []
        quarters_dict[quarter].append(month)
    
    for quarter, quarter_months in quarters_dict.items():
        total_capacity = len(all_engineers) * 100  # 100% per engineer
        total_allocated = 0
        total_effective_allocated = 0
        engineers_over_allocated = 0
        engineers_fully_occupied = 0
        engineers_available = 0
        
        # Calculate metrics for each engineer
        for engineer in all_engineers:
            engineer_allocation = 0
            engineer_effective_allocation = 0
            months_with_assignments = 0
            
            for month in quarter_months:
                # Get allocations
                month_allocation = 0
                has_assignment = False
                
                if 'Month' in monthly_df.columns:
                    month_data = monthly_df[(monthly_df['Month'] == month) & 
                                          (monthly_df['Engineer Name'].astype(str) == str(engineer))]
                    if not month_data.empty:
                        month_allocation = month_data['Allocation %'].sum()
                        has_assignment = True
                        months_with_assignments += 1
                
                # Get PTO adjustment
                working_days_ratio = 1
                engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == str(engineer)]
                
                if not engineer_matches.empty:
                    engineer_row = engineer_matches.iloc[0]
                    month_pto_key = f"PTO_{month.replace('-', '_')}"
                    if month_pto_key in engineers_df.columns:
                        pto_days = float(engineer_row.get(month_pto_key, 0))
                        working_days_in_month = 22
                        effective_working_days = max(0, working_days_in_month - pto_days)
                        working_days_ratio = effective_working_days / working_days_in_month if working_days_in_month > 0 else 1
                
                if has_assignment:
                    engineer_allocation += month_allocation
                    engineer_effective_allocation += month_allocation * working_days_ratio
            
            # Calculate quarterly metrics based on months with assignments
            if months_with_assignments > 0:
                avg_allocation = engineer_allocation / months_with_assignments
                avg_effective_allocation = engineer_effective_allocation / months_with_assignments
            else:
                avg_allocation = 0
                avg_effective_allocation = 0
            
            total_allocated += avg_allocation
            total_effective_allocated += avg_effective_allocation
            
            # Categorize engineer
            if avg_effective_allocation > 100:
                engineers_over_allocated += 1
            elif avg_effective_allocation >= 85:
                engineers_fully_occupied += 1
            else:
                engineers_available += 1
        
        quarterly_metrics.append({
            'Quarter': quarter,
            'Team Size': len(all_engineers),
            'Avg Team Utilization %': round(total_allocated / len(all_engineers), 1),
            'Avg Effective Utilization %': round(total_effective_allocated / len(all_engineers), 1),
            'Available Engineers': engineers_available,
            'Fully Occupied Engineers': engineers_fully_occupied,
            'Over-allocated Engineers': engineers_over_allocated
        })
    
    if not quarterly_metrics:
        return None
    
    metrics_df = pd.DataFrame(quarterly_metrics)
    
    # Sort quarters chronologically
    sorted_quarters = sort_quarters_chronologically(metrics_df['Quarter'].tolist())
    metrics_df['Quarter'] = pd.Categorical(metrics_df['Quarter'], categories=sorted_quarters, ordered=True)
    metrics_df = metrics_df.sort_values('Quarter')
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add utilization bars
    fig.add_trace(go.Bar(
        name='Average Team Utilization',
        x=metrics_df['Quarter'],
        y=metrics_df['Avg Team Utilization %'],
        yaxis='y',
        text=metrics_df['Avg Team Utilization %'].apply(lambda x: f"{x}%"),
        textposition='inside',
        marker_color='lightblue',
        hovertemplate='%{x}<br>Team Utilization: %{y}%<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Effective Utilization (PTO Adjusted)',
        x=metrics_df['Quarter'],
        y=metrics_df['Avg Effective Utilization %'],
        yaxis='y',
        text=metrics_df['Avg Effective Utilization %'].apply(lambda x: f"{x}%"),
        textposition='inside',
        marker_color='darkblue',
        hovertemplate='%{x}<br>Effective Utilization: %{y}%<extra></extra>'
    ))
    
    # Add engineer count lines
    fig.add_trace(go.Scatter(
        name='Available Engineers',
        x=metrics_df['Quarter'],
        y=metrics_df['Available Engineers'],
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='green', width=3),
        marker=dict(size=10),
        hovertemplate='%{x}<br>Available: %{y} engineers<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        name='Fully Occupied',
        x=metrics_df['Quarter'],
        y=metrics_df['Fully Occupied Engineers'],
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='orange', width=3),
        marker=dict(size=10),
        hovertemplate='%{x}<br>Fully Occupied: %{y} engineers<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        name='Over-allocated',
        x=metrics_df['Quarter'],
        y=metrics_df['Over-allocated Engineers'],
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='red', width=3),
        marker=dict(size=10),
        hovertemplate='%{x}<br>Over-allocated: %{y} engineers<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title=f"Team Utilization Summary ({len(all_engineers)} Engineers)",
        xaxis_title="Fiscal Quarter",
        yaxis=dict(
            title="Utilization %",
            side="left"
        ),
        yaxis2=dict(
            title="Number of Engineers",
            anchor="x",
            overlaying="y",
            side="right"
        ),
        barmode='group',
        height=500,
        showlegend=True
    )
    
    return fig

def sort_quarters_chronologically(quarters):
    """Sort quarters in chronological order (by fiscal year then quarter number)"""
    return sorted(quarters, key=lambda x: (int(x.split()[1].replace('FY', '')), int(x.split()[0][1])))

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
    """Default monthly assignments structure with Program and Priority fields"""
    current_date = datetime.now()
    months = []
    for i in range(6):  # Default to 6 months ahead
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    return pd.DataFrame({
        "Engineer Name": [],
        "Program": [],
        "Feature": [],
        "Priority": [],  # New field
        "Month": [],
        "Allocation %": [],
        "Notes": []
    })

# ─────────────────────────────────────────────────────────────
# 2) Monthly Assignment Functions
# ─────────────────────────────────────────────────────────────

def generate_monthly_utilization_chart(monthly_df, engineers_df):
    """Generate a quarterly summary of engineer utilization over time"""
    
    # Get all engineers with valid names, handling different data types
    all_engineers = []
    for name in engineers_df['Engineer Name'].tolist():
        if name is not None and str(name).strip() and str(name) != 'nan':
            all_engineers.append(str(name).strip())
    
    # If no engineers, return empty dataframe with expected columns
    if not all_engineers:
        empty_summary = pd.DataFrame(columns=['Engineer', 'Current Quarter Utilization', 'Current Quarter Availability', 
                                             'Avg. Quarterly Availability', 'Annual PTO Days', 'Status'])
        empty_details = pd.DataFrame(columns=['Engineer', 'Quarter', 'Features', 'Total Allocation %', 
                                            'Effective Allocation %', 'Available %', 'PTO Days', 'Working Days'])
        return empty_summary, empty_details
    
    # Generate default months if no data - always show next 12 months (4 quarters)
    current_date = datetime.now()
    months = []
    for i in range(12):  # Show 12 months = 4 quarters
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Group months by quarter
    quarters_dict = {}
    for month in months:
        quarter = get_fiscal_quarter(month)
        if quarter not in quarters_dict:
            quarters_dict[quarter] = []
        quarters_dict[quarter].append(month)
    
    # Sort quarters chronologically
    sorted_quarters = sort_quarters_chronologically(list(quarters_dict.keys()))
    
    # Create utilization data by quarter
    utilization_data = []
    availability_details = []
    
    for quarter in sorted_quarters:
        quarter_months = quarters_dict[quarter]
        
        for engineer in all_engineers:
            # Ensure string comparison
            engineer_str = str(engineer)
            
            # Initialize quarterly tracking
            total_allocation = 0
            total_effective_allocation = 0
            total_pto_days = 0
            total_working_days = 0
            all_features = {}
            months_with_data = 0
            
            # Calculate for each month in the quarter
            for month in quarter_months:
                # Filter monthly data for this specific month
                if not monthly_df.empty and 'Month' in monthly_df.columns:
                    month_data = monthly_df[monthly_df['Month'] == month]
                else:
                    month_data = pd.DataFrame()
                
                # Get PTO days for this specific month
                pto_days = 0
                working_days_in_month = 22  # Typical working days in a month
                
                engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == engineer_str]
                
                if not engineer_matches.empty:
                    engineer_row = engineer_matches.iloc[0]
                    month_pto_key = f"PTO_{month.replace('-', '_')}"
                    
                    if month_pto_key in engineers_df.columns:
                        pto_days = float(engineer_row.get(month_pto_key, 0))
                
                # Calculate working days
                effective_working_days = max(0, working_days_in_month - pto_days)
                
                # Calculate allocation for this month
                month_total_allocation = 0
                if not month_data.empty:
                    engineer_month_data = month_data[month_data['Engineer Name'].astype(str) == engineer_str]
                    
                    for _, row in engineer_month_data.iterrows():
                        try:
                            allocation = float(row['Allocation %'])
                            if allocation > 0:
                                month_total_allocation += allocation
                                feature_name = row['Feature']
                                if feature_name in all_features:
                                    all_features[feature_name] += allocation
                                else:
                                    all_features[feature_name] = allocation
                        except:
                            pass
                
                # Add to total only if there's an assignment
                if month_total_allocation > 0:
                    total_allocation += month_total_allocation
                    months_with_data += 1
                
                total_pto_days += pto_days
                total_working_days += effective_working_days
            
            # Calculate quarterly averages
            if months_with_data > 0:
                # Average only over months with assignments
                avg_allocation = total_allocation / months_with_data
                avg_working_days = total_working_days / len(quarter_months)
                avg_pto_days = total_pto_days / len(quarter_months)
                avg_working_days_ratio = avg_working_days / 22 if avg_working_days > 0 else 1
                
                # Calculate effective allocation and availability
                effective_allocation = avg_allocation / avg_working_days_ratio if avg_working_days_ratio > 0 else avg_allocation
                available_capacity = max(0, 100 - effective_allocation)
                
                # Format features for display (showing average per month with assignment)
                features_list = [f"{feat} ({all_features[feat]/months_with_data:.1f}%)" for feat in sorted(all_features.keys())]
            else:
                # No assignments in quarter
                avg_allocation = 0
                avg_working_days = total_working_days / len(quarter_months) if len(quarter_months) > 0 else 22
                avg_pto_days = total_pto_days / len(quarter_months) if len(quarter_months) > 0 else 0
                avg_working_days_ratio = avg_working_days / 22 if avg_working_days > 0 else 1
                effective_allocation = 0
                available_capacity = 100
                features_list = []
            
            utilization_data.append({
                'Engineer': engineer,
                'Quarter': quarter,
                'Total Allocation': avg_allocation if months_with_data > 0 else 0,
                'Effective Allocation': effective_allocation,
                'Available Capacity': available_capacity,
                'PTO Impact': (1 - avg_working_days_ratio) * 100 if months_with_data > 0 else 0,
                'Features': ', '.join(features_list) if features_list else 'None',
                'Working Days': total_working_days,
                'PTO Days': total_pto_days,
                'Status': 'Over-allocated' if effective_allocation > 100 else 
                         'Fully Occupied' if effective_allocation >= 85 else
                         'Available',
                'Months with Assignments': months_with_data
            })
            
            # Store detailed availability data
            availability_details.append({
                'Engineer': engineer,
                'Quarter': quarter,
                'Features': all_features,
                'Total Allocation %': round(avg_allocation if months_with_data > 0 else 0, 1),
                'Effective Allocation %': round(effective_allocation, 1),
                'Available %': round(available_capacity, 1),
                'PTO Days': round(total_pto_days / len(quarter_months), 1),  # Average PTO days per month
                'Working Days': round(total_working_days / len(quarter_months), 1),  # Average working days per month
                'Months with Data': months_with_data
            })
    
    # Create utilization dataframe
    utilization_df = pd.DataFrame(utilization_data)
    availability_df = pd.DataFrame(availability_details)
    
    # Create detailed availability summary
    availability_summary = []
    for engineer in all_engineers:
        engineer_data = utilization_df[utilization_df['Engineer'] == engineer]
        
        if not engineer_data.empty:
            # Current quarter data (first quarter)
            current_data = engineer_data.iloc[0]
            
            # Find first quarter where engineer becomes fully occupied
            fully_occupied = engineer_data[engineer_data['Effective Allocation'] >= 85]
            if not fully_occupied.empty:
                first_full_quarter = fully_occupied.iloc[0]['Quarter']
                status = f"Fully occupied from {first_full_quarter}"
            else:
                status = "Has availability"
            
            # Find over-allocated quarters
            over_allocated = engineer_data[engineer_data['Effective Allocation'] > 100]
            if not over_allocated.empty:
                over_quarters = ', '.join(over_allocated['Quarter'].tolist())
                status += f" | Over-allocated in: {over_quarters}"
            
            # Average availability across all quarters
            avg_availability = engineer_data['Available Capacity'].mean()
            
            # Get annual PTO
            annual_pto = 0
            engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == engineer]
            if not engineer_matches.empty:
                annual_pto = engineer_matches['Annual PTO Days'].iloc[0]
            
            availability_summary.append({
                'Engineer': engineer,
                'Current Quarter Utilization': f"{current_data['Effective Allocation']:.1f}%",
                'Current Quarter Availability': f"{current_data['Available Capacity']:.1f}%",
                'Avg. Quarterly Availability': f"{avg_availability:.1f}%",
                'Annual PTO Days': annual_pto,
                'Status': status
            })
        else:
            availability_summary.append({
                'Engineer': engineer,
                'Current Quarter Utilization': "0.0%",
                'Current Quarter Availability': "100.0%",
                'Avg. Quarterly Availability': "100.0%",
                'Annual PTO Days': 0,
                'Status': "Fully available"
            })
    
    summary_df = pd.DataFrame(availability_summary)
    
    # Ensure the dataframes have the expected columns even if empty
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=['Engineer', 'Current Quarter Utilization', 'Current Quarter Availability', 
                                          'Avg. Quarterly Availability', 'Annual PTO Days', 'Status'])
    if availability_df.empty:
        availability_df = pd.DataFrame(columns=['Engineer', 'Quarter', 'Features', 'Total Allocation %', 
                                              'Effective Allocation %', 'Available %', 'PTO Days', 'Working Days'])
    
    return summary_df, availability_df

def generate_quarterly_availability_chart(monthly_df, engineers_df):
    """Generate quarterly bandwidth availability chart per engineer"""
    
    # Get all valid engineers
    all_engineers = []
    for name in engineers_df['Engineer Name'].tolist():
        if name is not None and str(name).strip() and str(name) != 'nan':
            all_engineers.append(str(name).strip())
    
    if not all_engineers:
        return None
    
    # Generate months for next 12 months
    current_date = datetime.now()
    months = []
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Calculate quarterly data
    quarterly_data = []
    
    # Group months by quarter
    quarters = {}
    for month in months:
        quarter = get_fiscal_quarter(month)
        if quarter not in quarters:
            quarters[quarter] = []
        quarters[quarter].append(month)
    
    for quarter, quarter_months in quarters.items():
        for engineer in all_engineers:
            total_available = 0
            total_allocated = 0
            total_effective_allocated = 0
            total_working_days = 0
            total_pto_days = 0
            months_with_assignments = 0
            
            for month in quarter_months:
                # Get allocations for this month
                month_allocation = 0
                has_assignment = False
                
                if not monthly_df.empty and 'Month' in monthly_df.columns:
                    month_data = monthly_df[(monthly_df['Month'] == month) & 
                                          (monthly_df['Engineer Name'].astype(str) == str(engineer))]
                    if not month_data.empty:
                        month_allocation = month_data['Allocation %'].sum()
                        has_assignment = True
                        months_with_assignments += 1
                
                # Get PTO days
                pto_days = 0
                working_days_in_month = 22
                
                engineer_matches = engineers_df[engineers_df['Engineer Name'].astype(str) == str(engineer)]
                if not engineer_matches.empty:
                    engineer_row = engineer_matches.iloc[0]
                    month_pto_key = f"PTO_{month.replace('-', '_')}"
                    if month_pto_key in engineers_df.columns:
                        pto_days = float(engineer_row.get(month_pto_key, 0))
                
                effective_working_days = max(0, working_days_in_month - pto_days)
                working_days_ratio = effective_working_days / working_days_in_month if working_days_in_month > 0 else 1
                
                # Calculate for the month
                effective_allocation = month_allocation * working_days_ratio
                available_capacity = max(0, 100 - effective_allocation)
                
                # Only count months with assignments for allocation averaging
                if has_assignment or pto_days > 0:  # Count month if there's assignment OR PTO
                    total_available += available_capacity
                    total_allocated += month_allocation
                    total_effective_allocated += effective_allocation
                    total_working_days += effective_working_days
                    total_pto_days += pto_days
            
            # Average over months that have data (assignments or PTO)
            if months_with_assignments > 0 or total_pto_days > 0:
                # If engineer has assignments or PTO in the quarter
                num_months_to_average = max(months_with_assignments, 1)  # At least 1 to avoid division by zero
                avg_available = total_available / num_months_to_average
                avg_allocated = total_allocated / num_months_to_average
                avg_effective_allocated = total_effective_allocated / num_months_to_average
            else:
                # No assignments or PTO in this quarter - fully available
                avg_available = 100
                avg_allocated = 0
                avg_effective_allocated = 0
            
            quarterly_data.append({
                'Engineer': engineer,
                'Quarter': quarter,
                'Avg Available %': round(avg_available, 1),
                'Avg Allocated %': round(avg_effective_allocated, 1),
                'Total PTO Days': round(total_pto_days, 1),
                'Has Assignments': months_with_assignments > 0
            })
    
    if not quarterly_data:
        return None
    
    quarterly_df = pd.DataFrame(quarterly_data)
    
    # Get all unique engineers
    all_engineers_sorted = sorted(all_engineers)
    num_engineers = len(all_engineers_sorted)
    
    # If too many engineers, use a heatmap instead
    if num_engineers > 15:
        # Create pivot table for heatmap
        pivot_data = quarterly_df.pivot(
            index='Engineer',
            columns='Quarter',
            values='Avg Available %'
        )
        
        # Create a second pivot for showing which quarters have partial data
        has_assignments_pivot = quarterly_df.pivot(
            index='Engineer',
            columns='Quarter',
            values='Has Assignments'
        )
        
        # Sort columns chronologically
        sorted_columns = sort_quarters_chronologically(pivot_data.columns.tolist())
        pivot_data = pivot_data[sorted_columns]
        
        # Create custom text with indicators for partial quarters
        text_data = []
        for i, engineer in enumerate(pivot_data.index):
            row_text = []
            for quarter in sorted_columns:
                value = pivot_data.loc[engineer, quarter]
                has_data = has_assignments_pivot.loc[engineer, quarter] if quarter in has_assignments_pivot.columns else False
                if pd.notna(value):
                    if has_data:
                        row_text.append(f"{value:.1f}%")
                    else:
                        row_text.append(f"{value:.1f}%*")  # * indicates no assignments
                else:
                    row_text.append("")
            text_data.append(row_text)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=sorted_columns,
            y=pivot_data.index.tolist(),
            text=pivot_data.values,
            texttemplate='%{text:.1f}%',
            textfont={"size": 10},
            colorscale='RdYlGn',  # Green for high availability, red for low
            colorbar=dict(
                title="Available %<br>(After PTO)"
            ),
            hovertemplate='Engineer: %{y}<br>Quarter: %{x}<br>Available (After PTO): %{z:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Quarterly Bandwidth Availability by Engineer (Based on Assigned Months) - Heatmap View ({num_engineers} engineers)",
            xaxis_title="Fiscal Quarter",
            yaxis_title="Engineer",
            height=max(600, 30 * num_engineers),  # Dynamic height
            margin=dict(l=150)  # More room for engineer names
        )
    else:
        # Use regular bar chart for fewer engineers
        fig = go.Figure()
        
        # Sort quarters for proper display
        sorted_quarters = sort_quarters_chronologically(quarterly_df['Quarter'].unique())
        
        for engineer in all_engineers_sorted:
            engineer_data = quarterly_df[quarterly_df['Engineer'] == engineer]
            
            fig.add_trace(go.Bar(
                name=engineer,
                x=sorted_quarters,
                y=engineer_data['Avg Available %'].tolist(),
                text=engineer_data['Avg Available %'].apply(lambda x: f"{x}%"),
                textposition='auto',
                hovertemplate='%{x}<br>Available: %{y}%<br>Engineer: ' + engineer + '<br><i>Based on months with assignments</i><extra></extra>'
            ))
        
        # Dynamic height based on number of engineers
        chart_height = max(500, 500 + (num_engineers // 10) * 50)
        
        fig.update_layout(
            title="Quarterly Bandwidth Availability by Engineer (Based on Assigned Months)",
            xaxis_title="Fiscal Quarter",
            yaxis_title="Average Available Bandwidth %",
            barmode='group',
            height=chart_height,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                font=dict(size=10)
            ),
            margin=dict(r=150)  # More room for legend
        )
    
    return fig

def generate_quarterly_utilization_charts(monthly_df, engineers_df):
    """Generate quarterly utilization charts by program and feature"""
    
    if monthly_df.empty:
        return None, None
    
    # Generate months for next 12 months
    current_date = datetime.now()
    months = []
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Filter monthly_df to only include these months
    monthly_df_filtered = monthly_df[monthly_df['Month'].isin(months)]
    
    if monthly_df_filtered.empty:
        return None, None
    
    # Add Quarter column
    monthly_df_filtered['Quarter'] = monthly_df_filtered['Month'].apply(get_fiscal_quarter)
    
    # 1. Utilization by Program
    program_data = []
    if 'Program' in monthly_df_filtered.columns:
        program_quarterly = monthly_df_filtered.groupby(['Quarter', 'Program'])['Allocation %'].sum().reset_index()
        program_quarterly['Allocation %'] = program_quarterly['Allocation %'] / 3  # Average over quarter
        
        # Sort quarters chronologically
        quarter_order = sort_quarters_chronologically(program_quarterly['Quarter'].unique())
        
        fig_program = px.bar(
            program_quarterly,
            x='Quarter',
            y='Allocation %',
            color='Program',
            title='Quarterly Bandwidth Utilization by Program',
            labels={'Allocation %': 'Average Allocation %'},
            text='Allocation %',
            category_orders={'Quarter': quarter_order}
        )
        fig_program.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_program.update_layout(height=500)
    else:
        fig_program = None
    
    # 2. Utilization by Feature
    feature_quarterly = monthly_df_filtered.groupby(['Quarter', 'Feature'])['Allocation %'].sum().reset_index()
    feature_quarterly['Allocation %'] = feature_quarterly['Allocation %'] / 3  # Average over quarter
    
    # Get top 10 features by allocation
    top_features = feature_quarterly.groupby('Feature')['Allocation %'].sum().nlargest(10).index.tolist()
    feature_quarterly_top = feature_quarterly[feature_quarterly['Feature'].isin(top_features)]
    
    # Sort quarters chronologically
    quarter_order = sort_quarters_chronologically(feature_quarterly_top['Quarter'].unique())
    
    fig_feature = px.bar(
        feature_quarterly_top,
        x='Quarter',
        y='Allocation %',
        color='Feature',
        title='Quarterly Bandwidth Utilization by Top Features',
        labels={'Allocation %': 'Average Allocation %'},
        text='Allocation %',
        category_orders={'Quarter': quarter_order}
    )
    fig_feature.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_feature.update_layout(height=500)
    
    return fig_program, fig_feature

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

def generate_program_feature_quarterly_trends(monthly_df):
    """Generate quarterly trend charts for programs and features"""
    
    if monthly_df.empty:
        return None, None
    
    # Generate months for next 12 months
    current_date = datetime.now()
    months = []
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        months.append(month_date.strftime("%Y-%m"))
    
    # Filter monthly_df to only include these months
    monthly_df_filtered = monthly_df[monthly_df['Month'].isin(months)]
    
    if monthly_df_filtered.empty:
        return None, None
    
    # Add Quarter column
    monthly_df_filtered['Quarter'] = monthly_df_filtered['Month'].apply(get_fiscal_quarter)
    
    # 1. Program trend over quarters
    if 'Program' in monthly_df_filtered.columns:
        program_quarterly = monthly_df_filtered.groupby(['Quarter', 'Program'])['Allocation %'].sum().reset_index()
        # Average over 3 months per quarter
        program_quarterly['Allocation %'] = program_quarterly['Allocation %'] / 3
        
        # Create pivot for line chart
        program_pivot = program_quarterly.pivot(index='Quarter', columns='Program', values='Allocation %').fillna(0)
        
        # Sort quarters chronologically
        sorted_quarters = sort_quarters_chronologically(program_pivot.index.tolist())
        program_pivot = program_pivot.reindex(sorted_quarters)
        
        # Create line chart
        fig_program_trend = go.Figure()
        
        for program in program_pivot.columns:
            fig_program_trend.add_trace(go.Scatter(
                x=program_pivot.index,
                y=program_pivot[program],
                mode='lines+markers',
                name=program,
                line=dict(width=3),
                marker=dict(size=10),
                hovertemplate='%{x}<br>%{y:.1f}% allocated<br>Program: ' + program + '<extra></extra>'
            ))
        
        fig_program_trend.update_layout(
            title="Quarterly Program Allocation Trends",
            xaxis_title="Fiscal Quarter",
            yaxis_title="Average Allocation %",
            height=500,
            showlegend=True
        )
    else:
        fig_program_trend = None
    
    # 2. Top features trend over quarters
    feature_quarterly = monthly_df_filtered.groupby(['Quarter', 'Feature'])['Allocation %'].sum().reset_index()
    feature_quarterly['Allocation %'] = feature_quarterly['Allocation %'] / 3
    
    # Get top 8 features by total allocation
    top_features = feature_quarterly.groupby('Feature')['Allocation %'].sum().nlargest(8).index.tolist()
    feature_quarterly_top = feature_quarterly[feature_quarterly['Feature'].isin(top_features)]
    
    # Create pivot for line chart
    feature_pivot = feature_quarterly_top.pivot(index='Quarter', columns='Feature', values='Allocation %').fillna(0)
    
    # Sort quarters chronologically
    sorted_quarters = sort_quarters_chronologically(feature_pivot.index.tolist())
    feature_pivot = feature_pivot.reindex(sorted_quarters)
    
    # Create line chart
    fig_feature_trend = go.Figure()
    
    for feature in feature_pivot.columns:
        fig_feature_trend.add_trace(go.Scatter(
            x=feature_pivot.index,
            y=feature_pivot[feature],
            mode='lines+markers',
            name=feature,
            line=dict(width=2),
            marker=dict(size=8),
            hovertemplate='%{x}<br>%{y:.1f}% allocated<br>Feature: ' + feature + '<extra></extra>'
        ))
    
    fig_feature_trend.update_layout(
        title="Quarterly Top Features Allocation Trends",
        xaxis_title="Fiscal Quarter",
        yaxis_title="Average Allocation %",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        ),
        margin=dict(r=200)  # More room for legend
    )
    
    return fig_program_trend, fig_feature_trend

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
    # Add Program column if it doesn't exist
    if 'Program' not in loaded_monthly_df.columns:
        loaded_monthly_df['Program'] = 'Default Program'
    # Add Priority column if it doesn't exist
    if 'Priority' not in loaded_monthly_df.columns:
        loaded_monthly_df['Priority'] = 'Medium'
        # Save the updated dataframe
        loaded_monthly_df.to_csv(monthly_assignments_file, index=False)
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
# NEW SECTION: Monthly Feature Assignments with Edit Functionality
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

# Add Program column if it doesn't exist
if 'Program' not in monthly_df.columns:
    monthly_df['Program'] = 'Default Program'
    st.session_state.monthly_assignments_df = monthly_df
    monthly_df.to_csv(monthly_assignments_file, index=False)

# Add Priority column if it doesn't exist
if 'Priority' not in monthly_df.columns:
    monthly_df['Priority'] = 'Medium'
    st.session_state.monthly_assignments_df = monthly_df
    monthly_df.to_csv(monthly_assignments_file, index=False)

# Initialize editing state if not exists
if 'editing_assignment' not in st.session_state:
    st.session_state.editing_assignment = None
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

# Tabs for Add/Edit modes
assignment_tab1, assignment_tab2 = st.tabs(["➕ Add Assignment", "✏️ Edit Assignment"])

with assignment_tab1:
    # UI for adding monthly assignments
    col1, col2 = st.columns(2)

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
        program_name = st.text_input("Program Name", key="monthly_program", placeholder="e.g., Project Alpha, Core Platform")

    col3, col4 = st.columns(2)

    with col3:
        feature_name = st.text_input("Feature Name", key="monthly_feature")

    with col4:
        priority = st.selectbox("Priority", options=["Critical", "High", "Medium", "Low"], index=2, key="monthly_priority")

    col5, col6 = st.columns(2)

    with col5:
        # Generate month options
        current_date = datetime.now()
        month_options = []
        for i in range(12):  # Next 12 months
            month_date = current_date + timedelta(days=30*i)
            month_options.append(month_date.strftime("%Y-%m"))
        selected_month = st.selectbox("Month", options=month_options, key="monthly_month")

    with col6:
        allocation_percent = st.number_input("Allocation %", min_value=0, max_value=100, value=0, step=5, key="monthly_allocation")

    notes = st.text_area("Notes", key="monthly_notes", height=75)

    # Buttons in columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Add Monthly Assignment", key="add_monthly_assignment", type="primary"):
            if selected_engineer and feature_name and allocation_percent > 0:
                new_assignment = {
                    "Engineer Name": str(selected_engineer).strip(),  # Ensure it's stored as string and stripped
                    "Program": program_name if program_name else "Default Program",
                    "Feature": feature_name,
                    "Priority": priority,  # Add priority
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
                st.success(f"Added assignment: {selected_engineer} -> {feature_name} ({allocation_percent}%) for {selected_month} - Priority: {priority}")
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

with assignment_tab2:
    st.subheader("Edit Existing Assignment")
    
    # Get current assignments
    current_monthly_df = st.session_state.monthly_assignments_df
    
    if current_monthly_df.empty:
        st.info("No assignments to edit. Add some assignments first!")
    else:
        # Create selection options
        edit_options = []
        for idx, row in current_monthly_df.iterrows():
            allocation = row['Allocation %']
            priority = row.get('Priority', 'Medium')
            edit_options.append(f"{idx}: [{priority}] {row['Engineer Name']} - {row['Program']} - {row['Feature']} ({row['Month']}, {allocation}%)")
        
        selected_to_edit = st.selectbox("Select assignment to edit:", options=edit_options, key="edit_assignment_select")
        
        if selected_to_edit:
            # Extract index from the selected option
            edit_idx = int(selected_to_edit.split(":")[0])
            assignment_to_edit = current_monthly_df.iloc[edit_idx]
            
            # Show edit form
            st.write("**Edit Assignment Details:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Get valid engineers
                engineer_list = engineers_df['Engineer Name'].tolist()
                valid_engineers = []
                for name in engineer_list:
                    if name is not None and str(name).strip() and str(name) != 'nan':
                        valid_engineers.append(str(name).strip())
                
                # Find current engineer index
                current_engineer_idx = 0
                try:
                    current_engineer_idx = valid_engineers.index(str(assignment_to_edit['Engineer Name']).strip())
                except:
                    pass
                
                edit_engineer = st.selectbox(
                    "Engineer", 
                    options=valid_engineers, 
                    index=current_engineer_idx,
                    key="edit_engineer"
                )
            
            with col2:
                edit_program = st.text_input(
                    "Program Name", 
                    value=assignment_to_edit['Program'],
                    key="edit_program"
                )
            
            col3, col4 = st.columns(2)
            
            with col3:
                edit_feature = st.text_input(
                    "Feature Name", 
                    value=assignment_to_edit['Feature'],
                    key="edit_feature"
                )
            
            with col4:
                priority_options = ["Critical", "High", "Medium", "Low"]
                current_priority_idx = priority_options.index(assignment_to_edit.get('Priority', 'Medium'))
                edit_priority = st.selectbox(
                    "Priority", 
                    options=priority_options, 
                    index=current_priority_idx,
                    key="edit_priority"
                )
            
            col5, col6 = st.columns(2)
            
            with col5:
                # Generate month options
                current_date = datetime.now()
                month_options = []
                for i in range(12):
                    month_date = current_date + timedelta(days=30*i)
                    month_options.append(month_date.strftime("%Y-%m"))
                
                # Find current month index
                current_month_idx = 0
                try:
                    current_month_idx = month_options.index(assignment_to_edit['Month'])
                except:
                    pass
                
                edit_month = st.selectbox(
                    "Month", 
                    options=month_options, 
                    index=current_month_idx,
                    key="edit_month"
                )
            
            with col6:
                edit_allocation = st.number_input(
                    "Allocation %", 
                    min_value=0, 
                    max_value=100, 
                    value=int(assignment_to_edit['Allocation %']),
                    step=5,
                    key="edit_allocation"
                )
            
            edit_notes = st.text_area(
                "Notes", 
                value=assignment_to_edit.get('Notes', ''),
                key="edit_notes",
                height=75
            )
            
            # Update and Delete buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Update Assignment", key="update_assignment_btn", type="primary"):
                    # Update the assignment
                    current_monthly_df.loc[edit_idx, 'Engineer Name'] = str(edit_engineer).strip()
                    current_monthly_df.loc[edit_idx, 'Program'] = edit_program
                    current_monthly_df.loc[edit_idx, 'Feature'] = edit_feature
                    current_monthly_df.loc[edit_idx, 'Priority'] = edit_priority
                    current_monthly_df.loc[edit_idx, 'Month'] = edit_month
                    current_monthly_df.loc[edit_idx, 'Allocation %'] = edit_allocation
                    current_monthly_df.loc[edit_idx, 'Notes'] = edit_notes
                    
                    # Ensure all engineer names are stripped
                    current_monthly_df['Engineer Name'] = current_monthly_df['Engineer Name'].fillna('').astype(str).str.strip()
                    
                    # Update session state
                    st.session_state.monthly_assignments_df = current_monthly_df
                    
                    # Auto-save
                    current_monthly_df.to_csv(monthly_assignments_file, index=False)
                    st.success("Assignment updated and saved!")
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Delete This Assignment", key="delete_from_edit_btn"):
                    updated_df = current_monthly_df.drop(index=edit_idx).reset_index(drop=True)
                    st.session_state.monthly_assignments_df = updated_df
                    # Auto-save
                    updated_df.to_csv(monthly_assignments_file, index=False)
                    st.success("Assignment deleted and saved!")
                    st.rerun()

# Display selected engineer's assignments dynamically
if 'monthly_engineer' in st.session_state and st.session_state.monthly_engineer:
    selected_engineer = st.session_state.monthly_engineer
    st.subheader(f"📋 {selected_engineer}'s Current Assignments")
    
    # Get the latest monthly_df from session state
    current_monthly_df = st.session_state.monthly_assignments_df
    
    # Ensure we're comparing strings properly
    engineer_assignments = current_monthly_df[current_monthly_df['Engineer Name'].astype(str) == str(selected_engineer)].sort_values(['Priority', 'Month'])
    
    if not engineer_assignments.empty:
        # Create a formatted version for display
        display_df = engineer_assignments.copy()
        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
        
        # Add priority color coding
        def priority_color(priority):
            colors = {
                'Critical': '🔴',
                'High': '🟠',
                'Medium': '🟡',
                'Low': '🟢'
            }
            return colors.get(priority, '⚪') + ' ' + priority
        
        if 'Priority' in display_df.columns:
            display_df['Priority'] = display_df['Priority'].apply(priority_color)
        
        # Display the dataframe
        st.dataframe(
            display_df[['Priority', 'Program', 'Feature', 'Month', 'Allocation %', 'Notes']], 
            use_container_width=True,
            hide_index=True
        )
        
        # Quick stats for selected engineer
        col1, col2, col3, col4 = st.columns(4)
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
        with col4:
            # Count critical/high priority items
            if 'Priority' in engineer_assignments.columns:
                critical_high = len(engineer_assignments[engineer_assignments['Priority'].isin(['Critical', 'High'])])
                st.metric("Critical/High Priority", critical_high)
    else:
        st.info(f"No assignments found for {selected_engineer}. Add one using the form above!")

# Separator
st.divider()

# Display all assignments grouped by engineer
current_monthly_df = st.session_state.monthly_assignments_df
if not current_monthly_df.empty:
    st.subheader("All Monthly Assignments")
    
    # Add high priority filter
    show_high_priority = st.checkbox("Show only Critical/High priority assignments", key="filter_high_priority")
    
    if show_high_priority and 'Priority' in current_monthly_df.columns:
        filtered_df = current_monthly_df[current_monthly_df['Priority'].isin(['Critical', 'High'])]
        if filtered_df.empty:
            st.info("No Critical or High priority assignments found.")
            current_monthly_df = st.session_state.monthly_assignments_df  # Reset to show all
        else:
            current_monthly_df = filtered_df
            st.info(f"Showing {len(filtered_df)} Critical/High priority assignments")
    
    # Add view options
    view_mode = st.radio("View Mode:", ["By Engineer", "By Month", "By Program", "All Assignments"], horizontal=True)
    
    if view_mode == "By Engineer":
        # Group by engineer for better visualization
        engineers_in_monthly = current_monthly_df['Engineer Name'].unique()
        
        for engineer in engineers_in_monthly:
            if 'monthly_engineer' not in st.session_state or str(engineer) != str(st.session_state.monthly_engineer):  # Don't duplicate the selected engineer
                engineer_assignments = current_monthly_df[current_monthly_df['Engineer Name'] == engineer].sort_values(['Priority', 'Month'])
                
                with st.expander(f"📋 {engineer}'s Assignments ({len(engineer_assignments)} assignments)"):
                    if not engineer_assignments.empty:
                        display_df = engineer_assignments.copy()
                        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                        
                        # Add priority color coding
                        def priority_color(priority):
                            colors = {
                                'Critical': '🔴',
                                'High': '🟠',
                                'Medium': '🟡',
                                'Low': '🟢'
                            }
                            return colors.get(priority, '⚪') + ' ' + priority
                        
                        if 'Priority' in display_df.columns:
                            display_df['Priority'] = display_df['Priority'].apply(priority_color)
                        
                        st.dataframe(
                            display_df[['Priority', 'Program', 'Feature', 'Month', 'Allocation %', 'Notes']], 
                            use_container_width=True,
                            hide_index=True
                        )
    
    elif view_mode == "By Month":
        # Group by month
        months = sorted(current_monthly_df['Month'].unique())
        
        for month in months:
            month_assignments = current_monthly_df[current_monthly_df['Month'] == month].sort_values(['Priority', 'Engineer Name'])
            
            with st.expander(f"📅 {month} Assignments ({len(month_assignments)} assignments)"):
                if not month_assignments.empty:
                    display_df = month_assignments.copy()
                    display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                    
                    # Add priority color coding
                    def priority_color(priority):
                        colors = {
                            'Critical': '🔴',
                            'High': '🟠',
                            'Medium': '🟡',
                            'Low': '🟢'
                        }
                        return colors.get(priority, '⚪') + ' ' + priority
                    
                    if 'Priority' in display_df.columns:
                        display_df['Priority'] = display_df['Priority'].apply(priority_color)
                    
                    st.dataframe(
                        display_df[['Priority', 'Engineer Name', 'Program', 'Feature', 'Allocation %', 'Notes']], 
                        use_container_width=True,
                        hide_index=True
                    )
    
    elif view_mode == "By Program":
        # Group by program
        programs = sorted(current_monthly_df['Program'].unique())
        
        for program in programs:
            program_assignments = current_monthly_df[current_monthly_df['Program'] == program].sort_values(['Priority', 'Month', 'Engineer Name'])
            
            with st.expander(f"🎯 {program} ({len(program_assignments)} assignments)"):
                if not program_assignments.empty:
                    display_df = program_assignments.copy()
                    display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                    
                    # Add priority color coding
                    def priority_color(priority):
                        colors = {
                            'Critical': '🔴',
                            'High': '🟠',
                            'Medium': '🟡',
                            'Low': '🟢'
                        }
                        return colors.get(priority, '⚪') + ' ' + priority
                    
                    if 'Priority' in display_df.columns:
                        display_df['Priority'] = display_df['Priority'].apply(priority_color)
                    
                    st.dataframe(
                        display_df[['Priority', 'Engineer Name', 'Feature', 'Month', 'Allocation %', 'Notes']], 
                        use_container_width=True,
                        hide_index=True
                    )
    
    else:  # All Assignments
        display_df = current_monthly_df.copy().sort_values(['Priority', 'Month', 'Engineer Name'])
        display_df['Allocation %'] = display_df['Allocation %'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
        
        # Add priority color coding
        def priority_color(priority):
            colors = {
                'Critical': '🔴',
                'High': '🟠',
                'Medium': '🟡',
                'Low': '🟢'
            }
            return colors.get(priority, '⚪') + ' ' + priority
        
        if 'Priority' in display_df.columns:
            display_df['Priority'] = display_df['Priority'].apply(priority_color)
        
        st.dataframe(
            display_df[['Priority', 'Engineer Name', 'Program', 'Feature', 'Month', 'Allocation %', 'Notes']], 
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No monthly assignments yet. Use the form above to add assignments.")

# ─────────────────────────────────────────────────────────────
# Quarterly Utilization Summary
# ─────────────────────────────────────────────────────────────

st.header("📊 Quarterly Engineer Utilization Summary")

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
            if 'Program' not in loaded_monthly.columns:
                loaded_monthly['Program'] = 'Default Program'
            if 'Priority' not in loaded_monthly.columns:
                loaded_monthly['Priority'] = 'Medium'
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
        if 'Program' not in monthly_df.columns:
            monthly_df['Program'] = 'Default Program'
        if 'Priority' not in monthly_df.columns:
            monthly_df['Priority'] = 'Medium'
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
            st.subheader("Quarterly Engineer Availability Overview")
            
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
                if 'Current Quarter Availability' in availability_summary.columns and 'Avg. Quarterly Availability' in availability_summary.columns:
                    styled_summary = styled_summary.map(color_availability, subset=['Current Quarter Availability', 'Avg. Quarterly Availability'])
                st.dataframe(styled_summary, use_container_width=True)
            else:
                # Display without styling if columns are missing
                st.dataframe(availability_summary, use_container_width=True)
            
            # Show detailed quarterly breakdown
            with st.expander("📋 Detailed Quarterly Availability Breakdown"):
                # Create pivot table for better visualization
                if not availability_details.empty:
                    try:
                        pivot_data = []
                        for _, row in availability_details.iterrows():
                            pivot_data.append({
                                'Engineer': row['Engineer'],
                                'Quarter': row['Quarter'],
                                'Allocation %': row['Effective Allocation %'],
                                'Available %': row['Available %'],
                                'Working Days': row['Working Days']
                            })
                        
                        pivot_df = pd.DataFrame(pivot_data)
                        if not pivot_df.empty and len(pivot_df['Engineer'].unique()) > 0 and len(pivot_df['Quarter'].unique()) > 0:
                            pivot_table = pivot_df.pivot_table(
                                index='Engineer',
                                columns='Quarter',
                                values=['Available %', 'Allocation %'],
                                fill_value=100
                            )
                            
                            # Sort columns chronologically
                            quarters = pivot_table.columns.get_level_values(1).unique()
                            sorted_quarters = sort_quarters_chronologically(quarters.tolist())
                            
                            st.write("**Quarterly Availability % by Engineer:**")
                            availability_pivot = pivot_table['Available %'][sorted_quarters]
                            
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
                            
                            st.write("**Quarterly Allocation % by Engineer:**")
                            allocation_pivot = pivot_table['Allocation %'][sorted_quarters]
                            
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
                    st.info("No availability details to show. Add assignments to see the quarterly breakdown.")
            
            # Add priority summary if Priority column exists
            if 'Priority' in monthly_df.columns and not monthly_df.empty:
                st.subheader("📊 Quarterly Priority Summary")
                
                # Get current quarter data
                current_date = datetime.now()
                current_month = current_date.strftime("%Y-%m")
                current_quarter = get_fiscal_quarter(current_month)
                
                # Filter data for current quarter
                monthly_df_with_quarter = monthly_df.copy()
                monthly_df_with_quarter['Quarter'] = monthly_df_with_quarter['Month'].apply(get_fiscal_quarter)
                current_quarter_data = monthly_df_with_quarter[monthly_df_with_quarter['Quarter'] == current_quarter]
                
                col1, col2, col3, col4 = st.columns(4)
                
                if not current_quarter_data.empty:
                    priority_counts = current_quarter_data['Priority'].value_counts()
                    
                    with col1:
                        critical_count = priority_counts.get('Critical', 0)
                        st.metric(f"🔴 Critical Tasks ({current_quarter})", critical_count)
                    
                    with col2:
                        high_count = priority_counts.get('High', 0)
                        st.metric(f"🟠 High Priority ({current_quarter})", high_count)
                    
                    with col3:
                        medium_count = priority_counts.get('Medium', 0)
                        st.metric(f"🟡 Medium Priority ({current_quarter})", medium_count)
                    
                    with col4:
                        low_count = priority_counts.get('Low', 0)
                        st.metric(f"🟢 Low Priority ({current_quarter})", low_count)
                    
                    # Show critical assignments if any
                    if critical_count > 0:
                        with st.expander(f"⚠️ Critical Priority Assignments for {current_quarter}", expanded=True):
                            critical_assignments = current_quarter_data[current_quarter_data['Priority'] == 'Critical'].sort_values(['Month', 'Engineer Name'])
                            display_critical = critical_assignments[['Engineer Name', 'Program', 'Feature', 'Month', 'Allocation %']].copy()
                            display_critical['Allocation %'] = display_critical['Allocation %'].apply(lambda x: f"{x}%")
                            st.dataframe(display_critical, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No assignments found for {current_quarter}")
            
            st.markdown("""
            **Status Indicators:**
            - Engineers are considered fully occupied at 85% allocation
            - Over-allocation occurs above 100%
            
            **Availability Colors:**
            - 🟢 Green: Good availability (>20%)
            - 🟡 Yellow: Low availability (1-20%)
            - 🔴 Red: No availability (0%)
            
            **Priority Levels:**
            - 🔴 Critical: Urgent/blocking tasks
            - 🟠 High: Important tasks that need attention soon
            - 🟡 Medium: Regular priority tasks
            - 🟢 Low: Nice-to-have or future tasks
            
            **Calculation Method:**
            - Quarterly averages are based only on months where engineers have assignments
            - If an engineer has 30% allocation in August only, Q1 shows 30% utilization (70% available)
            - Empty months are not included in the average calculation
            - PTO is always factored into the calculations
            
            **Fiscal Year Quarters (FY starts in August):**
            - Q1: August - October (e.g., Aug 2025 = Q1 FY26)
            - Q2: November - January
            - Q3: February - April  
            - Q4: May - July
            """)
        else:
            st.info("No utilization data available. Add engineers and monthly assignments to see quarterly utilization summary.")
except Exception as e:
    st.error(f"Error generating utilization summary: {str(e)}")
    st.info("Please check your data and try again. If the problem persists, try refreshing the page or clearing your browser cache.")

# ─────────────────────────────────────────────────────────────
# Quarterly Charts Section
# ─────────────────────────────────────────────────────────────

st.header("📊 Quarterly Analysis")

# Note about chart display
st.info("""📌 Note: Quarterly calculations work as follows:
- If an engineer has assignments in only some months of a quarter, the average is calculated ONLY for those months
- Example: 30% allocation in August only = Q1 shows 30% utilization (70% available), not 10% utilization
- Months without assignments are excluded from averaging to reflect actual workload
- The heatmap shows '*' for quarters where an engineer has no assignments (100% available)
- All values are PTO-adjusted""")

# Get the latest data
monthly_df = st.session_state.monthly_assignments_df
engineers_df = st.session_state.engineers_df

# Calculate current quarter metrics
if not monthly_df.empty and not engineers_df.empty:
    current_date = datetime.now()
    current_month = current_date.strftime("%Y-%m")
    current_quarter = get_fiscal_quarter(current_month)
    
    # Get months in current quarter
    all_months = []
    for i in range(12):
        month_date = current_date + timedelta(days=30*i)
        all_months.append(month_date.strftime("%Y-%m"))
    
    current_quarter_months = []
    for month in all_months[:3]:  # Check first 3 months to find current quarter
        if get_fiscal_quarter(month) == current_quarter:
            current_quarter_months.append(month)
    
    # Calculate metrics
    if current_quarter_months:
        current_quarter_data = monthly_df[monthly_df['Month'].isin(current_quarter_months)]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Quarter", current_quarter)
        
        with col2:
            total_assignments = len(current_quarter_data)
            st.metric("Assignments This Quarter", total_assignments)
        
        with col3:
            if 'Program' in current_quarter_data.columns:
                active_programs = current_quarter_data['Program'].nunique()
                st.metric("Active Programs", active_programs)
            else:
                st.metric("Active Programs", "N/A")
        
        with col4:
            if 'Priority' in current_quarter_data.columns:
                critical_high = len(current_quarter_data[current_quarter_data['Priority'].isin(['Critical', 'High'])])
                st.metric("Critical/High Priority", critical_high)
            else:
                st.metric("Critical/High Priority", "N/A")
        
        st.divider()

# Tab organization for quarterly views
quarterly_tab1, quarterly_tab2, quarterly_tab3 = st.tabs(["📈 Trends Over Time", "📊 Current Quarter Distribution", "👥 Engineer Availability"])

with quarterly_tab1:
    st.subheader("Quarterly Trends Analysis")
    
    # Team utilization summary
    team_summary_fig = generate_team_utilization_summary(monthly_df, engineers_df)
    if team_summary_fig:
        st.plotly_chart(team_summary_fig, use_container_width=True)
    else:
        st.info("No data available for team utilization summary.")
    
    # Generate trend charts
    program_trend_fig, feature_trend_fig = generate_program_feature_quarterly_trends(monthly_df)
    
    if program_trend_fig:
        st.plotly_chart(program_trend_fig, use_container_width=True)
    else:
        st.info("No program data available for trend analysis.")
    
    if feature_trend_fig:
        st.plotly_chart(feature_trend_fig, use_container_width=True)
    else:
        st.info("No feature data available for trend analysis.")

with quarterly_tab2:
    st.subheader("Current Quarter Allocation Distribution")
    
    # Generate quarterly utilization charts
    program_fig, feature_fig = generate_quarterly_utilization_charts(monthly_df, engineers_df)
    
    if program_fig:
        st.plotly_chart(program_fig, use_container_width=True)
    
    if feature_fig:
        st.plotly_chart(feature_fig, use_container_width=True)
    
    # Add priority breakdown chart if Priority column exists
    if not monthly_df.empty and 'Priority' in monthly_df.columns:
        # Create priority breakdown by quarter
        monthly_df_with_quarter = monthly_df.copy()
        monthly_df_with_quarter['Quarter'] = monthly_df_with_quarter['Month'].apply(get_fiscal_quarter)
        
        priority_quarterly = monthly_df_with_quarter.groupby(['Quarter', 'Priority'])['Allocation %'].sum().reset_index()
        priority_quarterly['Allocation %'] = priority_quarterly['Allocation %'] / 3  # Average over quarter
        
        # Define priority order and colors
        priority_order = ['Critical', 'High', 'Medium', 'Low']
        priority_colors = {'Critical': '#FF4444', 'High': '#FF8800', 'Medium': '#FFBB00', 'Low': '#00CC00'}
        
        # Sort quarters chronologically
        quarter_order = sort_quarters_chronologically(priority_quarterly['Quarter'].unique())
        
        fig_priority = px.bar(
            priority_quarterly,
            x='Quarter',
            y='Allocation %',
            color='Priority',
            title='Quarterly Bandwidth Utilization by Priority',
            labels={'Allocation %': 'Average Allocation %'},
            text='Allocation %',
            category_orders={'Priority': priority_order, 'Quarter': quarter_order},
            color_discrete_map=priority_colors
        )
        fig_priority.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_priority.update_layout(height=500)
        
        st.plotly_chart(fig_priority, use_container_width=True)
    
    if not any([program_fig, feature_fig]):
        st.info("Add monthly assignments to see quarterly utilization charts by program and feature.")

with quarterly_tab3:
    st.subheader("Engineer Availability by Quarter")
    
    # Generate quarterly availability chart
    quarterly_availability_fig = generate_quarterly_availability_chart(monthly_df, engineers_df)
    if quarterly_availability_fig:
        st.plotly_chart(quarterly_availability_fig, use_container_width=True)
    else:
        st.info("No data available for quarterly availability chart.")

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
