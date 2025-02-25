from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Expense
from config import Config
from datetime import datetime, timedelta
from urllib.parse import quote
import io
import csv

app = Flask(__name__)
app.config.from_object(Config)

# 初始化数据库和登录管理
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(username, password)
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(username, password)
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    date_str = request.form.get('datetime')  # 获取日期时间字符串
    date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')  # 转换为 datetime 对象
    category = request.form.get('category')
    amount = float(request.form.get('amount'))
    expense = Expense(user_id=current_user.id, date=date, category=category, amount=amount)
    db.session.add(expense)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/statistics')
@login_required
def statistics():
    # 获取用户选择的时间范围
    selected_period = request.args.get('period', 'day')  # 默认为今天
    today = datetime.now().date()

    # 根据选择的时间范围计算开始日期
    if selected_period == 'day':
        start_date = today
        selected_period_label = '今天'
    elif selected_period == '7days':
        start_date = today - timedelta(days=7)
        selected_period_label = '最近七天'
    elif selected_period == 'week':
        start_date = today - timedelta(days=today.weekday())
        selected_period_label = '本周'
    elif selected_period == 'month':
        start_date = today.replace(day=1)
        selected_period_label = '本月'
    elif selected_period == '30days':
        start_date = today - timedelta(days=30)
        selected_period_label = '最近三十天'
    elif selected_period == 'year':
        start_date = today.replace(year=today.year - 1)
        selected_period_label = '最近一年'
    else:
        start_date = today
        selected_period_label = '今天'

    # 查询消费记录
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= today
    ).all()

    # 计算总消费和各类别消费
    total_expenses = sum(expense.amount for expense in expenses)
    categories = {}
    for expense in expenses:
        if expense.category not in categories:
            categories[expense.category] = 0
        categories[expense.category] += expense.amount

    # 根据时间范围生成主图表数据
    if selected_period == 'day':
        main_labels = list(categories.keys())
        main_data = list(categories.values())
    else:
        # 按天/周/月分组
        date_format = '%Y-%m-%d' if selected_period in ['7days', '30days'] else '%Y-%m' if selected_period == 'year' else '%Y-%m-%d'
        grouped_expenses = {}
        for expense in expenses:
            key = expense.date.strftime(date_format)
            if key not in grouped_expenses:
                grouped_expenses[key] = 0
            grouped_expenses[key] += expense.amount
        main_labels = list(grouped_expenses.keys())
        main_data = list(grouped_expenses.values())

    # 饼状图数据
    pie_labels = list(categories.keys())
    pie_data = list(categories.values())

    return render_template('statistics.html', 
                         selected_period=selected_period,
                         selected_period_label=selected_period_label,
                         total_expenses=total_expenses,
                         main_labels=main_labels,
                         main_data=main_data,
                         pie_labels=pie_labels,
                         pie_data=pie_data)


@app.route('/statistics/data')
@login_required
def statistics_data():
    # 获取用户选择的时间范围
    selected_period = request.args.get('period', 'day')
    today = datetime.now().date()

    # 根据选择的时间范围计算开始日期
    if selected_period == 'day':
        start_date = today
        selected_period_label = '今天'
    elif selected_period == '7days':
        start_date = today - timedelta(days=7)
        selected_period_label = '最近七天'
    elif selected_period == 'week':
        start_date = today - timedelta(days=today.weekday())
        selected_period_label = '本周'
    elif selected_period == 'month':
        start_date = today.replace(day=1)
        selected_period_label = '本月'
    elif selected_period == '30days':
        start_date = today - timedelta(days=30)
        selected_period_label = '最近三十天'
    elif selected_period == 'year':
        start_date = today.replace(year=today.year - 1)
        selected_period_label = '最近一年'
    else:
        start_date = today
        selected_period_label = '今天'

    # 查询消费记录
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= today
    ).all()

    # 计算总消费和各类别消费
    total_expenses = sum(expense.amount for expense in expenses)
    categories = {}
    for expense in expenses:
        if expense.category not in categories:
            categories[expense.category] = 0
        categories[expense.category] += expense.amount

    # 根据时间范围生成主图表数据
    if selected_period == 'day':
        main_labels = list(categories.keys())
        main_data = list(categories.values())
    else:
        # 按天/周/月分组
        date_format = '%Y-%m-%d' if selected_period in ['7days', '30days'] else '%Y-%m' if selected_period == 'year' else '%Y-%m-%d'
        grouped_expenses = {}
        for expense in expenses:
            key = expense.date.strftime(date_format)
            if key not in grouped_expenses:
                grouped_expenses[key] = 0
            grouped_expenses[key] += expense.amount
        main_labels = list(grouped_expenses.keys())
        main_data = list(grouped_expenses.values())

    # 饼状图数据
    pie_labels = list(categories.keys())
    pie_data = list(categories.values())

    return jsonify({
        'mainLabels': main_labels,
        'mainData': main_data,
        'pieLabels': pie_labels,
        'pieData': pie_data,
        'total_expenses': total_expenses
    })


@app.route('/export')
@login_required
def export_data():
    # 获取用户选择的时间范围
    selected_period = request.args.get('period', 'day')
    today = datetime.now().date()

    # 根据选择的时间范围计算开始日期
    if selected_period == 'day':
        start_date = today
    elif selected_period == '7days':
        start_date = today - timedelta(days=7)
    elif selected_period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif selected_period == 'month':
        start_date = today.replace(day=1)
    elif selected_period == '30days':
        start_date = today - timedelta(days=30)
    elif selected_period == 'year':
        start_date = today.replace(year=today.year - 1)
    else:
        start_date = today

    # 查询消费记录
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= today
    ).all()

    # 将数据写入 CSV 文件
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头（确保使用 UTF-8 编码）
    writer.writerow(['日期', '类别', '金额'])
    for expense in expenses:
        writer.writerow([expense.date, expense.category, expense.amount])

    # 返回 CSV 文件
    output.seek(0)
    response = make_response(output.getvalue().encode('utf-8-sig'))  # 使用 utf-8-sig 编码
    response.headers['Content-Disposition'] = f"attachment; filename*=utf-8''{quote(f'expenses_{selected_period}.csv')}"
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'  # 设置字符集
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)