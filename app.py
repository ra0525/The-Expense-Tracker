from flask import Flask, render_template, request, redirect
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
FILE_NAME = 'expenses.csv'

if not os.path.exists(FILE_NAME):
    pd.DataFrame(columns=['Date','Category','Description','Amount']).to_csv(FILE_NAME, index=False)

def read_csv():
    try:
        return pd.read_csv(FILE_NAME)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=['Date','Category','Description','Amount'])
        df.to_csv(FILE_NAME, index=False)
        return df


def save_csv(df):
    df.to_csv(FILE_NAME, index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET','POST'])
def add_expense():
    if request.method=='POST':
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').strftime('%d-%B-%Y')
        category = request.form['category']
        desc = request.form['description']
        amount = float(request.form['amount'])
        df = read_csv()
        df = pd.concat([df, pd.DataFrame([[date,category,desc,amount]], columns=['Date','Category','Description','Amount'])], ignore_index=True)
        save_csv(df)
        return redirect('/view')
    return render_template('add_expense.html')

from datetime import datetime

@app.route('/view', methods=['GET', 'POST'])
def view_expenses():
    df = read_csv()

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    current_year = datetime.now().year
    years = list(range(1947, current_year + 1))

    monthly_data = []
    monthly_total = 0
    yearly_data = []
    yearly_total = 0
    active_section = ""  # new

    if request.method == 'POST':
        if 'month' in request.form and 'year' in request.form:
            active_section = 'monthly'   # new
            selected_month = request.form.get('month')
            selected_year = int(request.form.get('year'))
            df['ParsedDate'] = pd.to_datetime(df['Date'], format='%d-%B-%Y', errors='coerce')
            filtered = df[(df['ParsedDate'].dt.strftime('%B') == selected_month) &
                          (df['ParsedDate'].dt.year == selected_year)]
            monthly_data = filtered.to_dict('records')
            monthly_total = filtered['Amount'].sum()
        elif 'year_only' in request.form:
            active_section = 'yearly'   # new
            selected_year = int(request.form.get('year_only'))
            df['ParsedDate'] = pd.to_datetime(df['Date'], format='%d-%B-%Y', errors='coerce')
            filtered = df[df['ParsedDate'].dt.year == selected_year]
            yearly_data = filtered.to_dict('records')
            yearly_total = filtered['Amount'].sum()

    return render_template('view_expenses.html',
                           months=months, years=years,
                           monthly_data=monthly_data, monthly_total=monthly_total,
                           yearly_data=yearly_data, yearly_total=yearly_total,
                           active_section=active_section)

@app.route('/delete', methods=['GET', 'POST'])
def delete_expense():
    df = read_csv()
    categories = []
    selected_date = None
    categories_on_date = []
    message = None
    show_category_select = False
    deleted = False
    remaining_expenses = []

    if request.method == 'POST':
        selected_date = request.form.get('date')
        selected_category = request.form.get('category')

        # if category selected → delete that category on that date
        if selected_date and selected_category:
            formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%B-%Y')
            before = len(df)
            df = df[~((df['Date'] == formatted_date) & (df['Category'] == selected_category))]
            after = len(df)
            save_csv(df)
            deleted = True
            print(f"Deleted {before - after} rows with date={formatted_date} and category={selected_category}")
            message = f"Deleted {before - after} expense(s)."
            remaining_expenses = df.to_dict('records')

        # if only date selected → check how many categories
        elif selected_date:
            formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%B-%Y')
            matching = df[df['Date'] == formatted_date]
            if matching.empty:
                message = "No expenses found on this date."
            else:
                unique_categories = matching['Category'].unique()
                if len(unique_categories) == 1:
                    # delete all on that date
                    before = len(df)
                    df = df[df['Date'] != formatted_date]
                    after = len(df)
                    save_csv(df)
                    deleted = True
                    print(f"Deleted {before - after} rows with date={formatted_date}")
                    message = f"Deleted {before - after} expense(s) on date {formatted_date}."
                    remaining_expenses = df.to_dict('records')
                else:
                    # show category select
                    show_category_select = True
                    categories_on_date = list(unique_categories)

    return render_template(
        'delete_expense.html',
        categories=categories,
        selected_date=selected_date,
        show_category_select=show_category_select,
        categories_on_date=categories_on_date,
        message=message,
        deleted=deleted,
        remaining_expenses=remaining_expenses
    )

@app.route('/edit', methods=['GET', 'POST'])
def edit_expense():
    df = read_csv()
    selected_date = None
    selected_date_input = None
    expenses_on_date = []  # list of expenses for that date
    columns = []
    updated_expenses = []

    if request.method == 'POST':
        selected_date_input = request.form.get('date')
        if selected_date_input:
            selected_date = datetime.strptime(selected_date_input, '%Y-%m-%d').strftime('%d-%B-%Y')
            expenses_found = df[df['Date'] == selected_date]

            if expenses_found.empty:
                message = "No expenses found for this date."
                return render_template('edit_expense.html',
                                       message=message,
                                       expenses_on_date=[],
                                       columns=[],
                                       date=selected_date_input,
                                       updated_expenses=[])
            else:
                expenses_on_date = expenses_found.to_dict('records')
                columns = list(df.columns)

                # Check if user also submitted column & new value
                column = request.form.get('column')
                new_value = request.form.get('new_value')

                if column and new_value:
                    if column == 'Amount':
                        new_value = float(new_value)
                    df.loc[df['Date'] == selected_date, column] = new_value
                    save_csv(df)
                    updated = df[df['Date'] == selected_date]
                    updated_expenses = updated.to_dict('records')
                    return render_template('edit_expense.html',
                                           message="Expense updated successfully!",
                                           expenses_on_date=expenses_on_date,
                                           columns=columns,
                                           date=selected_date_input,
                                           updated_expenses=updated_expenses)

                # If just picked date: show table & form to pick column/new value
                return render_template('edit_expense.html',
                                       expenses_on_date=expenses_on_date,
                                       columns=columns,
                                       date=selected_date_input,
                                       updated_expenses=[])

    # GET request: show date picker only
    return render_template('edit_expense.html', expenses_on_date=[], columns=[], date=None, updated_expenses=[])

@app.route('/by_date', methods=['GET','POST'])
def by_date():
    df = read_csv()
    filtered=[]
    total=0
    if request.method=='POST':
        start = request.form['start']
        end = request.form['end']
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        mask = (df['Date']>=start)&(df['Date']<=end)
        filtered = df.loc[mask].copy()
        filtered['Date'] = filtered['Date'].dt.strftime('%d-%B-%Y')
        total=filtered['Amount'].sum()
        filtered=filtered.to_dict('records')
    return render_template('view_by_date.html', data=filtered, total=total)

@app.route('/by_category', methods=['GET','POST'])
def by_category():
    df = read_csv()
    categories = []
    if not df.empty and 'Category' in df.columns:
        categories = df['Category'].dropna().unique().tolist()
    filtered = []
    total = 0
    if request.method=='POST':
        cat = request.form['category']
        filtered = df[df['Category'].str.lower() == cat.lower()]
        total = filtered['Amount'].sum()
        filtered = filtered.to_dict('records')
    return render_template('view_by_category.html', data=filtered, total=total, categories=categories)

@app.route('/reports')
def reports():
    df = read_csv()
    if df.empty:
        monthly = []; yearly = []; cat = []
    else:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['MonthYear'] = df['Date'].dt.strftime('%B-%Y')
        monthly = df.groupby('MonthYear')['Amount'].sum().reset_index().to_dict('records')
        df['Year'] = df['Date'].dt.year
        yearly = df.groupby('Year')['Amount'].sum().reset_index().to_dict('records')
        cat = df.groupby('Category')['Amount'].sum().reset_index().to_dict('records')
    return render_template('reports.html', monthly=monthly, yearly=yearly, cat=cat)

if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    port = 5000

    # Only open browser if Flask isn't running in the reloader process
    def open_browser():
        webbrowser.open(f'http://127.0.0.1:{port}')

    Timer(1, open_browser).start()
    app.run(debug=True, port=port, use_reloader=False)
