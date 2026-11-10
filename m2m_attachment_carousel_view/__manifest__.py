{
    'name': 'Many2Many Attachments Carousel View',
    'version': '18.1',
    'summary': '',
    'sequence': 10,
    'description': """
            """,
    'category': '',
    'website': '',
    'depends': ['base','web','product'],
    'data': [],
    "application": True,
    'assets': {
        'web.assets_backend': [
            'm2m_attachment_carousel_view/static/src/js/m2m_attachment_carousel_view.js',
            'm2m_attachment_carousel_view/static/src/xml/image_carousel_template.xml',
            'm2m_attachment_carousel_view/static/src/css/image_carousel.css',
        ],
    },
    'license': 'LGPL-3',
    "auto_install": False,
    "installable": True,
}
