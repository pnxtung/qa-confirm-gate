document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('table.resizable');
    tables.forEach(table => {
        const cols = table.querySelectorAll('th');
        cols.forEach(col => {
            const resizer = document.createElement('div');
            resizer.classList.add('resizer');
            col.appendChild(resizer);
            
            let x = 0; let w = 0;
            const mouseDownHandler = function(e) {
                x = e.clientX;
                const styles = window.getComputedStyle(col);
                w = parseInt(styles.width, 10);
                document.addEventListener('mousemove', mouseMoveHandler);
                document.addEventListener('mouseup', mouseUpHandler);
            };
            const mouseMoveHandler = function(e) {
                const dx = e.clientX - x;
                col.style.width = `${w + dx}px`;
                col.style.minWidth = `${w + dx}px`;
            };
            const mouseUpHandler = function() {
                document.removeEventListener('mousemove', mouseMoveHandler);
                document.removeEventListener('mouseup', mouseUpHandler);
            };
            resizer.addEventListener('mousedown', mouseDownHandler);

            // Double click to auto-fit
            resizer.addEventListener('dblclick', function(e) {
                e.stopPropagation();
                // Temporarily let browser determine natural width
                table.classList.remove('w-full');
                col.style.minWidth = '0px';
                col.style.width = 'auto';
                
                // Measure natural width
                const naturalWidth = col.getBoundingClientRect().width;
                
                // Restore and apply new width
                table.classList.add('w-full');
                col.style.minWidth = naturalWidth + 'px';
                col.style.width = naturalWidth + 'px';
            });
        });
    });
});
