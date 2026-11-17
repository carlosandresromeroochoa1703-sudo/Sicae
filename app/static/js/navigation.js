document.addEventListener("DOMContentLoaded", function () {

    /*
     * La página entra suavemente al cargar.
     * El menú lateral permanece completamente estable.
     */
    document.body.classList.add("page-loaded");

    const enlaces = document.querySelectorAll(
        'a[href]:not([target="_blank"]):not([href^="#"]):not([href^="javascript:"])'
    );

    enlaces.forEach(function (enlace) {

        enlace.addEventListener("click", function (evento) {

            const href = enlace.getAttribute("href");

            if (!href) {
                return;
            }

            if (
                evento.ctrlKey ||
                evento.shiftKey ||
                evento.altKey ||
                evento.metaKey
            ) {
                return;
            }

            if (
                href.startsWith("http://") ||
                href.startsWith("https://") ||
                href.startsWith("mailto:") ||
                href.startsWith("tel:")
            ) {
                return;
            }

            /*
             * No ocultamos la página actual.
             * Dejamos que el navegador cambie inmediatamente.
             */
            window.location.assign(href);

        });

    });

});
