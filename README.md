# Team Task Scheduler

A simple app for organizing team member tasks in daily and weekly views.

##  Description

This application allows teams to visually plan their schedules by assigning color-coded tasks to members. Tasks are displayed on an interactive calendar, with support for filtering, drag-and-drop, printing, and member management. Built using Flask and SQLite, it's optimized for use on local, small networks.

## Key Features

- **Daily & Weekly Views**: Switchable layout for flexible task planning
- **Task Blocks**: Tasks are shown as colored blocks by member
- **Task Management**: Add, edit, delete tasks with:
  - date, start time, end time
  - assigned member and notes
- **Member Management**: Add/edit/delete members (with name, team, color)
- **Filtering**: Filter by team or individual member
- **Drag and Drop**: Move tasks interactively on the calendar
- **Print Support**: Clean print layout with time markers and grid lines
- **Automatic Cleanup**: Deletes tasks older than 14 days

## Simple stack used

- **Backend**: Python (Flask), SQLAlchemy, SQLite
- **Frontend**: HTML, CSS (custom styles), JavaScript
- **Other**: Jinja2 templates, local session authentication


---

