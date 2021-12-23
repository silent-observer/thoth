$(document).ready(function() {
    $('#search-input').keyup(function(event) {
        if (event.keyCode === 13) {
            window.location.href = "/search?s=" + $('#search-input').val()
        }
    })
    $('#header-logo').click(function() {
        window.location.href = "/"
    })
    $('#login-icon').click(function() {
        window.location.href = "/login"
    })
    $('#register-icon').click(function() {
        window.location.href = "/register"
    })
    $('#logout-icon').click(function() {
        window.location.href = "/logout"
    })
})