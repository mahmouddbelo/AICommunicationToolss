from flask import render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, EmailDraft, Report, ChatSession, ChatMessage, UserPreference, AutoReply
from ai_services import AIService
import logging

# Initialize AI service
ai_service = AIService()



@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/auto-reply')
@login_required
def auto_replies():
    replies = AutoReply.query.filter_by(user_id=current_user.id).order_by(AutoReply.created_at.desc()).all()
    return render_template('auto_replies.html', replies=replies)

@app.route('/auto-reply/new', methods=['GET', 'POST'])
@login_required
def new_auto_reply():
    if request.method == 'POST':
        message = request.form.get('message')
        context = request.form.get('context', '')
        
        if not message:
            flash('Please provide the message you want to reply to', 'danger')
            return redirect(url_for('new_auto_reply'))
        
        # Get user preferences
        preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
        
        # Generate auto-reply using AI
        try:
            reply = ai_service.generate_auto_reply(
                incoming_message=message,
                context=context,
                preferences=preferences
            )
            
            # Create new auto-reply record
            auto_reply = AutoReply(
                original_message=message,
                reply_subject=reply['subject'],
                reply_content=reply['body'],
                context=context,
                user_id=current_user.id
            )
            
            db.session.add(auto_reply)
            db.session.commit()
            
            flash('Auto-reply generated successfully!', 'success')
            return render_template('auto_replies.html', 
                                 new_reply=True,
                                 generated_reply=reply,
                                 original_message=message)
        except Exception as e:
            logging.error(f"Error generating auto-reply: {str(e)}")
            flash(f'Error generating auto-reply: {str(e)}', 'danger')
            return redirect(url_for('new_auto_reply'))
    
    return render_template('auto_replies.html', new_reply=True)

@app.route('/auto-reply/<int:reply_id>')
@login_required
def view_auto_reply(reply_id):
    reply = AutoReply.query.get_or_404(reply_id)
    
    # Check if the reply belongs to the current user
    if reply.user_id != current_user.id:
        flash('You do not have permission to view this reply', 'danger')
        return redirect(url_for('auto_replies'))
    
    return render_template('auto_replies.html', selected_reply=reply)

