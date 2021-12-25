$(document).ready(function() {
    subject = $('#subject')
    for (s in data) {
        subject.append($('<option>', {
            value: s,
            text: s
        }));
    }
    subject.prop("selectedIndex", -1)

    subject.change(function() {
        $('#discipline-div').removeClass('disabled-div')

        discipline = $('#discipline')
        discipline.empty()
        data[subject.val()].forEach(d =>
            discipline.append($('<option>', {
                value: d,
                text: d
            }))
        )
        discipline.prop("selectedIndex", -1)
        discipline.removeAttr('disabled')
    })

    $('#discipline').change(function() {
        $('.submit-btn').removeAttr('disabled')
    })
})