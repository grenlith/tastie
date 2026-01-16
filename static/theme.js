(function() {
    // apply saved theme on load (before DOM is ready, to prevent flashing)
    var theme = localStorage.getItem('theme');
    if (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        theme = 'dark';
    }
    if (theme === 'dark') {
        document.documentElement.className = 'dark-theme';
    }

    document.addEventListener('DOMContentLoaded', function() {
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', function() {
                var html = document.documentElement;
                if (html.className === 'dark-theme') {
                    html.className = '';
                    localStorage.setItem('theme', 'light');
                } else {
                    html.className = 'dark-theme';
                    localStorage.setItem('theme', 'dark');
                }
            });
        }

        // auto-submit file inputs
        document.querySelectorAll('input[type="file"][data-auto-submit]').forEach(function(input) {
            input.addEventListener('change', function() {
                if (this.form) this.form.submit();
            });
        });
    });
})();
