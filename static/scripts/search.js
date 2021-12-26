$(document).ready(function() {
    $('#search-input').val(search_text)

    function build_search_results(data) {
        $('#search-results').empty()
        if (data['questions'].length == 0) {
            $('#search-results').append($('<p>', {
                text: 'Ничего не было найдено'
            }))
        } else {
            data['questions'].forEach((q) => {
                let question = $($.parseHTML(`
                    <section class="question">
                        <div class="question-body">
                            <div class="question-title">
                            <a href="${'/q/' + q['id']}">${q['title']}</a>
                            </div>
                            <p>${q['text']}</p>
                            <p class="question-rating">${q['rating']}</p>
                        </div>
                    </section>
                `))
                $('#search-results').append(question)
            })
        }
    }
    build_search_results(search_data)

    function update_results() {
        data = {
            s: $('#search-input').val(),
            d: $('#discipline').val(),
            sort: $('#sorting').val()
        },
        $.ajax({
            url: '/api/search',
            type: 'get',
            data: data,
            dataType: 'json',
            success: function(responce) {
                if ($('#search-input').val() == data.s && $('#discipline').val() == data.d && $('#sorting').val() == data.sort) {
                    search_data = responce
                    build_search_results(search_data)
                }
            }
        })
    }

    subject = $('#subject')
    subject.append($('<option>', {
        value: 'None',
        text: 'Предмет'
    }))
    for (s in discipline_data) {
        subject.append($('<option>', {
            value: s,
            text: s
        }));
    }

    subject.prop("selectedIndex", 0)

    $('#discipline').attr('disabled', '')
    $('#discipline').append($('<option>', {
        value: 'None',
        text: 'Дисциплина'
    }))
    $('#discipline').prop("selectedIndex", 0)

    subject.change(function() {
        $('#discipline-div').removeClass('disabled-div')

        discipline = $('#discipline')
        discipline.empty()
        discipline.append($('<option>', {
            value: 'None',
            text: 'Дисциплина'
        }))
        if (subject.val() !== 'None') {
            discipline_data[subject.val()].forEach(d =>
                discipline.append($('<option>', {
                    value: d,
                    text: d
                }))
            )
            discipline.removeAttr('disabled')
        }
        else {
            discipline.attr('disabled', '')
            update_results()
        }
        discipline.prop("selectedIndex", 0)
    })

    $('#discipline').change(update_results)
    $('#sorting').change(update_results)
})