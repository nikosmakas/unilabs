/**
 * Lightweight vanilla JS table sorting for tables with class "sortable".
 * Click a <th> to sort ascending; click again to sort descending.
 * Supports numeric and string comparison.
 */
(function () {
    'use strict';

    function sortTable(table, colIndex, ascending) {
        var tbody = table.tBodies[0];
        if (!tbody) return;
        var rows = Array.from(tbody.rows);

        rows.sort(function (a, b) {
            var aText = (a.cells[colIndex] || {}).textContent.trim();
            var bText = (b.cells[colIndex] || {}).textContent.trim();

            var aNum = parseFloat(aText);
            var bNum = parseFloat(bText);

            var result;
            if (!isNaN(aNum) && !isNaN(bNum)) {
                result = aNum - bNum;
            } else {
                result = aText.localeCompare(bText, 'el');
            }
            return ascending ? result : -result;
        });

        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    function initSortable() {
        var tables = document.querySelectorAll('table.sortable');
        tables.forEach(function (table) {
            var headers = table.querySelectorAll('thead th');
            headers.forEach(function (th, index) {
                th.style.cursor = 'pointer';
                th.setAttribute('title', 'Κλικ για ταξινόμηση');

                th.addEventListener('click', function () {
                    var currentAsc = th.getAttribute('data-sort-asc') === 'true';
                    var ascending = !currentAsc;

                    // Reset all headers in this table
                    headers.forEach(function (h) {
                        h.removeAttribute('data-sort-asc');
                        // Remove existing sort indicators
                        var indicator = h.querySelector('.sort-indicator');
                        if (indicator) indicator.remove();
                    });

                    th.setAttribute('data-sort-asc', String(ascending));

                    // Add sort indicator
                    var span = document.createElement('span');
                    span.className = 'sort-indicator ms-1';
                    span.textContent = ascending ? ' ?' : ' ?';
                    th.appendChild(span);

                    sortTable(table, index, ascending);
                });
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSortable);
    } else {
        initSortable();
    }
})();
