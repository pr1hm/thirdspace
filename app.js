const API_BASE = 'http://127.0.0.1:8000';

const slots = [...document.querySelectorAll('.slot')];
const slider = document.getElementById('slider');
const intensity = document.getElementById('intensity');
const intensityValue = document.getElementById('intensityValue');
const imageInput = document.getElementById('imageInput');
const sourcePreview = document.getElementById('sourcePreview');
const outputPreview = document.getElementById('outputPreview');
const inventoryGrid = document.getElementById('inventoryGrid');
const sourceEnlargeButton = sourcePreview.querySelector('[data-enlarge="sourcePreview"]');
const outputEnlargeButton = outputPreview.querySelector('[data-enlarge="outputPreview"]');
const saveButton = document.getElementById('saveButton');
const processingStatus = document.getElementById('processingStatus');
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxClose = document.getElementById('lightboxClose');

let draggedItem = null;
let draggedFromSlot = null;
let dragCompleted = false;
let draggedSourceImage = null;
let sourceImageDragCompleted = false;
let sourceImageUrl = null;
let sourceFile = null;
let outputImageUrl = null;
let processController = null;
let processRequestVersion = 0;

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
    intensityValue.textContent = `${intensity.value}%`;
    slider.classList.add('visible');
    intensity.focus();
}

function getSelectedFilters() {
    return slots
        .map(slot => slot.querySelector('.item'))
        .filter(Boolean)
        .map(item => ({
            name: item.dataset.filter,
            intensity: Number(item.dataset.intensity || 100),
        }));
}

async function processCurrentImage() {
    if (!sourceFile) return;

    processController?.abort();
    processController = new AbortController();
    const requestVersion = ++processRequestVersion;
    outputPreview.classList.add('processing');
    processingStatus.textContent = 'hol\' up...';
    saveButton.disabled = true;
    const formData = new FormData();
    formData.append('image', sourceFile, sourceFile.name);
    formData.append('filters', JSON.stringify(getSelectedFilters()));

    try {
        const response = await fetch(`${API_BASE}/process`, {
            method: 'POST',
            body: formData,
            signal: processController.signal,
        });
        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `Processing failed (${response.status})`);
        }

        const blob = await response.blob();
        if (requestVersion !== processRequestVersion) return;
        if (outputImageUrl) URL.revokeObjectURL(outputImageUrl);
        outputImageUrl = URL.createObjectURL(blob);
        const outputImage = document.createElement('img');
        outputImage.src = outputImageUrl;
        outputImage.alt = 'Processed output image';
        outputPreview.replaceChildren(outputImage);
        outputPreview.prepend(saveButton, processingStatus);
        outputPreview.append(outputEnlargeButton);
        saveButton.disabled = false;
        outputPreview.classList.remove('processing');
    } catch (error) {
        if (error.name !== 'AbortError') {
            outputPreview.classList.remove('processing');
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
    processCurrentImage();
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
            processCurrentImage();
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
    if (sourceImageUrl) URL.revokeObjectURL(sourceImageUrl);
    sourceFile = file;
    sourceImageUrl = URL.createObjectURL(file);
    sourcePreview.classList.add('has-image');
    const image = document.createElement('img');
    image.src = sourceImageUrl;
    image.alt = 'Loaded source image';
    image.draggable = true;
    image.addEventListener('click', event => event.stopPropagation());
    image.addEventListener('dragstart', event => {
        draggedSourceImage = image;
        sourceImageDragCompleted = false;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', 'source-image');
    });
    image.addEventListener('dragend', () => {
        if (!sourceImageDragCompleted && draggedSourceImage === image) clearSourceImage();
        draggedSourceImage = null;
        sourceImageDragCompleted = false;
    });
    sourcePreview.replaceChildren(image, sourceEnlargeButton);
    announce('Image loaded');
    processCurrentImage();
}

function clearSourceImage() {
    if (sourceImageUrl) URL.revokeObjectURL(sourceImageUrl);
    sourceImageUrl = null;
    sourceFile = null;
    sourcePreview.classList.remove('has-image');
    sourcePreview.replaceChildren(
        Object.assign(document.createElement('span'), {
            className: 'preview-hint',
            textContent: 'DRAG IMAGE OR CLICK TO LOAD AN IMG',
        }),
        sourceEnlargeButton
    );
    outputPreview.replaceChildren();
    outputPreview.append(
        saveButton,
        processingStatus,
        outputEnlargeButton
    );
    saveButton.disabled = true;
    outputPreview.classList.remove('processing');
}

function getPreviewImage(preview) {
    return preview.querySelector('img');
}

function showLightbox(preview) {
    const image = getPreviewImage(preview);
    if (!image) return;
    lightboxImage.src = image.currentSrc || image.src;
    lightbox.hidden = false;
    lightboxClose.focus();
}

function hideLightbox() {
    lightbox.hidden = true;
    lightboxImage.removeAttribute('src');
}

async function loadInventory() {
    try {
        const response = await fetch(`${API_BASE}/inventory`);
        if (!response.ok) throw new Error(`Inventory failed (${response.status})`);
        const filters = await response.json();
        inventoryGrid.replaceChildren();
        filters.forEach(filter => {
            const item = document.createElement('div');
            item.className = 'item';
            item.draggable = true;
            item.tabIndex = 0;
            item.dataset.filter = filter.name;
            item.title = filter.description;
            item.textContent = filter.name;
            inventoryGrid.append(item);
            setupInventoryItem(item);
        });
    } catch (error) {
        announce(error.message);
        console.error(error);
    }
}

function setupInventoryItem(item) {
    addDragHandlers(item);
    item.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const emptySlot = slots.find(slot => !slot.firstElementChild);
            if (emptySlot) placeItem(item, emptySlot);
        }
    });
}

