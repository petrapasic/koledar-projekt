from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import and_
from flask_migrate import Migrate
from models import db


app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

migrate = Migrate(app, db)

from models import User, Member, Task

target_metadata = db.metadata



def assign_task_columns(tasks):
    """Groups overlapping tasks into separate columns for one day."""
    task_info = []
    for task in tasks:
        start = int(task.start_time[:2]) * 60 + int(task.start_time[3:])
        end = int(task.end_time[:2]) * 60 + int(task.end_time[3:])
        task_info.append({"task": task, "start_min": start, "end_min": end})

    columns = []
    for t in task_info:
        placed = False
        for col in columns:
            if all(t["start_min"] >= existing["end_min"] or t["end_min"] <= existing["start_min"] for existing in col):
                col.append(t)
                placed = True
                break
        if not placed:
            columns.append([t])
    return columns


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('calendar_view'))
    return redirect(url_for('login'))

def auto_cleanup_old_tasks_for_user(user_id):
    """
    Automatically delete old tasks for a specific user
    """
    if not should_run_cleanup():
        return 0
    
    try:
        cutoff_date = datetime.now().date() - timedelta(days=CLEANUP_DAYS_OLD)
        
        # Filter by both date and user_id
        old_tasks = Task.query.filter(
            Task.date < cutoff_date,
            Task.user_id == user_id
        ).all()
        
        deleted_count = len(old_tasks)
        
        if old_tasks:
            for task in old_tasks:
                db.session.delete(task)
            
            db.session.commit()
            print(f"[AUTO-CLEANUP] User {user_id}: Deleted {deleted_count} tasks older than {CLEANUP_DAYS_OLD} days")
        
        record_cleanup_time()
        return deleted_count
        
    except Exception as e:
        print(f"[AUTO-CLEANUP ERROR] User {user_id}: {str(e)}")
        db.session.rollback()
        return 0

