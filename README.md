# A description NOT written by ChatGPT 🙂:
  I lazily (beri: vibe) coded this for my part-time job, where I would follow the needs of my manager to see a daily and weekly view of their employees. I only implemented the necessary functionalities, keeping the app as simple as possible. After all, the app is meant to ease up a chore of managing employees' time, not waste more of your own (to learn how yet another app works - keep in mind this was made for non-technical staff). 
  This was my first beginner Python project, so the app is nowhere near perfect (ex. security could be heavily improved). 
  It was meant to run on localhost; therefore, I didn't bother with further deployment.

# A description written by ChatGPT 🙂:
# Teams Task Scheduler

A simple app for organising team member tasks in daily and weekly views.

##  Description

This application enables teams to visually plan their schedules by assigning colour-coded tasks to individual members. Tasks are displayed on an interactive calendar, featuring support for filtering, drag-and-drop functionality, printing, and member management. Built using Flask and SQLite, it's optimised for use on local, small networks.

## Key Features

- **Daily & Weekly Views**: Switchable layout for flexible task planning
- **Task Blocks**: Tasks are shown as colored blocks by the member
- **Task Management**: Add, edit, and delete tasks with:
  - date, start time, end time
  - assigned member and notes
- **Member Management**: Add/edit/delete members (with name, team, colour)
- **Filtering**: Filter by team or individual member
- **Drag and Drop**: Move tasks interactively on the calendar
- **Print Support**: Clean print layout with time markers and grid lines
- **Automatic Cleanup**: Deletes tasks older than 14 days

## Simple stack used

- **Backend**: Python (Flask), SQLAlchemy, SQLite
- **Frontend**: HTML, CSS (custom styles), JavaScript
- **Other**: Jinja2 templates, local session authentication


---