sourcePreview.addEventListener('click', () => imageInput.click());
sourcePreview.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        imageInput.click();
    }
});
imageInput.addEventListener('change', event => loadSourceImage(event.target.files[0]));
sourcePreview.addEventListener('dragover', event => {
    event.preventDefault();
    sourcePreview.classList.add('drag-over');
});
sourcePreview.addEventListener('dragleave', () => sourcePreview.classList.remove('drag-over'));
sourcePreview.addEventListener('drop', event => {
    event.preventDefault();
    sourcePreview.classList.remove('drag-over');
    if (draggedSourceImage) {
        sourceImageDragCompleted = true;
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
    if (draggedSourceImage && !event.target.closest('#sourcePreview')) event.preventDefault();
});
document.addEventListener('drop', event => {
    if (draggedFromSlot && !event.target.closest('.filter-grid')) {
        event.preventDefault();
        draggedItem.remove();
        dragCompleted = true;
        processCurrentImage();
    }
    if (draggedSourceImage && !event.target.closest('#sourcePreview')) {
        event.preventDefault();
        clearSourceImage();
        sourceImageDragCompleted = true;
    }
});

intensity.addEventListener('input', () => {
    intensityValue.textContent = `${intensity.value}%`;
    const selectedSlot = slots.find(slot => slot.getAttribute('aria-label') === slider.dataset.slot);
    const placed = selectedSlot?.querySelector('.item');
    if (placed) {
        placed.dataset.intensity = intensity.value;
        processCurrentImage();
    }
});

async function saveOutputImage() {
    if (!outputImageUrl) return;

    const blob = await fetch(outputImageUrl).then(response => response.blob());
    const suggestedName = `sick-image-editor-${Date.now()}.png`;
    if ('showSaveFilePicker' in window) {
        const handle = await window.showSaveFilePicker({
            suggestedName,
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
    link.download = suggestedName;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

saveButton.addEventListener('click', async event => {
    event.stopPropagation();
    try {
        await saveOutputImage();
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
        showLightbox(document.getElementById(button.dataset.enlarge));
    });
});

lightboxClose.addEventListener('click', hideLightbox);
lightbox.addEventListener('click', event => {
    if (event.target === lightbox) hideLightbox();
});
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !lightbox.hidden) hideLightbox();
});

document.addEventListener('click', event => {
    if (!event.target.closest('.slidercss') && !event.target.closest('.slot .item')) hideSlider();
});
window.addEventListener('resize', hideSlider);
inventoryGrid.querySelectorAll('.item[draggable]').forEach(setupInventoryItem);
loadInventory();