def auto_cleanup_old_tasks_all_users():
    """
    Run cleanup for all users (can be called from a scheduled job)
    """
    if not should_run_cleanup():
        return {}
    
    try:
        # Get all users
        users = User.query.all()
        cleanup_results = {}
        
        cutoff_date = datetime.now().date() - timedelta(days=CLEANUP_DAYS_OLD)
        
        for user in users:
            old_tasks = Task.query.filter(
                Task.date < cutoff_date,
                Task.user_id == user.id
            ).all()
            
            deleted_count = len(old_tasks)
            
            if old_tasks:
                for task in old_tasks:
                    db.session.delete(task)
                
                cleanup_results[user.id] = {
                    'username': user.username,
                    'deleted_count': deleted_count
                }
        
        db.session.commit()
        record_cleanup_time()
        
        if cleanup_results:
            print(f"[AUTO-CLEANUP] Cleaned up tasks for {len(cleanup_results)} users")
            for user_id, result in cleanup_results.items():
                print(f"  User '{result['username']}': {result['deleted_count']} tasks deleted")
        
        return cleanup_results
        
    except Exception as e:
        print(f"[AUTO-CLEANUP ERROR] Global cleanup failed: {str(e)}")
        db.session.rollback()
        return {}
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('calendar_view'))
        return 'Napačno uporabniško ime ali geslo'
    
    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return 'Uporabniško ime že obstaja. Izberite drugo.'

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/calendar')
def calendar_view():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    auto_cleanup_old_tasks_for_user(current_user_id)  # Updated cleanup function
    
    # Get current user info
    current_user = User.query.get(current_user_id)
    
    view_type = request.args.get('view', 'daily')
    date_str = request.args.get('date')
    selected_team = request.args.get('team')
    selected_team = selected_team if selected_team and selected_team.lower() != 'none' else ''

    selected_member = request.args.get('member')
    selected_member = selected_member if selected_member and selected_member.lower() != 'none' else ''


    try:
        current_date = datetime.strptime(request.args.get('date', ''), '%Y-%m-%d')
    except (ValueError, TypeError):
        current_date = datetime.today()

    
    # Filter members by current user only
    is_admin = current_user and current_user.username == 'admin'
    members = Member.query.all() if is_admin else Member.query.filter_by(user_id=current_user_id).all()
    unique_teams = sorted(set(member.team for member in members if member.team))
    unique_members = sorted(set(member.name for member in members))

    # Create members_by_team dictionary for template
    members_by_team = {}
    for member in members:
        if member.team:
            if member.team not in members_by_team:
                members_by_team[member.team] = []
            members_by_team[member.team].append(member)

    # Apply filters to get filtered members
    filtered_members = members
    
    if selected_team:
        filtered_members = [m for m in filtered_members if m.team == selected_team]
    
    if selected_member:
        filtered_members = [m for m in filtered_members if m.name == selected_member]

    labels = [member.name for member in filtered_members]
    member_colors = {member.name: member.color or '#6366f1' for member in filtered_members}

    # Initialize variables
    tasks_by_member = {label: [] for label in labels}
    day_tasks = {}

    # Calculate navigation dates and display text
    if view_type == 'weekly':
        monday = current_date - timedelta(days=current_date.weekday())
        sunday = monday + timedelta(days=6)
        
        if monday.month == sunday.month:
            display_text = f"{monday.day}.-{sunday.day}. {monday.month}. {monday.year}"
        elif monday.year == sunday.year:
            display_text = f"{monday.day}.{monday.month}.-{sunday.day}.{sunday.month}. {monday.year}"
        else:
            display_text = f"{monday.day}.{monday.month}.{monday.year}-{sunday.day}.{sunday.month}.{sunday.year}"
        
        prev_date = (monday - timedelta(days=7)).strftime('%Y-%m-%d')
        next_date = (monday + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Create day_tasks for weekly view - filter by user
        for i in range(7):
            day = (monday + timedelta(days=i)).date()
            day_tasks[day] = []
            
            # Get tasks for this specific day and user
            if is_admin:
                daily_tasks = Task.query.filter(Task.date == day).all()
            else:
                daily_tasks = Task.query.filter(
                    Task.date == day,
                    Task.user_id == current_user_id
                ).all()

            
            # Apply filters
            for task in daily_tasks:
                if selected_team and (not task.member or task.member.team != selected_team):
                    continue
                
                if selected_member and (not task.member or task.member.name != selected_member):
                    continue
                
                day_tasks[day].append(task)
                
    else:
        # Daily view
        display_text = current_date.strftime('%d. %m. %Y')
        prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_date = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Filter tasks for the current date and user
        if is_admin:
            tasks = Task.query.filter(Task.date == current_date.date()).all()
        else:
            tasks = Task.query.filter(
                Task.date == current_date.date(),
                Task.user_id == current_user_id
            ).all()

        
        # Apply team filter if selected
        if selected_team:
            tasks = [t for t in tasks if t.member and t.member.team == selected_team]
        
        # Apply member filter if selected
        if selected_member:
            tasks = [t for t in tasks if t.member and t.member.name == selected_member]
        
        # Group tasks by member for daily view
        for task in tasks:
            if task.member and task.member.name in tasks_by_member:
                tasks_by_member[task.member.name].append(task)
    
    return render_template(
        'calendar.html',
        view_type=view_type,
        current_date=current_date,
        display_text=display_text,
        prev_date=prev_date,
        next_date=next_date,
        labels=labels,
        member_colors=member_colors,
        tasks_by_member=tasks_by_member,
        day_tasks=day_tasks,
        unique_teams=unique_teams,
        unique_members=unique_members,
        selected_team=selected_team,
        selected_member=selected_member,
        members_by_team=members_by_team,
        timedelta=timedelta,
        current_user=current_user
    )


@app.route('/manage-members', methods=['GET', 'POST'])
def manage_members():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form['name']
        team = request.form['team']
        color = request.form['color']
        
        # Associate member with current user
        new_member = Member(name=name, team=team, color=color, user_id=current_user_id)
        db.session.add(new_member)
        db.session.commit()
        return redirect(url_for('manage_members'))

    # Show only current user's members
    members = Member.query.filter_by(user_id=current_user_id).all()
    return render_template('manage_members.html', members=members)

@app.route('/delete-member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    
    # Only allow deletion of user's own members
    member = Member.query.filter_by(id=member_id, user_id=current_user_id).first()
    if member:
        # Delete associated tasks first
        Task.query.filter_by(member_id=member.id, user_id=current_user_id).delete()
        db.session.delete(member)
        db.session.commit()
    return redirect(url_for('manage_members'))


@app.route('/add-task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    
    # Show only current user's members
    members = Member.query.filter_by(user_id=current_user_id).all()
    
    if request.method == 'POST':
        name = request.form['name']
        date_str = request.form['date']
        start = request.form['start']
        end = request.form['end']
        member_id = request.form['member_id']
        notes = request.form.get('notes', '')


        # Verify member belongs to current user
        member = Member.query.filter_by(id=member_id, user_id=current_user_id).first()
        if not member:
            return "Invalid member selection", 400

        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Associate task with current user
        task = Task(
            name=name, 
            date=date, 
            start_time=start, 
            end_time=end, 
            member_id=member_id,
            user_id=current_user_id,
            notes=notes
        )
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('calendar_view'))

    return render_template('add_task.html', members=members)

@app.route('/delete-task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
    if task:
        db.session.delete(task)
        db.session.commit()

    # Preverimo, od kod prihajamo
    from_page = request.form.get('from_page')

    if from_page == 'manage_tasks':
        return redirect(url_for('manage_tasks'))
    else:
        # Vrni na koledar s potrebnimi parametri (poskrbimo za varne default vrednosti)
        view = request.form.get('view', 'daily')
        date = request.form.get('date') or datetime.today().strftime('%Y-%m-%d')
        team = request.form.get('team') or ''
        member = request.form.get('member') or ''
        return redirect(url_for('calendar_view', view=view, date=date, team=team, member=member))


@app.route('/edit-task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    
    # Only allow editing of user's own tasks
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first_or_404()
    members = Member.query.filter_by(user_id=current_user_id).all()
    from_page = request.args.get('from_page')

    if request.method == 'POST':
        member_id = request.form['member_id']
        
        # Verify member belongs to current user
        member = Member.query.filter_by(id=member_id, user_id=current_user_id).first()
        if not member:
            return "Invalid member selection", 400
        
        
        
        task.name = request.form['name']
        date_str = request.form.get('date')
        if not date_str:
            return "Datum ni podan.", 400

        try:
            task.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return f"Neveljaven datum: {date_str}", 400

        task.start_time = request.form['start']
        task.end_time = request.form['end']
        task.member_id = member_id
        task.notes = request.form.get('notes', '')
        
        db.session.commit()

        if request.form.get('from_page') == 'manage_tasks' or from_page == 'manage_tasks':
            return redirect(url_for('manage_tasks'))

        return redirect(url_for(
            'calendar_view',
            view=request.form.get('view', 'daily'),
            date=request.form.get('date'),
            team=request.form.get('team'),
            member=request.form.get('member')
        ))


    return render_template('edit_task.html', task=task, members=members)

@app.route('/manage-tasks', methods=['GET'])
def manage_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session['user_id']
    
    date_filter = request.args.get('date')
    if date_filter:
        tasks = Task.query.filter_by(
            date=date_filter, 
            user_id=current_user_id
        ).order_by(Task.start_time).all()
    else:
        tasks = Task.query.filter_by(
            user_id=current_user_id
        ).order_by(Task.date, Task.start_time).all()
    
    return render_template('manage_tasks.html', tasks=tasks, selected_date=date_filter)

@app.route('/update-task-position', methods=['POST'])
def update_task_position():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Niste prijavljeni'}), 401
    
    current_user_id = session['user_id']
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Podatki niso podani'}), 400
        
        task_id = data.get('task_id')
        new_date = data.get('new_date')
        new_start_time = data.get('new_start_time')
        new_end_time = data.get('new_end_time')
        new_member_name = data.get('new_member_name')
        
        if not all([task_id, new_date, new_start_time, new_end_time]):
            return jsonify({'success': False, 'error': 'Manjkajo obvezna polja'}), 400
        
        # Only allow updating user's own tasks
        task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
        if not task:
            return jsonify({'success': False, 'error': 'Naloga ni najdena'}), 404
        
        # Update task fields
        task.date = datetime.strptime(new_date, '%Y-%m-%d').date()
        task.start_time = new_start_time
        task.end_time = new_end_time
        
        # Update member if provided
        if new_member_name and new_member_name != task.member.name:
            member = Member.query.filter_by(
                name=new_member_name, 
                user_id=current_user_id
            ).first()
            if member:
                task.member_id = member.id
            else:
                return jsonify({'success': False, 'error': f'Član "{new_member_name}" ni najden'}), 404
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Naloga je bila uspešno posodobljena',
            'task': {
                'id': task.id,
                'name': task.name,
                'date': task.date.strftime('%Y-%m-%d'),
                'start_time': task.start_time,
                'end_time': task.end_time,
                'member_id': task.member_id
            }
        })
        


    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/edit-member/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    member = Member.query.filter_by(id=member_id, user_id=current_user_id).first_or_404()

    if request.method == 'POST':
        member.name = request.form['name']
        member.team = request.form['team']
        member.color = request.form['color']
        db.session.commit()
        return redirect(url_for('manage_members'))

    return render_template('edit_member.html', member=member)

 

# Cleanup interval in hours
CLEANUP_INTERVAL_HOURS = 12
CLEANUP_DAYS_OLD = 14  # How old tasks must be to be deleted

_last_cleanup_time = None

def should_run_cleanup():
    global _last_cleanup_time
    now = datetime.now()
    if not _last_cleanup_time:
        _last_cleanup_time = now
        return True
    elapsed = (now - _last_cleanup_time).total_seconds() / 3600
    return elapsed >= CLEANUP_INTERVAL_HOURS

def record_cleanup_time():
    global _last_cleanup_time
    _last_cleanup_time = datetime.now()




    
if __name__ == '__main__':
    from models import db
    
    app.run(host="0.0.0.0", port=5000, debug=False)

#    app.run(host="0.0.0.0", port=5000, debug=False)
