odoo.define('quan_ly_cong_viec.nhiem_vu_chatter_toggle', function (require) {
    "use strict";

    /**
     * Cho phép ẩn/hiện toàn bộ chatter (bên phải form Nhiệm vụ) bằng 1 nút bấm.
     *
     * Lưu ý quan trọng: chatter thật KHÔNG được phép nằm trong div bọc nào khác,
     * vì Odoo thay thế div.oe_chatter bằng div.o_FormRenderer_chatterContainer
     * (mounted Owl component), và layout 2 cột của form phụ thuộc vào việc nó
     * là con trực tiếp của <form> (anh em với .o_form_sheet_bg). Vì vậy nút toggle
     * không thể là cha của chatter - phải tìm chatter qua cùng .o_form_view chứa nút.
     */
    document.addEventListener('click', function (ev) {
        var nut = ev.target.closest('.o_nhiem_vu_chatter_toggle_btn');
        if (!nut) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();

        var formView = nut.closest('.o_form_view');
        if (!formView) {
            return;
        }
        var chatter = formView.querySelector('.o_FormRenderer_chatterContainer');
        var icon = nut.querySelector('i');
        if (!chatter) {
            return;
        }

        var dangAn = chatter.style.display === 'none';
        chatter.style.display = dangAn ? '' : 'none';
        if (icon) {
            icon.className = dangAn ? 'fa fa-chevron-right' : 'fa fa-chevron-left';
        }
    });
});