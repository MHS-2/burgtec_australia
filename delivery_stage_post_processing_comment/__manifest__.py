{
    "name": "Delivery Stage Post Processing Comments",
    "version": "18.0.1.0.0",
    "summary": "Per delivery stage (do_stage_X) comment button + popup on planning screen lines",
    "author": "Byte Legions",
    "license": "LGPL-3",
    "depends": ["hubspot_ticket_creation_ps"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "delivery_stage_post_processing_comment/static/src/stage_comment/stage_comment_dialog.js",
            "delivery_stage_post_processing_comment/static/src/stage_comment/stage_comment.js",
            "delivery_stage_post_processing_comment/static/src/stage_comment/stage_comment.xml",
            "delivery_stage_post_processing_comment/static/src/stage_comment/stage_comment.scss",
        ],
    },
    "installable": True,
}
