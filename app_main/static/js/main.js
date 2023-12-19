// let csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

// console.log('CSRF токен:', csrfToken);

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrfToken)
            console.log('CSRF токен:', csrfToken);
        }
    }
})

$(document).ready(function () {
    $.getJSON("/\<lang\>/home", function (data) {
        $('#catalog_link').append('<span class="badge bg-primary rounded-circle">' +
            data.count + '</span>');
    });
});


// $.ajax({
//     url: '/category-create',
//     type: 'POST',
//     headers: {
//         // 'X-CSRFToken': csrftoken
//         'Content-Type': 'application/json'
//     },
//     // data: {
//     //     name: 'SLAM'
//     // },
//     success: function(response) {
//         console.log('Запрос успешно выполнен');
//     },
//     error: function(xhr, status, error) {
//         console.log('Произошла ошибка:', error);
//     }
// });

