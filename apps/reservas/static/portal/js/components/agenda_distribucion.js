(function () {
    'use strict';
    if (window.AgendaUpec) return;

    // Una misma escala para el asistente, Mis reservas y la agenda de gestión.
    function rowLayout(hours, intervals, minimumEventHeight = 128) {
        const rows = hours.map(hour => ({ hour, height: 48, top: 0 }));
        const ranges = intervals.map(interval => rows.map((row, index) => ({
            index, weight: Math.max(0, Math.min(row.hour + 1, interval.fin) - Math.max(row.hour, interval.inicio)),
        })).filter(item => item.weight > 0)).filter(range => range.length)
            .sort((a, b) => a.at(-1).index - b.at(-1).index || a[0].index - b[0].index);
        ranges.forEach(range => {
            const height = range.reduce((sum, item) => sum + rows[item.index].height * item.weight, 0);
            const last = range.at(-1);
            rows[last.index].height += Math.max(0, minimumEventHeight - height) / last.weight;
        });
        let total = 0;
        rows.forEach(row => { row.top = total; total += row.height; });
        return { rows, total };
    }

    function position(layout, hour) {
        if (!layout.rows.length) return 0;
        if (hour <= layout.rows[0].hour) return 0;
        const row = layout.rows.find(item => hour >= item.hour && hour < item.hour + 1);
        return row ? row.top + (hour - row.hour) * row.height : layout.total;
    }

    function mode(width, selected) { return selected || (width < 700 ? 'day' : 'week'); }

    window.AgendaUpec = Object.freeze({ rowLayout, position, mode });
})();
