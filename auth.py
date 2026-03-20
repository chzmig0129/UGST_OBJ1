"""
Authentication Blueprint.

Provides /auth/login, /auth/register, and /auth/logout routes.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Show login form and authenticate the user."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Por favor ingresa tu usuario y contraseña.', 'error')
            return render_template('auth/login.html')

        # Import User here to avoid circular imports at module load time.
        from app import User  # noqa: PLC0415
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'error')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
            return render_template('auth/login.html')

        login_user(user)
        flash(f'Bienvenido, {user.username}!', 'success')

        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Show registration form and create a new user."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validation
        if not username or not email or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('auth/register.html')

        from app import User, db  # noqa: PLC0415

        # Check for existing username or email
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'error')
            return render_template('auth/register.html')

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Cuenta creada exitosamente. Por favor inicia sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))
