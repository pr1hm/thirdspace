const API_BASE = 'http://127.0.0.1:8000';
const slots = [...document.querySelectorAll('.slot')];
const slider = document.getElementById('slider');
const intensity = document.getElementById('intensity');
const intensityval = document.getElementById('intensityval');
const input = document.getElementById('input');
const inputpre = document.getElementById('inputpre');
const outputpre = document.getElementById('outputpre');
const inventory = document.getElementById('inventoryGrid');
const inEnlarge = inputpre.querySelector('[data-enlarge="inputpre"]');
const outEnlarge = outputpre.querySelector('[data-enlarge="outputpre"]');
const savebtn = document.getElementById('saveButton');
const status = document.getElementById('processingStatus');
const lightbox = document.getElementById('lightbox');
const lightboximg = document.getElementById('lightboxImg');
const lightboxclose = document.getElementById('lightboxClose');
let draggedItem = null;
let draggedFromSlot = null;
let dragCompleted = false;
let draginput = null;
let inputdragged = false;
let inputurl = null;
let inputfile = null;
let outputurl = null;
let control = null;
let processver = 0;

function announce(message) {
    return message;
}

function hideSlider() {
    slider.classList.remove('visible');
    slider.removeAttribute('data-slot');
}

function showSlider(slot) {
    const bounds = slot.getBoundingClientRect();
    slider.style.left = `${Math.min(window.innerWidth - 76, bounds.right + 8)}px`;
    slider.style.top = `${Math.max(8, bounds.top + bounds.height / 2 - 75)}px`;
    slider.dataset.slot = slot.getAttribute('aria-label');
    const placed = slot.querySelector('.item');
    intensity.value = placed?.dataset.intensity || '100';
    intensityval.textContent = `${intensity.value}%`;
    slider.classList.add('visible');
    intensity.focus();
}

function getFilter() {
    return slots
        .map(slot => slot.querySelector('.item'))
        .filter(Boolean)
        .map(item => ({
            name: item.dataset.filter,
            intensity: Number(item.dataset.intensity || 100),
        }));
}

async function processimg() {
    if (!inputfile) return;

    control?.abort();
    control = new AbortController();
    const requestVersion = ++processver;
    outputpre.classList.add('processing');
    status.textContent = 'hol\' up...';
    savebtn.disabled = true;
    const formData = new FormData();
    formData.append('image', inputfile, inputfile.name);
    formData.append('filters', JSON.stringify(getFilter()));

    try {
        const response = await fetch(`${API_BASE}/process`, {
            method: 'POST',
            body: formData,
            signal: control.signal,
        });
        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `Processing failed (${response.status})`);
        }

        const blob = await response.blob();
        if (requestVersion !== processver) return;
        if (outputurl) URL.revokeObjectURL(outputurl);
        outputurl = URL.createObjectURL(blob);
        const outputimg = document.createElement('img');
        outputimg.src = outputurl;
        outputimg.alt = 'Processed output image';
        outputpre.replaceChildren(outputimg);
        outputpre.prepend(savebtn, status);
        outputpre.append(outEnlarge);
        savebtn.disabled = false;
        outputpre.classList.remove('processing');
    } catch (error) {
        if (error.name !== 'AbortError') {
            outputpre.classList.remove('processing');
            announce(error.message);
            console.error(error);
        }
    }
}

function placeItem(item, slot) {
    const placed = item.cloneNode(true);
    placed.classList.remove('dragging');
    placed.setAttribute('draggable', 'true');
    placed.dataset.intensity = '100';
    placed.style.cursor = 'grab';
    placed.setAttribute('aria-label', `${item.dataset.filter} filter, double-click to adjust intensity`);
    slot.replaceChildren(placed);
    addDragHandlers(placed);
    announce(`${item.dataset.filter} equipped`);
    processimg();
    return placed;
}

function addDragHandlers(item) {
    item.setAttribute('draggable', 'true');
    item.addEventListener('dragstart', event => {
        draggedItem = item;
        draggedFromSlot = item.closest('.slot');
        dragCompleted = false;
        item.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.filter);
    });
    item.addEventListener('dragend', () => {
        item.classList.remove('dragging');
        if (draggedFromSlot && !dragCompleted && item.parentElement) {
            item.remove();
            processimg();
        }
        draggedItem = null;
        draggedFromSlot = null;
        dragCompleted = false;
    });
}

function loadSourceImage(file) {
    if (!file || !file.type.startsWith('image/')) {
        announce('Please choose an image');
        return;
    }
    if (inputurl) URL.revokeObjectURL(inputurl);
    inputfile = file;
    inputurl = URL.createObjectURL(file);
    inputpre.classList.add('has-image');
    const image = document.createElement('img');
    image.src = inputurl;
    image.alt = 'Loaded source image';
    image.draggable = true;
    image.addEventListener('click', event => event.stopPropagation());
    image.addEventListener('dragstart', event => {
        draginput = image;
        inputdragged = false;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', 'source-image');
    });
    image.addEventListener('dragend', () => {
        if (!inputdragged && draginput === image) clearSourceImage();
        draginput = null;
        inputdragged = false;
    });
    inputpre.replaceChildren(image, inEnlarge);
    announce('Image loaded');
    processimg();
}

