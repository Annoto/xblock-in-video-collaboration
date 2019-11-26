(function() {
    $(function($) {
        var setReadonlyAttr = function() {
            var field = $('#xb-field-edit-version');
            if (field.length) {
                field.attr('readonly', 'readonly');
            } else {
                setTimeout(setReadonlyAttr, 200);
            }
        };
        setReadonlyAttr();
    });
})();
