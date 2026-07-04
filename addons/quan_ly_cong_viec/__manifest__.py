# -*- coding: utf-8 -*-
{
    'name': "Quản lý Công việc",

    'summary': """
        Module quản lý công việc, dự án, nhiệm vụ và theo dõi tiến độ""",

    'description': """
        Module quản lý công việc bao gồm:
        - Quản lý dự án
        - Quản lý công việc
        - Phân công nhiệm vụ
        - Theo dõi tiến độ
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Project Management',
    'version': '1.0',

    'depends': ['base', 'mail', 'nhan_su'],  # mail: cần cho mail.activity (cảnh báo trễ hạn)
    # Note: project_management là soft dependency - không cần khai báo ở đây
    # Field du_an_id trong cong_viec sẽ tự động tham chiếu đến model 'projects' nếu module project_management được cài đặt

    # Data files được load theo thứ tự
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data (sequences phải load trước views)
        'data/sequence_data.xml',
        'data/cron_canh_bao_qua_han.xml',
        # Views
        'views/cong_viec.xml',
        'views/nhiem_vu.xml',
        'views/tien_do.xml',
        'views/bao_cao_hieu_qua.xml',
        'views/bao_cao_du_an.xml',
        'report/report_action_bao_cao_du_an.xml',
        'report/report_bao_cao_du_an.xml',
        'views/menu.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,

    # Assets: JS/CSS cho nút thu/mở chatter ở form Nhiệm vụ
    'assets': {
        'web.assets_backend': [
            'quan_ly_cong_viec/static/src/js/nhiem_vu_chatter_toggle.js',
            'quan_ly_cong_viec/static/src/css/nhiem_vu_chatter_toggle.css',
        ],
    },
}