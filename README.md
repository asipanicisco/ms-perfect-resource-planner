# MS Perfect Resources - Engineer Resource Allocation Tool

A Streamlit-based web application for managing engineer capacity, PTO (Paid Time Off), and monthly feature assignments. This tool helps teams track engineer availability and resource allocation across multiple months.

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

### 📊 Monthly Feature Assignments
- **Flexible assignment creation**: Assign engineers to features by month with allocation percentages
- **Multiple view modes**: View assignments by engineer, by month, or all at once
- **Auto-save functionality**: Assignments are saved automatically
- **Delete assignments**: Easy removal of incorrect assignments

### 📈 Engineer Utilization Summary
- **Real-time utilization calculation**: See current and average monthly availability
- **PTO-adjusted calculations**: Automatically accounts for PTO when calculating effective allocation
- **Visual indicators**: Color-coded status (Available, Fully Occupied, Over-allocated)
- **Detailed breakdowns**: Monthly availability and allocation percentages in pivot tables
- **85% threshold**: Engineers are considered fully occupied at 85% allocation

### 🚀 Future Projects Planning
- **Project timeline visualization**: Gantt-style chart for future projects
- **Priority tracking**: High/Medium/Low priority indicators
- **Resource estimation**: Track estimated engineer count per project

### 📥 Export Functionality
- **Excel export**: Generate comprehensive Excel files with all data
- **Multiple sheets**: Separate sheets for engineers, assignments, and projects

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
Set PTO: Navigate to "Monthly PTO Management" tab to set time off
Create Assignments: Add monthly assignments with allocation percentages
Review Utilization: Check the Engineer Utilization Summary for availability

Key Concepts

Allocation %: Percentage of an engineer's time allocated to a feature
Effective Allocation: Allocation adjusted for PTO days
Working Days: Standard 22 working days per month minus PTO
Availability Threshold: 85% - engineers are considered fully occupied above this

Tips for Best Use

Name Consistency: Ensure engineer names match exactly between sections
PTO Entry: Enter PTO before creating assignments for accurate calculations
Fix PTO Button: Use if utilization isn't calculating correctly
Refresh Button: Force reload data if updates aren't showing

Data Storage
The application uses CSV files for data persistence:

engineers.csv: Engineer roster and PTO data
monthly_assignments.csv: Feature assignments by month
future_projects.csv: Future project planning data

Troubleshooting
Utilization showing 100% availability despite assignments

Click the "🔧 Fix PTO" button to ensure PTO columns exist for assignment months
Check that engineer names match exactly (no extra spaces)
Use the "🔄 Refresh" button to reload data

Data not saving

The application auto-saves on most actions
Use the manual "💾 Save" buttons as backup
Check file permissions in the application directory

Adding rows causes data loss

Use the "➕ Quick Add Engineer" form instead of inline table editing
This is a known Streamlit limitation with dynamic row addition

Color Coding
Availability Colors

🟢 Green: Good availability (>20%)
🟡 Yellow: Low availability (1-20%)
🔴 Red: No availability (0%)

Status Indicators

Available: Under 85% allocation
Fully Occupied: 85-100% allocation
Over-allocated: Above 100% allocation

Known Limitations

Dynamic row editing: Adding rows directly in tables may cause issues
Browser storage: localStorage/sessionStorage not supported in artifacts
Excel formulas: Export includes data only, no formulas

Support
For issues or feature requests, please contact your team administrator or submit a ticket through your internal support system.
Version
Current Version: 1.0.0
Last Updated: December 2024
