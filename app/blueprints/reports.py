from flask import Blueprint, render_template, session, redirect, url_for
from app.utils import extract_section, format_insights, format_strategies

reports = Blueprint('reports', __name__, url_prefix='/reports')


@reports.route('/report')
def show_report():
    if 'insights' in session:
        insights = session['insights']
        summary = extract_section(insights, "Summary")
        key_insights_raw = extract_section(insights, "Key Insights")
        actionable_strategies_raw = extract_section(insights, "Actionable Strategies")

        key_insights = format_insights(key_insights_raw) if key_insights_raw else []
        actionable_strategies = format_strategies(actionable_strategies_raw) if actionable_strategies_raw else []

        return render_template('report.html', summary=summary, key_insights=key_insights, actionable_strategies=actionable_strategies)
    return redirect(url_for('main.index'))  # if 'index' is within the 'main' blueprint