@app.route('/auto-reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_auto_reply(reply_id):
    reply = AutoReply.query.get_or_404(reply_id)
    
    # Check if the reply belongs to the current user
    if reply.user_id != current_user.id:
        flash('You do not have permission to delete this reply', 'danger')
        return redirect(url_for('auto_replies'))
    
    db.session.delete(reply)
    db.session.commit()
    
    flash('Auto-reply deleted successfully', 'success')
    return redirect(url_for('auto_replies'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        # Create default preferences
        preferences = UserPreference(user=user)
        
        db.session.add(user)
        db.session.add(preferences)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get counts for each type of content
    email_count = EmailDraft.query.filter_by(user_id=current_user.id).count()
    report_count = Report.query.filter_by(user_id=current_user.id).count()
    chat_count = ChatSession.query.filter_by(user_id=current_user.id).count()
    
    # Get recent items
    recent_emails = EmailDraft.query.filter_by(user_id=current_user.id).order_by(EmailDraft.created_at.desc()).limit(3).all()
    recent_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(3).all()
    recent_chats = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).limit(3).all()
    
    from models import ChatMessage
    
    return render_template(
        'dashboard.html',
        email_count=email_count,
        report_count=report_count,
        chat_count=chat_count,
        recent_emails=recent_emails,
        recent_reports=recent_reports,
        recent_chats=recent_chats,
        ChatMessage=ChatMessage
    )

# Email routes
@app.route('/emails')
@login_required
def email_drafts():
    emails = EmailDraft.query.filter_by(user_id=current_user.id).order_by(EmailDraft.created_at.desc()).all()
    return render_template('email_drafts.html', emails=emails)

@app.route('/emails/new', methods=['GET', 'POST'])
@login_required
def new_email():
    if request.method == 'POST':
        context = request.form.get('context')
        
        if not context:
            flash('Please provide context for generating the email', 'danger')
            return redirect(url_for('new_email'))
        
        # Get user preferences
        preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
        
        # Generate email using AI
        try:
            email_content = ai_service.generate_email(context, preferences)
            
            # Create new email draft
            email = EmailDraft(
                subject=email_content['subject'],
                content=email_content['body'],
                user_id=current_user.id
            )
            
            db.session.add(email)
            db.session.commit()
            
            flash('Email draft generated successfully!', 'success')
            return redirect(url_for('email_drafts'))
        except Exception as e:
            logging.error(f"Error generating email: {str(e)}")
            flash(f'Error generating email: {str(e)}', 'danger')
            return redirect(url_for('new_email'))
    
    return render_template('email_drafts.html', new_email=True)

@app.route('/emails/<int:email_id>')
@login_required
def view_email(email_id):
    email = EmailDraft.query.get_or_404(email_id)
    
    # Check if the email belongs to the current user
    if email.user_id != current_user.id:
        flash('You do not have permission to view this email', 'danger')
        return redirect(url_for('email_drafts'))
    
    return render_template('email_drafts.html', selected_email=email)

@app.route('/emails/<int:email_id>/delete', methods=['POST'])
@login_required
def delete_email(email_id):
    email = EmailDraft.query.get_or_404(email_id)
    
    # Check if the email belongs to the current user
    if email.user_id != current_user.id:
        flash('You do not have permission to delete this email', 'danger')
        return redirect(url_for('email_drafts'))
    
    db.session.delete(email)
    db.session.commit()
    
    flash('Email draft deleted successfully', 'success')
    return redirect(url_for('email_drafts'))

# Report routes
@app.route('/reports')
@login_required
def reports():
    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('reports.html', reports=user_reports)

@app.route('/reports/new', methods=['GET', 'POST'])
@login_required
def new_report():
    if request.method == 'POST':
        context = request.form.get('context')
        report_type = request.form.get('report_type')
        
        if not context or not report_type:
            flash('Please provide all required information', 'danger')
            return redirect(url_for('new_report'))
        
        # Get user preferences
        preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
        
        # Generate report using AI
        try:
            report_content = ai_service.generate_report(context, report_type, preferences)
            
            # Create new report
            report = Report(
                title=report_content['title'],
                content=report_content['content'],
                report_type=report_type,
                source_data=context,
                user_id=current_user.id
            )
            
            db.session.add(report)
            db.session.commit()
            
            flash('Report generated successfully!', 'success')
            return redirect(url_for('reports'))
        except Exception as e:
            logging.error(f"Error generating report: {str(e)}")
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(url_for('new_report'))
    
    return render_template('reports.html', new_report=True)

@app.route('/reports/<int:report_id>')
@login_required
def view_report(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Check if the report belongs to the current user
    if report.user_id != current_user.id:
        flash('You do not have permission to view this report', 'danger')
        return redirect(url_for('reports'))
    
    return render_template('reports.html', selected_report=report)

@app.route('/reports/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Check if the report belongs to the current user
    if report.user_id != current_user.id:
        flash('You do not have permission to delete this report', 'danger')
        return redirect(url_for('reports'))
    
    db.session.delete(report)
    db.session.commit()
    
    flash('Report deleted successfully', 'success')
    return redirect(url_for('reports'))

# Chatbot routes
@app.route('/chatbot')
@login_required
def chatbot():
    chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    return render_template('chatbot.html', chat_sessions=chat_sessions)

@app.route('/chatbot/new', methods=['POST'])
@login_required
def new_chat():
    title = request.form.get('title', 'New Chat')
    
    chat_session = ChatSession(
        title=title,
        user_id=current_user.id
    )
    
    db.session.add(chat_session)
    db.session.commit()
    
    return redirect(url_for('view_chat', chat_id=chat_session.id))

@app.route('/chatbot/<int:chat_id>')
@login_required
def view_chat(chat_id):
    chat_session = ChatSession.query.get_or_404(chat_id)
    
    # Check if the chat session belongs to the current user
    if chat_session.user_id != current_user.id:
        flash('You do not have permission to view this chat', 'danger')
        return redirect(url_for('chatbot'))
    
    messages = ChatMessage.query.filter_by(session_id=chat_id).order_by(ChatMessage.timestamp.asc()).all()
    chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    
    return render_template('chatbot.html', chat_sessions=chat_sessions, current_chat=chat_session, messages=messages)

@app.route('/chatbot/<int:chat_id>/send', methods=['POST'])
@login_required
def send_message(chat_id):
    chat_session = ChatSession.query.get_or_404(chat_id)
    
    # Check if the chat session belongs to the current user
    if chat_session.user_id != current_user.id:
        return jsonify({'error': 'You do not have permission to access this chat'}), 403
    
    message_content = request.form.get('message')
    
    if not message_content:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Create new user message
    user_message = ChatMessage(
        content=message_content,
        is_user=True,
        session_id=chat_id
    )
    
    db.session.add(user_message)
    db.session.commit()
    
    # Get chat history
    messages = ChatMessage.query.filter_by(session_id=chat_id).order_by(ChatMessage.timestamp.asc()).all()
    chat_history = [{'content': msg.content, 'is_user': msg.is_user} for msg in messages]
    
    # Get user preferences
    preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
    
    # Generate AI response
    try:
        response_content = ai_service.chatbot_response(message_content, chat_history, preferences)
        
        # Create AI response message
        ai_message = ChatMessage(
            content=response_content,
            is_user=False,
            session_id=chat_id
        )
        
        db.session.add(ai_message)
        db.session.commit()
        
        return jsonify({
            'user_message': {
                'id': user_message.id,
                'content': user_message.content,
                'is_user': True,
                'timestamp': user_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            },
            'ai_message': {
                'id': ai_message.id,
                'content': ai_message.content,
                'is_user': False,
                'timestamp': ai_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logging.error(f"Error generating chatbot response: {str(e)}")
        return jsonify({'error': f'Error generating response: {str(e)}'}), 500

@app.route('/chatbot/<int:chat_id>/delete', methods=['POST'])
@login_required
def delete_chat(chat_id):
    chat_session = ChatSession.query.get_or_404(chat_id)
    
    # Check if the chat session belongs to the current user
    if chat_session.user_id != current_user.id:
        flash('You do not have permission to delete this chat', 'danger')
        return redirect(url_for('chatbot'))
    
    # Delete all messages in the chat
    ChatMessage.query.filter_by(session_id=chat_id).delete()
    
    # Delete the chat session
    db.session.delete(chat_session)
    db.session.commit()
    
    flash('Chat deleted successfully', 'success')
    return redirect(url_for('chatbot'))

# User preferences routes
@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    user_preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
    
    if not user_preferences:
        user_preferences = UserPreference(user_id=current_user.id)
        db.session.add(user_preferences)
        db.session.commit()
    
    if request.method == 'POST':
        # Update email preferences
        user_preferences.email_tone = request.form.get('email_tone', 'professional')
        user_preferences.email_length = request.form.get('email_length', 'medium')
        user_preferences.email_signature = request.form.get('email_signature', '')
        
        # Update report preferences
        user_preferences.report_format = request.form.get('report_format', 'detailed')
        user_preferences.report_tone = request.form.get('report_tone', 'formal')
        
        # Update chat preferences
        user_preferences.chat_tone = request.form.get('chat_tone', 'helpful')
        
        db.session.commit()
        
        flash('Preferences updated successfully', 'success')
        return redirect(url_for('preferences'))
    
    return render_template('preferences.html', preferences=user_preferences)
