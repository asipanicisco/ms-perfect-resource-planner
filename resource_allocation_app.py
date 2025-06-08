import streamlit as st
import pandas as pd
import xlsxwriter
from io import BytesIO
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

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
    n = len(engineer_list)
    return pd.DataFrame({
        "Team": ["Team A", "Team B"] if n >= 2 else ["Team A"] * n,
        "Engineer Name": engineer_list,
        "PTO Days": [0 for _ in range(n)],
        "Project Alpha Allocation": [50, 30] if n >= 2 else [50] * n,
        "Project Beta Allocation": [30, 40] if n >= 2 else [30] * n,
        "Notes": ["" for _ in range(n)]
    })

# ─────────────────────────────────────────────────────────────
# 2) Generate Program Allocation Chart Preview
# ─────────────────────────────────────────────────────────────

def generate_allocation_chart_preview(programs_df):
    """Generate a stacked bar chart showing program allocation by engineer (PTO-adjusted)"""
    
    # Make a copy for processing
    df_copy = programs_df.copy()
    
    # Find allocation columns
    alloc_cols = [col for col in df_copy.columns if col.endswith('% Allocated') or col.endswith('Allocation')]
    
    if not alloc_cols or len(df_copy) == 0:
        return None, None
    
    # Calculate adjusted allocations for each program
    chart_data = {}
    engineers = df_copy.get('Engineer Name', []).tolist()
    
    for col in alloc_cols:
        program_name = col.replace(' % Allocated', '').replace(' Allocation', '')
        adjusted_values = []
        
        for idx, val in enumerate(df_copy.get(col, [])):
            try:
                # Handle different input formats
                val_str = str(val).replace('%', '').strip()
                if val_str and val_str != 'nan' and val_str != '':
                    percent = float(val_str)
                    pto = float(df_copy.get('PTO Days', [0] * len(df_copy))[idx])
                    # Adjust for PTO: effective allocation = percent * ((30 - pto_days) / 30)
                    effective = percent * ((30 - pto) / 30) if pto < 30 else 0
                    adjusted_values.append(max(0, effective))
                else:
                    adjusted_values.append(0.0)
            except (ValueError, TypeError):
                adjusted_values.append(0.0)
        
        chart_data[program_name] = adjusted_values
    
    # Calculate effective total utilization
    total_utilization = []
    for idx in range(len(engineers)):
        total = sum(chart_data[program][idx] for program in chart_data.keys())
        total_utilization.append(round(total, 2))
    
    # Create stacked bar chart using plotly
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for i, (program, values) in enumerate(chart_data.items()):
        if any(v > 0 for v in values):  # Only add if there's actual data
            fig.add_trace(go.Bar(
                name=program,
                x=engineers,
                y=values,
                marker_color=colors[i % len(colors)]
            ))
    
    fig.update_layout(
        title='Engineer Allocation by Program (PTO-Adjusted)',
        xaxis_title='Engineer',
        yaxis_title='Allocation (%)',
        barmode='stack',
        legend=dict(orientation="h", yanchor="top", y=-0.1),
        height=500
    )
    
    # Create utilization summary DataFrame
    utilization_df = pd.DataFrame({
        'Engineer': engineers,
        'Team': df_copy.get('Team', ['']*len(engineers)),
        'PTO Days': df_copy.get('PTO Days', [0]*len(engineers)),
        'Effective Total %': total_utilization
    })
    
    return fig, utilization_df

# ─────────────────────────────────────────────────────────────
# 3) Generate Excel File with Charts (Including PTO Adjustments)
# ─────────────────────────────────────────────────────────────

