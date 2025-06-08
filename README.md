# MS Perfect Resources - Engineer Resource Allocation Tool

A Streamlit-based web application for managing engineer capacity, PTO (Paid Time Off), and monthly feature assignments with automatic utilization calculations.

## Key Concepts & Formulas

### 🧮 Utilization Calculations

#### Effective Allocation Formula
The system automatically adjusts allocations based on PTO:
Effective Allocation % = Total Allocation % × Working Days Ratio
where:
Working Days Ratio = Effective Working Days / Standard Working Days
Effective Working Days = Standard Working Days - PTO Days
Standard Working Days = 22 days per month

#### Available Capacity Formula
Available Capacity % = 100% - Effective Allocation %

#### Example Calculation
- **Engineer assigned**: 50% to Feature A, 30% to Feature B
- **Total allocation**: 80%
- **PTO days in month**: 5 days
- **Calculation**:
  - Effective working days: 22 - 5 = 17 days
  - Working days ratio: 17 ÷ 22 = 0.773 (77.3%)
  - Effective allocation: 80% × 0.773 = 61.8%
  - Available capacity: 100% - 61.8% = 38.2%

### 📊 Allocation Thresholds
- **Available**: Effective allocation < 85%
- **Fully Occupied**: Effective allocation 85% - 100%
- **Over-allocated**: Effective allocation > 100%

## Features

### 👥 Engineer Management
- **Add/Edit/Delete Engineers**: Manage your engineering team roster
- **Quick Add Engineer**: Fast form-based engineer addition
- **Auto-save**: Changes are automatically saved to CSV
- **Data validation**: Automatic cleanup of empty rows and whitespace

### 📅 Monthly PTO Management
- **12-month PTO tracking**: Set PTO days for each engineer by month
- **Annual PTO calculation**: Automatically sums monthly PTO values
- **Quick actions**: Clear all PTO or apply the same value to all months
- **Visual PTO entry**: Easy-to-use grid layout for monthly PTO entry
- **PTO impact on utilization**: Automatically reduces available capacity

### 📊 Monthly Feature Assignments
- **Flexible assignment creation**: Assign engineers to features by month with allocation percentages
- **Multiple view modes**: View assignments by engineer, by month, or all at once
- **Auto-save functionality**: Assignments are saved automatically
- **Real-time utilization updates**: See impact immediately after adding assignments

### 📈 Engineer Utilization Summary
- **Real-time calculations**: Updates automatically with assignments and PTO
- **PTO-adjusted metrics**: Shows both raw and effective allocations
- **Visual status indicators**: Color-coded availability levels
- **Detailed breakdowns**: Monthly pivot tables with color coding
- **Multi-month view**: See utilization trends across 6 months

### 🚀 Future Projects Planning
- **Project timeline visualization**: Gantt-style chart for future projects
- **Priority tracking**: High/Medium/Low priority indicators
- **Resource estimation**: Track estimated engineer count per project
- **Status management**: Planning, On Hold, Active, etc.

### 📥 Export Functionality
- **Excel export**: Generate comprehensive Excel files with all data
- **Multiple sheets**: Engineers, Monthly Assignments, Future Projects
- **Assignment matrix**: Pivot view of assignments by engineer and month

## Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd ms-perfect-resources

Create a virtual environment (recommended)

bashpython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies

bashpip install streamlit pandas xlsxwriter plotly

Optional: Install AgGrid for enhanced editing

bashpip install streamlit-aggrid
Usage

Start the application

bashstreamlit run resource_allocation_app.py

Access the application
Open your browser and navigate to http://localhost:8501

Application Workflow
Getting Started

Add Engineers: Use the "➕ Quick Add Engineer" form to add team members
Set PTO: Navigate to "Monthly PTO Management" tab to set time off for specific months
Create Assignments: Add monthly assignments with allocation percentages
Review Utilization: Check the Engineer Utilization Summary for real-time availability

Best Practices

PTO Before Assignments: Enter PTO data before creating assignments for accurate calculations
Monthly Granularity: Set PTO by month rather than using annual averages
Regular Reviews: Check utilization summary regularly to avoid over-allocation
Name Consistency: Ensure engineer names match exactly between all sections

Data Storage
The application uses CSV files for data persistence:

engineers.csv: Engineer roster, team info, and monthly PTO data
monthly_assignments.csv: Feature assignments with allocation percentages
future_projects.csv: Future project planning and resource estimates

Troubleshooting
Common Issues
Utilization showing 100% availability despite assignments
Solution: Click the "🔧 Fix PTO" button

This adds missing PTO columns for assignment months
Ensures PTO values are numeric
Recalculates annual PTO totals

Data not updating after changes
Solution: Use the "🔄 Refresh" button

Forces reload from CSV files
Updates all calculations
Refreshes the UI

Engineer names not matching
Solution: Check for extra spaces

Names are automatically trimmed of whitespace
Use exact spelling and capitalization
Check the Debug Information expander

Data Integrity

Auto-save: Most operations save automatically
Manual save: Available as backup option
File permissions: Ensure write access to CSV files
Backup: Regularly backup your CSV files

Color Coding Reference
Availability Indicators

🟢 Green (>20%): Good availability
🟡 Yellow (1-20%): Limited availability
🔴 Red (0%): No availability

Allocation Status

🟢 Green (<80%): Normal allocation
🟡 Yellow (80-99%): High allocation
🔴 Red (≥100%): Over-allocated

Advanced Features
Debug Information

Available in "🔍 Debug Information" expander
Shows data types and column mappings
Helps troubleshoot matching issues
Displays PTO column verification

Fix PTO Button

Adds missing PTO columns dynamically
Converts string values to numeric
Recalculates annual totals
Essential for fixing calculation issues

Limitations & Workarounds
LimitationWorkaroundCan't add rows inline in tablesUse "Quick Add Engineer" formExcel export data onlyNo formulas in exportMonthly PTO columns must existUse "Fix PTO" buttonName matching is exactCheck Debug Information
Performance Tips

Keep engineer count under 100 for best performance
Limit assignments to 12 months forward
Use filters in assignment views
Regular cleanup of old data

Version History

v1.0.0 (December 2024): Initial release

Core engineer management
Monthly PTO tracking
Assignment management
Utilization calculations
Export functionality



Support
For issues or feature requests, please contact your team administrator or submit through internal channels.
License
Internal use only - Proprietary
