$(document).ready(function() {
    subject = $('#subject')
    for (s in data) {
        subject.append($('<option>', {
            value: s,
            text: s
        }));
    }
    subject.prop("selectedIndex", -1)
    $('#discipline').attr('disabled', '')
    $('.list-btn').attr('disabled', '')

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
        $('.list-btn').attr('disabled', '')
    })

    $('#discipline').change(function() {
        $('.list-btn').removeAttr('disabled')
    })

    function delete_function() {
        var this_discipline = $(this).attr('val')
        $(this).parent().remove()
        $.post(window.location, {
            'action': 'delete',
            'discipline': this_discipline
        })
    }

    $('#like-btn').click(function() {
        var new_discipline = $('#discipline').val()
        subject.prop("selectedIndex", -1)
        $('#discipline').attr('disabled', '')
        $('#discipline').empty()
        $('.list-btn').attr('disabled', '')

        var new_li = $($.parseHTML('<li>' + new_discipline + '<img class="delete-btn" val="' + new_discipline + '" src="/static/resources/cross_icon.png"></li>'))
        $('#like-list').append(new_li)
        $(new_li).find('.delete-btn').click(delete_function)

        $.post(window.location, {
            'action': 'like',
            'discipline': new_discipline
        })
    })

    $('#dislike-btn').click(function() {
        var new_discipline = $('#discipline').val()
        subject.prop("selectedIndex", -1)
        $('#discipline').attr('disabled', '')
        $('#discipline').empty()
        $('.list-btn').attr('disabled', '')

        var new_li = $($.parseHTML('<li>' + new_discipline + '<img class="delete-btn" val="' + new_discipline + '" src="/static/resources/cross_icon.png"></li>'))
        $('#dislike-list').append(new_li)
        $(new_li).find('.delete-btn').click(delete_function)

        $.post(window.location, {
            'action': 'dislike',
            'discipline': new_discipline
        })
    })

    $('.delete-btn').click(delete_function)
})