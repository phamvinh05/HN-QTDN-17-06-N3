# -*- coding: utf-8 -*-
{
    'name': "project_management",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'nhan_su', 'mail', 'quan_ly_cong_viec'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'report/report_action.xml',
        'report/project_approval_report.xml',
        # Load các view/actions trước
        'views/projects.xml',
        'views/employees.xml',
        'views/budgets.xml',
        'views/expenses.xml',
        'views/chart.xml',
        'views/chartoftasks.xml',
        'views/cong_viec_extend.xml',
        'views/nhan_vien_extend.xml',
        'views/risk_management.xml',
        'views/gemini_ai_views.xml',
        'views/projects_dashboard.xml',
        # Cuối cùng mới load menu, vì menu tham chiếu tới các action ở trên
        'views/menu.xml',
    ],

    # 'assets': {
    #     'web.assets_backend': [
    #         'project_management\static\src\projects.css',
    #     ],
    # },

    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}