def generate_excel(engineers_df, programs_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Write data to separate sheets
        engineers_df.to_excel(writer, sheet_name='Engineer Capacity', index=False)
        programs_df.to_excel(writer, sheet_name='Program Allocation', index=False)
        
        # Add future projects sheet if it exists in session state
        if 'future_projects_df' in st.session_state and not st.session_state.future_projects_df.empty:
            st.session_state.future_projects_df.to_excel(writer, sheet_name='Future Projects', index=False)

        workbook = writer.book
        worksheet_program = writer.sheets['Program Allocation']
        
        # Make a copy of the DataFrame for processing
        df_copy = programs_df.copy()
        
        # Dynamically detect all allocation columns (both '% Allocated' and 'Allocation' patterns)
        alloc_cols = [col for col in df_copy.columns if col.endswith('% Allocated') or col.endswith('Allocation')]
        
        # Only create chart if we have allocation columns and data
        if alloc_cols and len(df_copy) > 0:
            chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
            
            # Assign a color palette
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            series_added = False
            
            for i, col in enumerate(alloc_cols):
                color = colors[i % len(colors)]
                adjusted_values = []
                valid_data = False
                
                for idx, val in enumerate(df_copy.get(col, [])):
                    try:
                        # Handle different input formats
                        val_str = str(val).replace('%', '').strip()
                        if val_str and val_str != 'nan' and val_str != '':
                            percent = float(val_str)
                            pto = float(df_copy.get('PTO Days', [0] * len(df_copy))[idx])
                            effective = percent * ((30 - pto) / 30) if pto < 30 else 0
                            adjusted_values.append(max(0, effective))
                            if effective > 0:
                                valid_data = True
                        else:
                            adjusted_values.append(0.0)
                    except (ValueError, TypeError):
                        adjusted_values.append(0.0)
                
                # Only add series if there's valid data
                if valid_data:
                    temp_col = f"Adjusted_{col.replace(' ', '_').replace('%', 'Pct')}"
                    df_copy[temp_col] = pd.Series(adjusted_values)
                    
                    # Write the adjusted values to the worksheet for the chart
                    col_idx = len(df_copy.columns) - 1
                    for row_idx, val in enumerate(adjusted_values):
                        worksheet_program.write(row_idx + 1, col_idx, val)
                    
                    # Add series to chart
                    chart.add_series({
                        'name': col.replace(' % Allocated', '').replace(' Allocation', ''),
                        'categories': ['Program Allocation', 1, 0, len(df_copy), 0],
                        'values': ['Program Allocation', 1, col_idx, len(df_copy), col_idx],
                        'fill': {'color': color},
                    })
                    series_added = True
            
            # Only insert chart if we added at least one series
            if series_added:
                chart.set_title({'name': 'Engineer Allocation by Program (adjusted for PTO)'})
                chart.set_x_axis({'name': 'Engineer'})
                chart.set_y_axis({'name': 'Allocation (%)'})
                chart.set_legend({'position': 'bottom'})
                worksheet_program.insert_chart('L2', chart)

        # Calculate Effective Total %
        total_utilization = []
        for idx in range(len(df_copy)):
            try:
                total = 0.0
                for col_name in df_copy.columns:
                    if col_name.startswith('Adjusted_'):
                        total += df_copy[col_name].iloc[idx]
                total_utilization.append(round(total, 2))
            except:
                total_utilization.append(0.0)
        
        # Add Effective Total % column
        df_copy['Effective Total %'] = total_utilization
        
        # Write the Effective Total % to the worksheet
        if 'Effective Total %' in df_copy.columns:
            et_col_idx = len(programs_df.columns)  # Position after original columns
            worksheet_program.write(0, et_col_idx, 'Effective Total %')
            for row_idx, val in enumerate(total_utilization):
                worksheet_program.write(row_idx + 1, et_col_idx, val)
            
            # Heatmap formatting for Effective Total %
            red_fmt = workbook.add_format({'bg_color': '#FF9999'})
            yellow_fmt = workbook.add_format({'bg_color': '#FFEB99'})
            green_fmt = workbook.add_format({'bg_color': '#CCFFCC'})
            
            worksheet_program.conditional_format(1, et_col_idx, len(df_copy), et_col_idx, {
                'type': 'cell',
                'criteria': '>=',
                'value': 100,
                'format': red_fmt
            })
            worksheet_program.conditional_format(1, et_col_idx, len(df_copy), et_col_idx, {
                'type': 'cell',
                'criteria': 'between',
                'minimum': 80,
                'maximum': 99.99,
                'format': yellow_fmt
            })
            worksheet_program.conditional_format(1, et_col_idx, len(df_copy), et_col_idx, {
                'type': 'cell',
                'criteria': '<',
                'value': 80,
                'format': green_fmt
            })

        # Build Gantt sheet
        gantt_sheet = workbook.add_worksheet("Program Timeline")
        gantt_sheet.write_row("A1", ["Engineer Name", "Team", "Program", "Start Date", "End Date"])
        row_idx = 1
        
        for _, row_data in df_copy.iterrows():
            engineer = row_data.get("Engineer Name", "")
            team = row_data.get("Team", "")
            
            for col in alloc_cols:
                try:
                    val_str = str(row_data.get(col, "")).replace('%', '').strip()
                    if val_str and val_str != 'nan' and val_str != '' and float(val_str) > 0:
                        program = col.replace(' % Allocated', '').replace(' Allocation', '')
                        end_date = row_data.get(f"{program} End Date", "")
                        
                        if not end_date or pd.isna(end_date):
                            # Default to 30 days from today if no end date
                            end_dt = datetime.today() + pd.Timedelta(days=30)
                        else:
                            try:
                                end_dt = datetime.strptime(str(end_date), "%Y-%m-%d")
                            except:
                                end_dt = datetime.today() + pd.Timedelta(days=30)
                        
                        start_dt = end_dt - pd.Timedelta(days=30)
                        gantt_sheet.write_row(row_idx, 0, [
                            engineer, team, program,
                            start_dt.date().isoformat(), end_dt.date().isoformat()
                        ])
                        row_idx += 1
                except (ValueError, TypeError):
                    continue
    
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

def generate_gantt_dataframe(programs_df):
    gantt_data = []
    today = datetime.today()
    fixed_cols = {"Team", "Engineer Name", "PTO Days", "Notes"}
    
    # Find allocation columns (both patterns)
    alloc_cols = [col for col in programs_df.columns if col.endswith('% Allocated') or col.endswith('Allocation')]
    
    for _, row_data in programs_df.iterrows():
        engineer = row_data.get("Engineer Name", "")
        team = row_data.get("Team", "")
        
        for col in alloc_cols:
            try:
                percent_str = str(row_data.get(col, "")).replace('%', '').strip()
                if percent_str and percent_str != 'nan' and percent_str != '':
                    percent = float(percent_str)
                    if percent > 0:
                        program = col.replace(' % Allocated', '').replace(' Allocation', '')
                        end_dt = today + pd.Timedelta(days=30)
                        start_dt = end_dt - pd.Timedelta(days=30)
                        gantt_data.append({
                            "Engineer": engineer,
                            "Team": team,
                            "Program": program,
                            "Start": start_dt,
                            "Finish": end_dt,
                            "Allocation": percent
                        })
            except (ValueError, TypeError):
                continue
    
    return pd.DataFrame(gantt_data)

# ─────────────────────────────────────────────────────────────
# 6) Main App Logic
# ─────────────────────────────────────────────────────────────

engineer_file = "engineers.csv"
program_file = "programs.csv"
future_projects_file = "future_projects.csv"

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

st.header("📊 Program Allocation")

# Initialize Programs DataFrame
if "programs_df" not in st.session_state:
    try:
        programs_df = pd.read_csv(program_file)
    except FileNotFoundError:
        engineer_list = st.session_state.engineers_df.get("Engineer Name", []).tolist()
        programs_df = default_programs(engineer_list)
    st.session_state.programs_df = programs_df

programs_df = st.session_state.programs_df

if st.button("➕ Add Program Row", key="add_prog_row"):
    new_prog_row = {col: "" if not (col.endswith('Allocation') or col.endswith('% Allocated')) and col != "PTO Days" else 0 for col in programs_df.columns}
    programs_df = pd.concat([programs_df, pd.DataFrame([new_prog_row])], ignore_index=True)
    st.session_state.programs_df = programs_df

# Expander to rename program columns
with st.expander("Rename Program Columns", expanded=False):
    prog_renames = {}
    for col in programs_df.columns:
        new_col = st.text_input(f"Rename '{col}' to:", value=col, key=f"rename_prog_{col}")
        prog_renames[col] = new_col
    if st.button("Apply Program Renames", key="apply_prog_renames"):
        programs_df = programs_df.rename(columns=prog_renames)
        st.session_state.programs_df = programs_df
        # Save the renamed dataframe to CSV to persist changes
        programs_df.to_csv(program_file, index=False)
        st.success("Program column names updated and saved!")

# Expander for modifying columns
with st.expander("Modify Program Columns", expanded=False):
    cols = programs_df.columns.tolist()
    col_to_delete = st.selectbox("Select column to delete:", options=cols, key="delete_prog_col")
    if st.button("Delete Column", key="del_prog_col_btn"):
        if col_to_delete in programs_df.columns:
            programs_df.drop(columns=[col_to_delete], inplace=True)
            st.session_state.programs_df = programs_df
            # Save changes to CSV to persist
            programs_df.to_csv(program_file, index=False)
            st.success(f"Deleted column '{col_to_delete}' and saved changes")
    
    new_col_name = st.text_input("New column name:", key="new_prog_col_name")
    if st.button("Add Column", key="add_prog_col_btn"):
        if new_col_name and new_col_name not in programs_df.columns:
            programs_df[new_col_name] = ""
            st.session_state.programs_df = programs_df
            # Save changes to CSV to persist
            programs_df.to_csv(program_file, index=False)
            st.success(f"Added column '{new_col_name}' and saved changes")
        else:
            st.error("Invalid or duplicate column name.")

if aggrid_available:
    # Build grid options for programs
    gb_prog = GridOptionsBuilder.from_dataframe(programs_df)
    gb_prog.configure_default_column(editable=True)
    prog_response = AgGrid(
        programs_df,
        gridOptions=gb_prog.build(),
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True,
        update_mode='VALUE_CHANGED',
        key='prog_grid'
    )
    programs_df = pd.DataFrame(prog_response['data'])
    st.session_state.programs_df = programs_df
else:
    # Fallback to regular data editor
    programs_df = st.data_editor(programs_df, key="programs_editor")
    st.session_state.programs_df = programs_df

if st.button("💾 Save Program Changes", key="save_prog_btn"):
    programs_df.to_csv(program_file, index=False)
    st.success("Program data saved!")

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

# Show Program Allocation Chart Preview instead of Gantt
allocation_chart, utilization_df = generate_allocation_chart_preview(programs_df)

if allocation_chart is not None:
    st.subheader("Program Allocation Chart Preview")
    st.plotly_chart(allocation_chart, use_container_width=True)
    
    # Show utilization summary
    st.subheader("Engineer Utilization Summary")
    
    # Color-code the utilization summary
    def color_utilization(val):
        if val >= 100:
            return 'background-color: #FF9999'  # Red for over-allocated
        elif val >= 80:
            return 'background-color: #FFEB99'  # Yellow for high utilization
        else:
            return 'background-color: #CCFFCC'  # Green for under-utilized
    
    styled_df = utilization_df.style.map(color_utilization, subset=['Effective Total %'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Legend
    st.markdown("""
    **Color Legend:**
    - 🟢 Green: Under-utilized (<80%)
    - 🟡 Yellow: Well-utilized (80-99%)  
    - 🔴 Red: Over-allocated (≥100%)
    """)
else:
    st.info("No allocation data found for chart preview. Add some 'Allocation' or '% Allocated' columns with values > 0.")

# Show Future Projects Timeline
if 'future_projects_df' in st.session_state:
    future_timeline = generate_future_projects_timeline(st.session_state.future_projects_df)
    if future_timeline is not None:
        st.subheader("Future Projects Timeline")
        st.plotly_chart(future_timeline, use_container_width=True)
    else:
        st.info("No future projects data available for timeline. Add projects in the Future Projects Planning section above.")

if st.button("Generate Excel File with Charts", key="export_excel"):
    try:
        excel_file = generate_excel(engineers_df, programs_df)
        st.download_button(
            label="📥 Download Excel File",
            data=excel_file,
            file_name="Engineer_Resource_Allocation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("Excel file generated successfully!")
    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        st.info("This might be due to invalid data. Please check your allocation percentages and try again.")
