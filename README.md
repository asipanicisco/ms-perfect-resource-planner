# MS Perfect Resources - Engineering Resource Management Tool

A comprehensive Streamlit-based application for managing engineering team resources, tracking monthly feature assignments, and visualizing engineer availability over time.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Key Calculations](#key-calculations)
- [Data Persistence](#data-persistence)
- [Excel Export](#excel-export)
- [Troubleshooting](#troubleshooting)

## Overview

MS Perfect Resources is designed to help engineering managers and project coordinators:
- Track engineer capacity and PTO days
- Assign engineers to features on a monthly basis
- Visualize utilization and availability trends
- Plan future projects with resource requirements
- Export comprehensive reports to Excel

## Features

### 1. **Engineer Management**
- Add, edit, and manage engineer information
- Track team assignments, roles, and weekly hours
- Record annual PTO days for capacity planning
- Rename columns for customization
- Inline editing with AgGrid support (optional)

### 2. **Monthly Feature Assignments**
- Assign engineers to specific features by month
- Set allocation percentages for each assignment
- Add notes for context
- View assignments grouped by engineer
- Easy deletion of assignments

### 3. **Engineer Utilization Timeline**
The application provides a powerful dual-chart visualization:

#### Top Chart: Utilization Trends
- Shows each engineer's utilization percentage over time
- Includes PTO-adjusted calculations
- Visual thresholds at 95% (fully occupied) and 100% (over-allocated)
- Interactive hover details showing assigned features

#### Bottom Chart: Available Capacity
- Bar chart showing remaining capacity per engineer per month
- Color-coded by month for easy comparison
- Displays PTO impact on availability

### 4. **Availability Analysis**
- **Summary Table**: Shows current and average utilization
- **Detailed Breakdown**: Monthly availability matrix with color coding
- **Status Tracking**: Identifies when engineers become fully occupied

### 5. **Future Projects Planning**
- Track upcoming projects with timelines
- Estimate required engineer count
- Set priority levels and status
- Visualize project timelines in Gantt-style chart

### 6. **Excel Export**
Generate comprehensive Excel files containing:
- Engineer capacity data
- Monthly assignments
- Pivot tables for analysis
- Future projects planning
- All data formatted for easy reporting

## Installation

### Prerequisites
```bash
pip install streamlit
pip install pandas
pip install xlsxwriter
pip install plotly
```

### Optional (for enhanced editing)
```bash
pip install streamlit-aggrid
```

### Running the Application
```bash
streamlit run resource_management.py
```

## Usage Guide

### Getting Started

1. **Add Engineers**
   - Click "➕ Add Engineer Row" 
   - Fill in engineer details (Name, Team, Role, PTO Days)
   - Click "💾 Save Engineer Changes"

2. **Create Monthly Assignments**
   - Select an engineer from the dropdown
   - Enter the feature name
   - Choose the month (YYYY-MM format)
   - Set allocation percentage (0-100%)
   - Add optional notes
   - Click "➕ Add Monthly Assignment"

3. **View Utilization**
   - The timeline chart automatically updates
   - Check the availability summary table
   - Expand "Detailed Monthly Availability Breakdown" for matrices

### Understanding the Charts

#### Utilization Chart (Top)
- **Line Plot**: Shows utilization trends for each engineer
- **Red Dashed Line**: 100% capacity (over-allocated)
- **Orange Dashed Line**: 95% capacity (fully occupied)
- **Hover Details**: Shows features assigned and working days

#### Availability Chart (Bottom)
- **Bar Chart**: Remaining capacity by engineer and month
- **Colors**: Different colors represent different months
- **Values**: Percentage of available capacity

### Color Coding

#### Availability Colors
- 🟢 **Green**: Good availability (>20%)
- 🟡 **Yellow**: Low availability (1-20%)
- 🔴 **Red**: No availability (0%) or over-allocated

#### Status Colors
- 🟢 **Green**: Engineer has availability
- 🟡 **Yellow**: Engineer is fully occupied
- 🔴 **Red**: Engineer is over-allocated

## Key Calculations

### PTO Distribution
- Annual PTO days are distributed evenly across 12 months
- Monthly PTO = Annual PTO ÷ 12
- Assumes 22 working days per month

### Effective Allocation
```
Working Days Ratio = (22 - Monthly PTO Days) / 22
Effective Allocation = Total Assignment % × Working Days Ratio
Available Capacity = 100% - Effective Allocation
```

### Example
- Engineer has 24 annual PTO days
- Monthly PTO = 24 ÷ 12 = 2 days
- Working days = 22 - 2 = 20 days
- Working ratio = 20/22 = 90.9%
- If assigned 80% to a feature:
  - Effective allocation = 80% × 90.9% = 72.7%
  - Available capacity = 100% - 72.7% = 27.3%

### Thresholds
- **95%**: Considered "Fully Occupied" (5% buffer for meetings, etc.)
- **100%**: Over-allocated threshold

## Data Persistence

The application saves data to CSV files:
- `engineers.csv`: Engineer information
- `monthly_assignments.csv`: Feature assignments
- `future_projects.csv`: Future project data

Data is automatically saved when you click the respective save buttons.

## Excel Export

The exported Excel file includes:
1. **Engineer Capacity**: All engineer data with PTO days
2. **Monthly Assignments**: Detailed assignment list
3. **Monthly Assignment Matrix**: Pivot table view
4. **Future Projects**: Project planning data

### Using the Excel Export
1. Click "Generate Excel File with All Data"
2. Click "📥 Download Excel File"
3. Open in Excel for further analysis
4. Use pivot tables for custom reports

## Troubleshooting

### Common Issues

1. **"No engineers found" message**
   - Add at least one engineer in the Engineer Management section
   - Save the engineer data

2. **Charts not updating**
   - Ensure you've saved your changes
   - Check that allocation percentages are numeric
   - Refresh the page if needed

3. **AgGrid not working**
   - Install with: `pip install streamlit-aggrid`
   - The app will fall back to standard editors if not installed

4. **Excel export failing**
   - Check for invalid data (non-numeric allocations)
   - Ensure all required fields are filled
   - Try saving all sections before exporting

### Best Practices

1. **Regular Saves**: Save data in each section regularly
2. **PTO Planning**: Update PTO days at the start of the year
3. **Monthly Reviews**: Review and update assignments monthly
4. **Allocation Limits**: Aim to keep engineers below 95% allocation
5. **Buffer Time**: Leave 5-10% capacity for unexpected work

## Advanced Features

### Custom Column Names
- Use the "Rename Columns" expanders to customize field names
- Changes are saved to maintain consistency

### Bulk Operations
- Export to Excel for bulk updates
- Import updated CSV files by replacing the saved files

### Integration Ideas
- Connect to HR systems for automatic PTO updates
- Integrate with project management tools
- Set up automated reports via scheduled runs

## Support

For issues or feature requests, please contact your IT administrator or the development team.
To run the tool use: nohup streamlit run resource_allocation_app.py --server.port 8000 > streamlit.log 2>&1 &
---

*MS Perfect Resources - Making resource management perfect for your team*
