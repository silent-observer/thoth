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
    $('.submit-btn').attr('disabled', '')

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
        $('.submit-btn').removeAttr('disabled')
    })

    $('.submit-btn').click(function(event) {
        event.preventDefault()
        var title = $('#title').val()
        var text = $('#question').val()
        var subject = $('#subject').val()
        var discipline = $('#discipline').val()

        var error = false

        $('.error').remove()
        if (title.length < 10 || title.length > 100) {
            var errorText = $($.parseHTML('<p class="error">Заголовок должен содержать от 10 до 100 символов</p>'))
            $('.question').prepend(errorText)
            error = true
        }
        if (text.length < 10 || text.length > 2000) {
            var errorText = $($.parseHTML('<p class="error">Текст вопроса должен содержать от 10 до 2000 символов</p>'))
            $('.question').prepend(errorText)
            error = true
        }
        if (!error) {
            $.post(window.location, {
                'title': title,
                'question': text,
                'subject': subject,
                'discipline': discipline
            }, function(data, status, xhr){
                console.log(data)
                console.log(status)
                console.log(xhr)
                if (data.startsWith('/')) {
                    window.location.href = data
                } else {
                }
            })
        }
    })
})