function clearSourceImage() {
    if (inputurl) URL.revokeObjectURL(inputurl);
    inputurl = null;
    inputfile = null;
    inputpre.classList.remove('has-image');
    inputpre.replaceChildren(
        Object.assign(document.createElement('span'), {
            className: 'preview-hint',
            textContent: 'DRAG IMAGE OR CLICK TO LOAD AN IMG',
        }),
        inEnlarge
    );
    outputpre.replaceChildren();
    outputpre.append(
        savebtn,
        status,
        outEnlarge
    );
    savebtn.disabled = true;
    outputpre.classList.remove('processing');
}

function getpreview(preview) {
    return preview.querySelector('img');
}

function showlightbox(preview) {
    const image = getpreview(preview);
    if (!image) return;
    lightboximg.src = image.currentSrc || image.src;
    lightbox.hidden = false;
    lightboxclose.focus();
}

function hidelightbox() {
    lightbox.hidden = true;
    lightboximg.removeAttribute('src');
}

async function loadInventory() {
    try {
        const response = await fetch(`${API_BASE}/inventory`);
        if (!response.ok) throw new Error(`Inventory failed (${response.status})`);
        const filters = await response.json();
        inventory.replaceChildren();
        filters.forEach(filter => {
            const item = document.createElement('div');
            item.className = 'item';
            item.draggable = true;
            item.tabIndex = 0;
            item.dataset.filter = filter.name;
            item.title = filter.description;
            item.textContent = filter.name;
            inventory.append(item);
            inventoryfn(item);
        });
    } catch (error) {
        announce(error.message);
        console.error(error);
    }
}

function inventoryfn(item) {
    addDragHandlers(item);
    item.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const emptySlot = slots.find(slot => !slot.firstElementChild);
            if (emptySlot) placeItem(item, emptySlot);
        }
    });
}

inputpre.addEventListener('click', () => input.click());
inputpre.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        input.click();
    }
});
input.addEventListener('change', event => loadSourceImage(event.target.files[0]));
inputpre.addEventListener('dragover', event => {
    event.preventDefault();
    inputpre.classList.add('drag-over');
});
inputpre.addEventListener('dragleave', () => inputpre.classList.remove('drag-over'));
inputpre.addEventListener('drop', event => {
    event.preventDefault();
    inputpre.classList.remove('drag-over');
    if (draginput) {
        inputdragged = true;
        return;
    }
    loadSourceImage(event.dataTransfer.files[0]);
});

slots.forEach(slot => {
    slot.addEventListener('dragover', event => {
        event.preventDefault();
        slot.classList.add('drag-over');
    });
    slot.addEventListener('dragleave', () => slot.classList.remove('drag-over'));
    slot.addEventListener('drop', event => {
        event.preventDefault();
        slot.classList.remove('drag-over');
        if (draggedItem) {
            dragCompleted = true;
            const item = draggedItem;
            if (draggedFromSlot) item.remove();
            placeItem(item, slot);
        }
    });
    slot.addEventListener('dblclick', event => {
        if (event.target.closest('.item')) showSlider(slot);
    });
});

document.addEventListener('dragover', event => {
    if (draggedFromSlot && !event.target.closest('.filter-grid')) event.preventDefault();
    if (draginput && !event.target.closest('#inputpre')) event.preventDefault();
});
document.addEventListener('drop', event => {
    if (draggedFromSlot && !event.target.closest('.filter-grid')) {
        event.preventDefault();
        draggedItem.remove();
        dragCompleted = true;
        processimg();
    }
    if (draginput && !event.target.closest('#inputpre')) {
        event.preventDefault();
        clearSourceImage();
        inputdragged = true;
    }
});

intensity.addEventListener('input', () => {
    intensityval.textContent = `${intensity.value}%`;
    const selectedSlot = slots.find(slot => slot.getAttribute('aria-label') === slider.dataset.slot);
    const placed = selectedSlot?.querySelector('.item');
    if (placed) {
        placed.dataset.intensity = intensity.value;
        processimg();
    }
});

async function saveoutput() {
    if (!outputurl) return;

    const blob = await fetch(outputurl).then(response => response.blob());
    if ('showSaveFilePicker' in window) {
        const handle = await window.showSaveFilePicker({
            types: [{
                description: 'PNG image',
                accept: { 'image/png': ['.png'] },
            }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
    }

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

savebtn.addEventListener('click', async event => {
    event.stopPropagation();
    try {
        await saveoutput();
    } catch (error) {
        if (error.name !== 'AbortError') {
            announce(error.message);
            console.error(error);
        }
    }
});

document.querySelectorAll('[data-enlarge]').forEach(button => {
    button.addEventListener('click', event => {
        event.stopPropagation();
        showlightbox(document.getElementById(button.dataset.enlarge));
    });
});

lightboxclose.addEventListener('click', hidelightbox);
lightbox.addEventListener('click', event => {
    if (event.target === lightbox) hidelightbox();
});
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !lightbox.hidden) hidelightbox();
});

document.addEventListener('click', event => {
    if (!event.target.closest('.slidercss') && !event.target.closest('.slot .item')) hideSlider();
});
window.addEventListener('resize', hideSlider);
inventory.querySelectorAll('.item[draggable]').forEach(inventory);
loadInventory();