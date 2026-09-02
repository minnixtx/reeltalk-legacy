(function () {
    "use strict";

    const MIN_CHARS = 2;
    const DEBOUNCE_MS = 300;

    /**
     * Search-as-you-type dropdown for the main search box (decision 28).
     *
     * Binds to `#tour-search` and renders suggestions from
     * `/search/suggest/?q=<term>&type=film` in `#search-suggest`.
     * Click-only: clicking a row navigates to the film page; Enter still
     * submits the normal search form.
     */
    function initSuggest(input) {
        const menu = document.getElementById("search-suggest");

        if (!menu) {
            return;
        }

        let debounceTimer = null;

        function hide() {
            menu.classList.add("is-hidden");
            menu.innerHTML = "";
        }

        function render(rows) {
            menu.innerHTML = "";

            if (!rows.length) {
                hide();
                return;
            }

            rows.forEach((row) => {
                const item = document.createElement("a");
                item.href = row.url;
                item.className = "search-suggest-item";
                item.setAttribute("role", "option");

                const poster = document.createElement("span");
                poster.className = "search-suggest-poster";

                if (row.poster) {
                    const img = document.createElement("img");
                    img.src = row.poster;
                    img.alt = "";
                    img.loading = "lazy";
                    img.decoding = "async";
                    poster.appendChild(img);
                } else {
                    poster.classList.add("no-cover");
                }
                item.appendChild(poster);

                const text = document.createElement("span");
                text.className = "search-suggest-text";

                const title = document.createElement("span");
                title.className = "search-suggest-title";
                title.textContent = row.title;
                text.appendChild(title);

                if (row.year) {
                    const year = document.createElement("span");
                    year.className = "has-text-grey search-suggest-year";
                    year.textContent = `(${row.year})`;
                    text.appendChild(year);
                }
                item.appendChild(text);

                // click-only: close the dropdown, then let the anchor navigate
                item.addEventListener("click", hide);
                menu.appendChild(item);
            });

            menu.classList.remove("is-hidden");
        }

        function fetchSuggestions() {
            const query = input.value.trim();

            if (query.length < MIN_CHARS) {
                hide();
                return;
            }

            fetch(`/search/suggest/?q=${encodeURIComponent(query)}&type=film`)
                .then((response) => response.json())
                .then((data) => render(data.results || []))
                .catch(hide);
        }

        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchSuggestions, DEBOUNCE_MS);
        });

        // close on outside clicks; mousedown fires before the item's click,
        // and items inside .search-suggest are exempt
        document.addEventListener("mousedown", (event) => {
            if (!event.target.closest(".search-suggest")) {
                hide();
            }
        });

        // Enter submits the normal search form; just close the dropdown
        input.form.addEventListener("submit", hide);
    }

    const input = document.getElementById("tour-search");

    if (input) {
        initSuggest(input);
    }
})();
