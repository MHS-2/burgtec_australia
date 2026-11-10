{
    "name": "Burgtec Account Budget Planning",
    "summary": "Revenue budget planning by target type, state and month",
    "description": """
Budget Planning Screen in Accounting
====================================
Define revenue targets based on Target Type (e.g. Churn, Major Projects),
State (location) and Month. Monthly totals are auto-calculated as a SUM
footer row on the budget lines.
    """,
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account", "base", 'accountant'],
    "data": [
        "security/burgtec_account_budget_planning_group.xml",
        "security/ir.model.access.csv",
        "views/budget_target_type_views.xml",
        "views/budget_target_state_views.xml",
        "views/budget_plan_views.xml",
        "views/budget_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
